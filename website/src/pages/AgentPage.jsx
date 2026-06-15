import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { avatarFor, initialsFor } from '../lib/avatars'
import './AgentPage.css'

// dev → local backend; production build → comms on the box via Cloudflare Tunnel
const API = import.meta.env.DEV ? 'http://localhost:5181' : 'https://comms.newavera.co.il'

function Avatar({ name }) {
  const src = avatarFor(name)
  const [failed, setFailed] = useState(false)
  if (!src || failed) {
    return <div className="agent-avatar agent-avatar-fallback" aria-hidden="true">{initialsFor(name)}</div>
  }
  return <img className="agent-avatar" src={src} alt={name} onError={() => setFailed(true)} />
}

export default function AgentPage() {
  const { slug } = useParams()
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showMd, setShowMd] = useState(false)
  const [showLog, setShowLog] = useState(false)

  // mini-chat state
  const [thread, setThread] = useState([])     // [{author, text}]
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const chatEnd = useRef(null)

  useEffect(() => {
    let alive = true
    setLoading(true); setError(null); setProfile(null); setThread([])
    fetch(`${API}/agents/${slug}/profile`)
      .then((x) => { if (!x.ok) throw new Error(x.status === 404 ? 'סוכן לא נמצא' : 'שגיאת שרת'); return x.json() })
      .then((p) => { if (alive) { setProfile(p); setLoading(false) } })
      .catch((e) => { if (alive) { setError(e.message); setLoading(false) } })
    return () => { alive = false }
  }, [slug])

  useEffect(() => {
    if (chatEnd.current) chatEnd.current.scrollIntoView({ behavior: 'smooth' })
  }, [thread, sending])

  async function send() {
    const text = draft.trim()
    if (!text || sending) return
    setDraft('')
    const history = thread.slice(-8)  // light context: last few turns
    setThread((t) => [...t, { author: 'בועז', text }])
    setSending(true)
    try {
      const r = await fetch(`${API}/agents/${slug}/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, history }),
      }).then((x) => x.json())
      setThread((t) => [...t, { author: profile?.name || slug, text: r.reply || '(אין תשובה)' }])
    } catch {
      setThread((t) => [...t, { author: 'מערכת', text: '(שגיאה — הסוכן לא זמין כרגע)' }])
    } finally {
      setSending(false)
    }
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  if (loading) {
    return <div className="agent-page"><div className="container"><div className="agent-loading">טוען מסך סוכן…</div></div></div>
  }
  if (error) {
    return (
      <div className="agent-page"><div className="container">
        <div className="agent-error">
          <p>{error}</p>
          <Link className="agent-back" to="/">← חזרה למבנה החברה</Link>
        </div>
      </div></div>
    )
  }

  const { name, role, md, log, reports } = profile

  return (
    <div className="agent-page">
      <div className="container">
        <Link className="agent-back" to="/">← מבנה החברה</Link>

        <header className="agent-head">
          <Avatar name={name} />
          <div className="agent-head-text">
            <h1 className="agent-name">{name}</h1>
            {role && <span className="agent-role">{role}</span>}
          </div>
        </header>

        <div className="agent-grid">
          {/* ── works ── */}
          <section className="agent-card agent-works">
            <h2 className="agent-card-title">📄 העבודות של {name}</h2>
            {reports.length === 0 ? (
              <p className="agent-empty">אין עדיין דוחות שמורים.</p>
            ) : (
              <ul className="agent-reports">
                {reports.map((r, i) => (
                  <li key={i}>
                    <a href={r.link} target="_blank" rel="noopener noreferrer">
                      <span className="report-topic">{r.topic}</span>
                      <span className="report-date">{r.date}</span>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* ── chat ── */}
          <section className="agent-card agent-chat-card">
            <h2 className="agent-card-title">💬 שיחה עם {name} על החומר שלו</h2>
            <div className="agent-chat-stream">
              {thread.length === 0 && (
                <div className="agent-chat-hint">
                  שאל את {name} על העבודות שלו — למשל "אילו דוחות הפקת?" או "מה הקישור לדוח על …".
                </div>
              )}
              {thread.map((m, i) => (
                m.author === 'מערכת' ? (
                  <div key={i} className="agent-sys">{m.text}</div>
                ) : (
                  <div key={i} className={`agent-bubble ${m.author === 'בועז' ? 'mine' : 'theirs'}`}>
                    {m.author !== 'בועז' && <span className="agent-bubble-author">{m.author}</span>}
                    <div className="agent-bubble-text">{m.text}</div>
                  </div>
                )
              ))}
              {sending && (
                <div className="agent-bubble theirs typing"><div className="agent-bubble-text"><i /><i /><i /></div></div>
              )}
              <div ref={chatEnd} />
            </div>
            <div className="agent-compose">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={onKey}
                placeholder="שאל על החומר… (Enter לשליחה)"
                rows={2}
              />
              <button onClick={send} disabled={sending || !draft.trim()}>שלח</button>
            </div>
          </section>

          {/* ── main MD ── */}
          <section className="agent-card agent-doc">
            <button className="agent-card-title agent-toggle" onClick={() => setShowMd((v) => !v)}>
              📘 קובץ ההגדרה הראשי {showMd ? '▲' : '▼'}
            </button>
            {showMd && (
              md ? <pre className="agent-pre" dir="rtl">{md}</pre>
                 : <p className="agent-empty">אין קובץ הגדרה לסוכן זה.</p>
            )}
          </section>

          {/* ── log ── */}
          <section className="agent-card agent-doc">
            <button className="agent-card-title agent-toggle" onClick={() => setShowLog((v) => !v)}>
              🧾 לוג הריצות {showLog ? '▲' : '▼'}
            </button>
            {showLog && (
              log ? <pre className="agent-pre agent-log" dir="rtl">{log}</pre>
                  : <p className="agent-empty">אין עדיין רישומי לוג.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
