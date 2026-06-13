import goalsRaw from '../../../goals/Goals.md?raw'
import { parseMarkdownTable, colIndex } from '../lib/mdTable'
import './GoalsPage.css'

function statusClass(s) {
  if (s.includes('פעיל')) return 'tag tag-on'
  if (s.includes('להגדרה')) return 'tag tag-todo'
  return 'tag tag-planned'
}

export default function GoalsPage() {
  const { headers, rows } = parseMarkdownTable(goalsRaw)
  const cAgent = colIndex(headers, 'סוכן')
  const cGoal = colIndex(headers, 'יעד')
  const cMetric = colIndex(headers, 'מדד')
  const cTarget = headers.findIndex((h) => h.includes('מספרי'))
  const cWindow = colIndex(headers, 'חלון')
  const cStatus = colIndex(headers, 'סטטוס')

  return (
    <div className="goals-page">
      <div className="container">
        <div className="goals-head">
          <span className="goals-eyebrow">company framework<i /></span>
          <h1 className="goals-title">יעדי הסוכנים</h1>
          <p className="goals-note">
            נקרא ישירות מ-<code>goals/Goals.md</code> · יעד מדיד לכל סוכן. יעדים שטרם נקבעו מסומנים <span className="tag tag-todo">להגדרה</span>.
          </p>
        </div>

        <div className="goals-tablewrap">
          <table className="goals-table">
            <thead>
              <tr><th>סוכן</th><th>יעד</th><th>מדד</th><th>יעד</th><th>חלון</th><th>סטטוס</th></tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="cell-agent">{r[cAgent]}</td>
                  <td>{r[cGoal]}</td>
                  <td className="cell-metric">{r[cMetric]}</td>
                  <td className="cell-target">{r[cTarget]}</td>
                  <td className="cell-window">{r[cWindow]}</td>
                  <td><span className={statusClass(r[cStatus] || '')}>{r[cStatus]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
