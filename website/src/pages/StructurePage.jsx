import { useMemo, useState } from 'react'
import structureRaw from '../../../structure/Structure.md?raw'
import { parseMarkdownTable, colIndex } from '../lib/mdTable'
import './StructurePage.css'

function NodeCard({ node, root, staff, showPurpose }) {
  /* personal assistant — compact card: just the name + a small tag */
  if (staff) {
    return (
      <div className="node node-staff">
        <span className="node-role">{node.name}</span>
        <span className="node-staff-tag">עוזר אישי</span>
      </div>
    )
  }
  /* a node with a personal name (שם) shows its role (תפקיד) in bold with the
     name in parentheses below — matching the management cards, whose bold line
     is already the role. role-only nodes keep role bold + English subtitle. */
  const personalName = node.shem && node.shem !== '—' ? node.shem : ''
  return (
    <div className={`node ${root ? 'node-ceo' : ''}`}>
      <span className="node-level">{`רמה ${node.level}`}</span>
      {personalName ? (
        <>
          <span className="node-role">{node.en || node.name}</span>
          <span className="node-name">{`(${personalName})`}</span>
        </>
      ) : (
        <>
          <span className="node-role">{node.name}</span>
          {node.en && <span className="node-en">{node.en}</span>}
        </>
      )}
      {showPurpose && node.purpose && <span className="node-purpose">{node.purpose}</span>}
      {node.link && (
        <a className="node-link" href={node.link} target="_blank" rel="noopener noreferrer">
          🔧 עורך התסריט
        </a>
      )}
    </div>
  )
}

/* Recursive org tree. Assistant nodes (type 'עוזר') render as side-staff of
   their parent — not in the subordinate row — to mark they aren't VPs.
   Each node that has reports (except the root) gets a +/- control above its
   box, straddling the connector line, to expand/collapse that branch only. */
function TreeNode({ node, childrenOf, root, collapsed, onToggle, showPurpose }) {
  const kids = childrenOf(node.name)
  const assistants = kids.filter((k) => k.type === 'עוזר')
  const reports = kids.filter((k) => k.type !== 'עוזר')
  const hasReports = reports.length > 0
  const isCollapsed = collapsed.has(node.name)
  const showReports = hasReports && !isCollapsed
  return (
    <li>
      <div className="node-anchor">
        {hasReports && !root && (
          <div className="node-toggle">
            <button
              className="node-toggle-btn"
              onClick={() => onToggle(node.name)}
              disabled={isCollapsed}
              title="קבץ מחלקה"
              aria-label="קבץ מחלקה"
            >−</button>
            <button
              className="node-toggle-btn"
              onClick={() => onToggle(node.name)}
              disabled={!isCollapsed}
              title="הרחב מחלקה"
              aria-label="הרחב מחלקה"
            >+</button>
          </div>
        )}
        <NodeCard node={node} root={root} showPurpose={showPurpose} />
        {assistants.length > 0 && (
          <div className="staff-side">
            {assistants.map((a) => (
              <div className="staff-item" key={a.name}>
                <span className="staff-conn" />
                <NodeCard node={a} staff />
              </div>
            ))}
          </div>
        )}
        {hasReports && isCollapsed && (
          <span className="node-collapsed-badge">{reports.length}+</span>
        )}
      </div>
      {showReports && (
        <ul>
          {reports.map((r) => (
            <TreeNode
              key={r.name}
              node={r}
              childrenOf={childrenOf}
              collapsed={collapsed}
              onToggle={onToggle}
              showPurpose={showPurpose}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

export default function StructurePage() {
  const { headers, rows } = parseMarkdownTable(structureRaw)
  const cName = colIndex(headers, 'סוכן')
  const cEn = colIndex(headers, 'תפקיד')
  const cShem = colIndex(headers, 'שם')
  const cLevel = colIndex(headers, 'רמה')
  const cParent = colIndex(headers, 'כפוף')
  const cPurpose = colIndex(headers, 'מטרה')
  const cType = colIndex(headers, 'סוג')
  const cLink = colIndex(headers, 'קישור')

  const nodes = rows.map((r) => ({
    name: r[cName],
    en: cEn >= 0 ? r[cEn] : '',
    shem: cShem >= 0 ? r[cShem] : '',
    level: r[cLevel],
    parent: cParent >= 0 ? r[cParent] : '',
    purpose: cPurpose >= 0 ? r[cPurpose] : '',
    type: cType >= 0 ? r[cType] : '',
    link: cLink >= 0 ? r[cLink] : '',
  }))

  const byName = {}
  nodes.forEach((n) => { byName[n.name] = n })
  const isRoot = (n) => !n.parent || n.parent === '—' || n.parent === '-' || !byName[n.parent]
  const roots = nodes.filter(isRoot)
  const childrenOf = (name) => nodes.filter((n) => n.parent === name)

  /* every non-root node that has subordinates — these are the collapsible
     departments. Collapsing them all leaves the management board visible. */
  const departments = useMemo(
    () => nodes
      .filter((n) => !isRoot(n) && nodes.some((c) => c.parent === n.name && c.type !== 'עוזר'))
      .map((n) => n.name),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [structureRaw],
  )

  const [collapsed, setCollapsed] = useState(() => new Set())
  const [showPurpose, setShowPurpose] = useState(false)  // agent descriptions hidden by default
  const onToggle = (name) =>
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  const collapseAll = () => setCollapsed(new Set(departments))
  const expandAll = () => setCollapsed(new Set())

  return (
    <div className="struct">
      <div className="container">
        <div className="struct-head">
          <span className="struct-eyebrow">company framework<i /></span>
          <h1 className="struct-title">מבנה החברה</h1>
          <p className="struct-note">
            נקרא ישירות מ-<code>structure/Structure.md</code> · רמת כל סוכן ניתנת לשינוי בקובץ.
          </p>
        </div>

        <div className="tree-controls">
          <button className="tree-btn tree-btn-wide" onClick={collapseAll}>
            כווץ הכל
          </button>
          <button className="tree-btn tree-btn-wide" onClick={expandAll}>
            פתח הכל
          </button>
          <button className="tree-btn tree-btn-wide" onClick={() => setShowPurpose((v) => !v)}>
            {showPurpose ? 'הסתר תיאורים' : 'הצג תיאורים'}
          </button>
          <span className="tree-controls-hint">או ± מעל כל מחלקה</span>
        </div>

        <div className="tree">
          <ul>
            {roots.map((r) => (
              <TreeNode
                key={r.name}
                node={r}
                childrenOf={childrenOf}
                root
                collapsed={collapsed}
                onToggle={onToggle}
                showPurpose={showPurpose}
              />
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
