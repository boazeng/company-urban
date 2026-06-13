import { useEffect, useRef, useState } from 'react'
import { AGENT_ROLES as ROLE_LABELS } from '../lib/agents'
import './CommsPage.css'

// dev → local backend; production build → comms on the box via Cloudflare Tunnel
const API = import.meta.env.DEV ? 'http://localhost:5181' : 'https://comms.newavera.co.il'

export default function CommsPage() {
  const [rooms, setRooms] = useState([])
  const [agents, setAgents] = useState([])
  const [roles, setRoles] = useState({})
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [online, setOnline] = useState(true)
  const [creating, setCreating] = useState(false)
  const [pendingDelete, setPendingDelete] = useState(null)
  const scroller = useRef(null)
  const pollRef = useRef(null)

  async function loadRooms() {
    const r = await fetch(`${API}/rooms`).then((x) => x.json())
    setRooms(r)
    return r
  }

  useEffect(() => {
    (async () => {
      try {
        const ag = await fetch(`${API}/agents`).then((x) => x.json())
        setAgents(ag.agents || [])
        setRoles(ag.roles || {})
        let r = await loadRooms()
        if (!r.length) {
          const created = await fetch(`${API}/rooms`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'שיחה עם רונית', participants: ['רונית'] }),
          }).then((x) => x.json())
          r = await loadRooms()
          setActiveId(created.id)
        } else {
          setActiveId(r[0].id)
        }
      } catch {
        setOnline(false)
      }
    })()
    return stopPolling
  }, [])

  // switching rooms: stop any polling, reset, load that room's messages
  useEffect(() => {
    if (activeId == null) return
    stopPolling()
    setBusy(false)
    fetch(`${API}/rooms/${activeId}/messages`)
      .then((x) => x.json()).then(setMessages).catch(() => setOnline(false))
  }, [activeId])

  useEffect(() => {
    if (scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight
  }, [messages, busy])

  const activeRoom = rooms.find((r) => r.id === activeId)

  function stopPolling() {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  // poll messages + round state until the round ends
  function startPolling(roomId) {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const [msgs, st] = await Promise.all([
          fetch(`${API}/rooms/${roomId}/messages`).then((x) => x.json()),
          fetch(`${API}/rooms/${roomId}/state`).then((x) => x.json()),
        ])
        setMessages(msgs)
        if (!st.round_active) { stopPolling(); setBusy(false) }
      } catch {
        stopPolling(); setBusy(false); setOnline(false)
      }
    }, 1200)
  }

  async function send() {
    const text = draft.trim()
    if (!text || busy || activeId == null) return
    const roomId = activeId
    setDraft('')
    setMessages((m) => [...m, { id: `tmp-${Date.now()}`, author: 'בועז', text }])
    setBusy(true)
    try {
      await fetch(`${API}/rooms/${roomId}/messages`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      startPolling(roomId)
    } catch {
      setBusy(false); setOnline(false)
    }
  }

  async function raiseHand() {
    if (activeId == null) return
    try {
      await fetch(`${API}/rooms/${activeId}/interrupt`, { method: 'POST' })
      const msgs = await fetch(`${API}/rooms/${activeId}/messages`).then((x) => x.json())
      setMessages(msgs)
    } catch {
      setOnline(false)
    }
  }

  async function removeRoom(roomId) {
    setPendingDelete(null)
    try {
      await fetch(`${API}/rooms/${roomId}`, { method: 'DELETE' })
      const r = await loadRooms()
      if (activeId === roomId) {
        stopPolling()
        setActiveId(r.length ? r[0].id : null)
        if (!r.length) setMessages([])
      }
    } catch {
      setOnline(false)
    }
  }

  async function invite(agent) {
    if (!agent || activeId == null) return
    await fetch(`${API}/rooms/${activeId}/participants`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent }),
    })
    await loadRooms()
  }

  function mention(agent) {
    setDraft((d) => `@${agent} ${d}`)
  }

  function onKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  if (!online) {
    return (
      <div className="comms-page"><div className="container">
        <div className="comms-offline">
          <h1>מערכת התקשורת לא זמינה</h1>
          <p>הבקאנד לא רץ. הפעל אותו:</p>
          <pre>cd comms/backend
uvicorn app:app --port 5181 --reload</pre>
        </div>
      </div></div>
    )
  }

  const notInRoom = agents.filter((a) => !activeRoom?.participants.includes(a))
  const pendingRoom = rooms.find((r) => r.id === pendingDelete)

  return (
    <div className="comms-page">
      <div className="container comms-shell">
        <aside className="comms-rooms">
          <div className="comms-rooms-head">
            חדרים
            <button className="comms-newbtn" onClick={() => setCreating((v) => !v)}>
              {creating ? '×' : '+ חדר'}
            </button>
          </div>

          {creating && (
            <NewRoomForm
              agents={agents}
              roles={roles}
              onCancel={() => setCreating(false)}
              onCreate={async (payload) => {
                const created = await fetch(`${API}/rooms`, {
                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(payload),
                }).then((x) => x.json())
                await loadRooms()
                if (created.id) setActiveId(created.id)
                setCreating(false)
              }}
            />
          )}

          {rooms.map((r) => (
            <div key={r.id} className={`comms-room-row ${r.id === activeId ? 'active' : ''}`}>
              <button
                className={`comms-room ${r.id === activeId ? 'active' : ''}`}
                onClick={() => setActiveId(r.id)}
              >
                <span className="comms-room-title">
                  {r.kind === 'meeting' ? '👥 ' : ''}{r.title}
                </span>
                <span className="comms-room-parts">
                  {r.participants.join(' · ')}{r.chair ? ` · יו״ר: ${r.chair}` : ''}
                </span>
              </button>
              <button
                className="comms-room-del"
                title="מחק שיחה"
                onClick={() => setPendingDelete(r.id)}
              >🗑️</button>
            </div>
          ))}
        </aside>

        <section className="comms-chat">
          <header className="comms-chat-head">
            <div className="comms-chat-headtop">
              <h2>{activeRoom?.kind === 'meeting' ? '👥 ' : ''}{activeRoom?.title || 'שיחה'}</h2>
              <div className="comms-chat-headactions">
                {notInRoom.length > 0 && (
                  <select className="comms-invite" value="" onChange={(e) => invite(e.target.value)}>
                    <option value="" disabled>+ הזמן סוכן</option>
                    {notInRoom.map((a) => <option key={a} value={a}>{a}</option>)}
                  </select>
                )}
                {activeId != null && (
                  <button
                    className="comms-chat-del"
                    title="מחק שיחה"
                    onClick={() => setPendingDelete(activeId)}
                  >🗑️ מחק שיחה</button>
                )}
              </div>
            </div>
            <div className="comms-chat-chips">
              {activeRoom?.participants.map((a) => (
                <button key={a} className={`chip-part ${activeRoom.chair === a ? 'chair' : ''}`}
                        title="לחץ כדי לפנות אליו (@)" onClick={() => mention(a)}>
                  {activeRoom.chair === a ? '⭐ ' : ''}{a}
                </button>
              ))}
            </div>
          </header>

          <div className="comms-stream" ref={scroller}>
            {messages.map((m) => (
              m.author === 'מערכת' ? (
                <div key={m.id} className="sys-line">{m.text}</div>
              ) : (
                <div key={m.id} className={`bubble ${m.author === 'בועז' ? 'mine' : 'theirs'}`}>
                  {m.author !== 'בועז' && (
                    <span className="bubble-author">
                      {activeRoom?.chair === m.author ? '⭐ ' : ''}{m.author}
                    </span>
                  )}
                  <div className="bubble-text">{m.text}</div>
                </div>
              )
            ))}
            {busy && (
              <div className="bubble theirs typing">
                <span className="bubble-author">המשתתפים מדברים…</span>
                <div className="bubble-text"><i /><i /><i /></div>
              </div>
            )}
          </div>

          <div className="comms-compose">
            <button
              className={`comms-hand ${busy ? 'live' : ''}`}
              onClick={raiseHand}
              title="עצור את הסבב — אני רוצה לדבר"
            >✋ אני רוצה לדבר</button>
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={onKey}
              placeholder="כתוב הודעה… (Enter לשליחה · @שם לפנייה ממוקדת)"
              rows={1}
            />
            <button className="comms-send" onClick={send} disabled={busy || !draft.trim()}>שלח</button>
          </div>
        </section>
      </div>

      {pendingDelete != null && (
        <div className="modal-overlay" onClick={() => setPendingDelete(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-icon">🗑️</div>
            <h3 className="modal-title">למחוק את השיחה?</h3>
            <p className="modal-body">
              {pendingRoom ? `"${pendingRoom.title}" וכל ההודעות שבה יימחקו. ` : ''}
              פעולה בלתי הפיכה.
            </p>
            <div className="modal-actions">
              <button className="modal-btn ghost" onClick={() => setPendingDelete(null)}>
                ביטול
              </button>
              <button className="modal-btn danger" onClick={() => removeRoom(pendingDelete)}>
                מחק
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function NewRoomForm({ agents, roles = {}, onCreate, onCancel }) {
  const [title, setTitle] = useState('')
  const [picked, setPicked] = useState([])
  const [chair, setChair] = useState('')

  function toggle(a) {
    setPicked((p) => p.includes(a) ? p.filter((x) => x !== a) : [...p, a])
  }

  const isMeeting = picked.length > 1
  const canCreate = title.trim() && picked.length > 0 && (!isMeeting || chair)

  return (
    <div className="comms-newroom">
      <input
        className="comms-newtitle"
        placeholder="נושא החדר/הישיבה"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <div className="comms-newlabel">משתתפים</div>
      <div className="comms-newagents">
        {agents.map((a) => (
          <label key={a} className={`comms-agent ${picked.includes(a) ? 'on' : ''}`}>
            <input type="checkbox" checked={picked.includes(a)} onChange={() => toggle(a)} />
            <span className="comms-agent-name">{a}</span>
            {(roles[a] || ROLE_LABELS[a]) && (
              <span className="comms-agent-role">{roles[a] || ROLE_LABELS[a]}</span>
            )}
          </label>
        ))}
      </div>
      {isMeeting && (
        <>
          <div className="comms-newlabel">יו״ר הישיבה</div>
          <select value={chair} onChange={(e) => setChair(e.target.value)} className="comms-chairsel">
            <option value="" disabled>בחר יו״ר</option>
            {picked.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </>
      )}
      <div className="comms-newactions">
        <button
          disabled={!canCreate}
          onClick={() => onCreate({
            title: title.trim(),
            participants: picked,
            chair: isMeeting ? chair : null,
          })}
        >צור</button>
        <button className="ghost" onClick={onCancel}>ביטול</button>
      </div>
    </div>
  )
}
