import scheduleRaw from '../../../schedule/Schedule.md?raw'
import { parseMarkdownTable, colIndex } from '../lib/mdTable'
import './CalendarPage.css'

const clean = (s) => (s || '').replace(/`/g, '')
const DAYS = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']

function statusDot(s) {
  if (s?.includes('פעיל')) return 'dot dot-on'
  if (s?.includes('כבוי')) return 'dot dot-off'
  return 'dot dot-planned'
}

// which weekday columns a schedule row lands on, from its "ימים" cell
function daysFor(cell) {
  const s = cell || ''
  if (s.includes('יומי')) return DAYS
  return DAYS.filter((d) => s.includes(d))
}

export default function CalendarPage() {
  const { headers, rows } = parseMarkdownTable(scheduleRaw)
  const cAgent = colIndex(headers, 'סוכן'), cCmd = colIndex(headers, 'פקודה'), cTrig = colIndex(headers, 'טריגר')
  const cWhen = colIndex(headers, 'מתי'), cDays = colIndex(headers, 'ימים'), cOwner = colIndex(headers, 'בעלים'), cStatus = colIndex(headers, 'סטטוס')

  const scheduled = rows.filter((r) => r[cTrig]?.includes('מתוזמן'))
  const realtime = rows.filter((r) => r[cTrig]?.includes('זמן-אמת'))

  const columns = DAYS.map((day) => ({
    day,
    items: scheduled
      .map((r) => {
        const m = (r[cWhen] || '').match(/(\d{1,2}):(\d{2})/)
        if (!m || !daysFor(r[cDays]).includes(day)) return null
        return {
          time: `${m[1].padStart(2, '0')}:${m[2]}`,
          mins: Number(m[1]) * 60 + Number(m[2]),
          name: r[cAgent], cmd: clean(r[cCmd]), owner: r[cOwner], status: r[cStatus],
        }
      })
      .filter(Boolean)
      .sort((a, b) => a.mins - b.mins),
  }))

  const today = new Date().getDay()  // 0 = ראשון

  return (
    <div className="cal-page">
      <div className="container">
        <div className="cal-head">
          <span className="cal-eyebrow">company framework<i /></span>
          <h1 className="cal-title">יומן שבועי</h1>
          <p className="cal-note">המטלות המתוזמנות מ-<code>schedule/Schedule.md</code>, פרושות על פני השבוע.</p>
        </div>

        <div className="cal-grid">
          {columns.map((col, i) => (
            <div className={`cal-col ${i === today ? 'today' : ''}`} key={col.day}>
              <div className="cal-colhead">
                {col.day}{i === today && <span className="cal-todaytag">היום</span>}
              </div>
              <div className="cal-colbody">
                {col.items.length === 0 && <div className="cal-none">—</div>}
                {col.items.map((it, j) => (
                  <div className={`cal-card ${it.status?.includes('פעיל') ? 'active' : ''}`} key={j}>
                    <div className="cal-card-top">
                      <span className="cal-time">{it.time}</span>
                      <span className={statusDot(it.status)} title={it.status} />
                    </div>
                    <div className="cal-card-name">{it.name}</div>
                    <div className="cal-card-meta"><code>{it.cmd}</code></div>
                    <div className="cal-card-owner">{it.owner}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {realtime.length > 0 && (
          <div className="cal-rt">
            <div className="cal-rt-head">⚡ לפי אירוע (זמן-אמת) — ללא שעה קבועה</div>
            <div className="cal-rt-items">
              {realtime.map((r, i) => (
                <div className="cal-rt-item" key={i}>
                  <span className="cal-card-name">{r[cAgent]}</span>
                  <code>{clean(r[cCmd])}</code>
                  <span className="cal-rt-owner">{r[cOwner]}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
