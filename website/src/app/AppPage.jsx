import { useEffect, useState } from 'react'
import TactLogo from '../components/TactLogo'
import './AppPage.css'

// same live-fetch pattern as CommsPage: dev → local comms, prod → the box.
const API = import.meta.env.DEV ? 'http://localhost:5181' : 'https://comms.newavera.co.il'

// urgency → sort weight + dot color (TACT palette).
const URGENCY = {
  'דחוף': { rank: 0, color: '#D64A2E' },
  'גבוה': { rank: 1, color: '#E08A2E' },
  'בינוני': { rank: 2, color: '#C9A227' },
  'נמוך': { rank: 3, color: '#3E7C5A' },
}
const STATUS_RANK = { 'חדש': 0, 'בטיפול': 1 }

function sortTasks(tasks) {
  return [...tasks].sort((a, b) => {
    if (a.immediate !== b.immediate) return a.immediate ? -1 : 1
    const ua = URGENCY[a.urgency]?.rank ?? 9
    const ub = URGENCY[b.urgency]?.rank ?? 9
    if (ua !== ub) return ua - ub
    const sa = STATUS_RANK[a.status] ?? 9
    const sb = STATUS_RANK[b.status] ?? 9
    return sa - sb
  })
}

export default function AppPage() {
  const [tasks, setTasks] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const r = await fetch(`${API}/my-tasks`)
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data = await r.json()
      setTasks(sortTasks(Array.isArray(data) ? data : []))
    } catch (e) {
      setError('לא הצלחתי לטעון את המטלות. נסה לרענן.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const open = tasks?.filter((t) => t.status === 'חדש' || t.status === 'בטיפול').length ?? 0

  return (
    <div className="app-shell">
      <header className="app-bar">
        <TactLogo tone="light" size={0.7} />
        <div className="app-bar-title">
          <span className="app-bar-h1">המטלות שלי</span>
          {tasks && <span className="app-bar-sub">{open} פתוחות · {tasks.length} סה״כ</span>}
        </div>
        <button className="app-refresh" onClick={load} aria-label="רענן" disabled={loading}>
          ↻
        </button>
      </header>

      <main className="app-main">
        {loading && <div className="app-state">טוען מטלות…</div>}
        {!loading && error && (
          <div className="app-state app-error">
            {error}
            <button className="app-retry" onClick={load}>נסה שוב</button>
          </div>
        )}
        {!loading && !error && tasks && tasks.length === 0 && (
          <div className="app-state">אין מטלות פתוחות 🎉</div>
        )}
        {!loading && !error && tasks && tasks.length > 0 && (
          <table className="task-table">
            <thead>
              <tr>
                <th className="col-task">מטלה</th>
                <th className="col-urg">דחיפות</th>
                <th className="col-status">סטטוס</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className={t.immediate ? 'row-immediate' : ''}>
                  <td className="col-task">
                    <div className="task-subject">
                      {t.immediate && <span className="immediate-flag" title="מיידי">⚡</span>}
                      {t.subject}
                    </div>
                    {t.sub_subject && <div className="task-sub">{t.sub_subject}</div>}
                    {t.description && <div className="task-desc">{t.description}</div>}
                  </td>
                  <td className="col-urg">
                    <span className="urg-pill">
                      <span
                        className="urg-dot"
                        style={{ background: URGENCY[t.urgency]?.color || '#9A958B' }}
                      />
                      {t.urgency || '—'}
                    </span>
                  </td>
                  <td className="col-status">
                    <span className={`status-pill status-${t.status === 'בטיפול' ? 'wip' : 'new'}`}>
                      {t.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </main>
    </div>
  )
}
