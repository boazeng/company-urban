/* Derive an agent's department = its level-1 ancestor in the org tree.
   Reads structure/Structure.md (the same source the Structure page uses), so
   departments stay in sync with the org chart automatically. */
import structureRaw from '../../../structure/Structure.md?raw'
import { parseMarkdownTable, colIndex } from './mdTable'

const { headers, rows } = parseMarkdownTable(structureRaw)
const cName = colIndex(headers, 'סוכן')
const cParent = colIndex(headers, 'כפוף')

const byName = {}
const nodes = rows.map((r) => ({
  name: r[cName],
  parent: cParent >= 0 ? r[cParent] : '',
}))
nodes.forEach((n) => { byName[n.name] = n })

const isRoot = (n) =>
  !n || !n.parent || n.parent === '—' || n.parent === '-' || !byName[n.parent]
const ceo = (nodes.find(isRoot) || {}).name

/* Climb parents until just below the CEO → that level-1 node is the department.
   A node already at level 1 (or unknown) returns itself. */
export function departmentOf(name) {
  let node = byName[name]
  if (!node) return name
  let guard = 0
  while (node.parent && node.parent !== ceo && byName[node.parent] && guard++ < 20) {
    node = byName[node.parent]
  }
  return node.name
}
