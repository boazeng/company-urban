import { useMemo, useState } from 'react'
import scheduleRaw from '../../../schedule/Schedule.md?raw'
import { parseMarkdownTable, colIndex } from '../lib/mdTable'
import { departmentOf } from '../lib/departments'
import './TimelinePage.css'

const clean = (s) => s.replace(/`/g, '')

function triggerClass(t) {
  if (t.includes('זמן-אמת')) return 'tag tag-rt'
  if (t.includes('מתוזמן')) return 'tag tag-sched'
  return 'tag'
}
function statusClass(s) {
  if (s.includes('פעיל')) return 'tag tag-on'
  if (s.includes('כבוי')) return 'tag tag-off'
  return 'tag tag-planned'
}

export default function TimelinePage() {
  const { headers, rows } = parseMarkdownTable(scheduleRaw)

  // map columns by Hebrew header name (robust to column reordering)
  const cAgent = colIndex(headers, 'סוכן'), cCmd = colIndex(headers, 'פקודה'), cTrig = colIndex(headers, 'טריגר')
  const cWhen = colIndex(headers, 'מתי'), cDays = colIndex(headers, 'ימים'), cOwner = colIndex(headers, 'בעלים'), cStatus = colIndex(headers, 'סטטוס')

  const [dept, setDept] = useState('')
  const [agent, setAgent] = useState('')

  // department of a row = department of its owner (level-1 area)
  const deptOfRow = (r) => departmentOf(r[cOwner])

  // distinct departments (sorted, stable) across all rows
  const departments = useMemo(
    () => [...new Set(rows.map(deptOfRow).filter(Boolean))],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scheduleRaw],
  )
  // agents available given the current department filter
  const agentsForDept = useMemo(
    () => [...new Set(rows.filter((r) => !dept || deptOfRow(r) === dept).map((r) => r[cAgent]).filter(Boolean))],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [scheduleRaw, dept],
  )

  const filtered = rows.filter(
    (r) => (!dept || deptOfRow(r) === dept) && (!agent || r[cAgent] === agent),
  )

  function onDept(v) { setDept(v); setAgent('') }  // changing dept resets agent
  const hasFilter = dept || agent

  // markers for the 24h strip — scheduled rows that have an HH:MM time
  const marks = filtered
    .map((r) => {
      const when = r[cWhen] || ''
      const m = when.match(/(\d{1,2}):(\d{2})/)
      if (!r[cTrig]?.includes('מתוזמן') || !m) return null
      return {
        hour: Number(m[1]) + Number(m[2]) / 60,
        time: `${m[1]}:${m[2]}`,
        agent: r[cAgent],
        active: r[cStatus]?.includes('פעיל'),
      }
    })
    .filter(Boolean)

  return (
    <div className="tl-page">
      <div className="container">
        <div className="tl-head">
          <span className="tl-eyebrow">company framework<i /></span>
          <h1 className="tl-title">לוח זמנים</h1>
          <p className="tl-note">נקרא ישירות מ-<code>schedule/Schedule.md</code> — מנוהל ע״י המנצח זובין.</p>
        </div>

        {/* filters */}
        <div className="tl-filters">
          <label className="tl-filter">
            <span>מחלקה</span>
            <select value={dept} onChange={(e) => onDept(e.target.value)}>
              <option value="">כל המחלקות</option>
              {departments.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </label>
          <label className="tl-filter">
            <span>סוכן</span>
            <select value={agent} onChange={(e) => setAgent(e.target.value)}>
              <option value="">כל הסוכנים</option>
              {agentsForDept.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </label>
          {hasFilter && (
            <button className="tl-filter-clear" onClick={() => { setDept(''); setAgent('') }}>
              נקה סינון
            </button>
          )}
          <span className="tl-filter-count">{filtered.length} מתוך {rows.length}</span>
        </div>

        {/* 24h strip */}
        <div className="clock">
          <div className="clock-track">
            {[0, 6, 12, 18, 24].map((h) => (
              <span className="clock-tick" key={h} style={{ left: `${(h / 24) * 100}%` }}>
                <i /><b>{String(h).padStart(2, '0')}:00</b>
              </span>
            ))}
            {marks.map((m, i) => (
              <span
                className={`clock-mark ${m.active ? 'on' : ''}`}
                key={i}
                style={{ left: `${(m.hour / 24) * 100}%` }}
                title={`${m.agent} · ${m.time}`}
              >
                <em>{m.agent}</em>
                <span className="clock-time">{m.time}</span>
              </span>
            ))}
          </div>
        </div>

        {/* the real table */}
        <div className="tl-tablewrap">
          <table className="tl-table">
            <thead>
              <tr>
                <th>סוכן</th><th>פקודה</th><th>טריגר</th><th>מתי</th><th>ימים</th><th>בעלים</th><th>סטטוס</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <tr key={i}>
                  <td className="cell-agent">{r[cAgent]}</td>
                  <td><code>{clean(r[cCmd])}</code></td>
                  <td><span className={triggerClass(r[cTrig])}>{r[cTrig]}</span></td>
                  <td className="cell-when">{r[cWhen]}</td>
                  <td>{r[cDays]}</td>
                  <td>{r[cOwner]}</td>
                  <td><span className={statusClass(r[cStatus])}>{r[cStatus]}</span></td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={7} className="tl-empty">אין סוכנים מתוזמנים בסינון הזה.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
