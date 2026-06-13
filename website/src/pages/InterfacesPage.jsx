import interfacesRaw from '../../../interfaces/Interfaces.md?raw'
import { parseMarkdownTable, colIndex } from '../lib/mdTable'
import './InterfacesPage.css'

function typeClass(t) {
  const s = t.toLowerCase()
  if (s.includes('telegram')) return 'chip chip-tg'
  if (s.includes('api')) return 'chip chip-api'
  if (s.includes('imap') || s.includes('gmail') || s.includes('email')) return 'chip chip-mail'
  if (s.includes('scrap')) return 'chip chip-scrape'
  return 'chip'
}
function statusClass(s) {
  if (s.includes('פעיל')) return 'tag tag-on'
  if (s.includes('בהגדרה')) return 'tag tag-wip'
  return 'tag tag-planned'
}

export default function InterfacesPage() {
  const { headers, rows } = parseMarkdownTable(interfacesRaw)
  const cAgent = colIndex(headers, 'סוכן')
  const cType = colIndex(headers, 'תקשורת')
  const cSystem = colIndex(headers, 'מערכת')
  const cStatus = colIndex(headers, 'סטטוס')

  return (
    <div className="ifc-page">
      <div className="container">
        <div className="ifc-head">
          <span className="ifc-eyebrow">company framework<i /></span>
          <h1 className="ifc-title">ממשקים חיצוניים</h1>
          <p className="ifc-note">
            נקרא ישירות מ-<code>interfaces/Interfaces.md</code> · כל הערוצים שהסוכנים מתקשרים דרכם החוצה.
          </p>
        </div>

        <div className="ifc-tablewrap">
          <table className="ifc-table">
            <thead>
              <tr><th>סוכן</th><th>סוג תקשורת</th><th>מערכת חיצונית</th><th>סטטוס</th></tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="cell-agent">{r[cAgent]}</td>
                  <td><span className={typeClass(r[cType] || '')}>{r[cType]}</span></td>
                  <td className="cell-sys">{r[cSystem]}</td>
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
