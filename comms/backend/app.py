"""Comms backend — the company's communication hub.

A room hosts a conversation between the human (בועז) and one or more agents.
MVP: 1:1 rooms (בועז ↔ רונית). The schema already supports N agents per room,
so multi-agent meetings (with a chair agent) slot in later without migration.

Run:  uvicorn app:app --port 5181 --reload   (from comms/backend)
"""
import os
import re
import threading

import requests
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
import agents
import cmd_brain

app = FastAPI(title="Agent Company — Comms")

VAULT = os.environ.get("VAULT", r"C:/Users/User/Aiprojects/obsi_comp")
AGENT_OUTPUT_BUCKET = os.environ.get("AGENT_OUTPUT_BUCKET", "")
S3_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Hebrew agent name ⇄ English slug. The slug keys the agent's S3 deliverables
# (output/<slug>/) and its definition file (.claude/commands/<slug>.md), and is
# the URL segment for the agent screen (/agent/<slug>).
AGENT_SLUGS = {
    "דפנה": "dafna", "דרור": "dror", "עומרי": "omri", "גיא": "guy",
    "רונית": "ronit", "רן": "ran", "זובין": "conductor",
    "מנכ״ל": "ceo", "סמנכ״ל כספים": "cfo", "סמנכ״ל תפעול": "coo",
}
SLUG_TO_NAME = {v: k for k, v in AGENT_SLUGS.items()}

SYSTEM = "מערכת"
# רן מצורף אוטומטית לכל חדר (Front Door). הוא "מאזין": נוכח בכל חדר אך עונה רק
# כשפונים אליו ב-@רן, או כשהוא הסוכן היחיד בחדר (1:1). ראה structure/Orchestration.md.
AUTO_JOIN = ["רן"]
LISTENERS = {"רן"}
# per-room live state (single-process uvicorn): is a round running, and did
# בועז raise his hand to interrupt it.
ROUND_ACTIVE: dict[int, bool] = {}
INTERRUPT: dict[int, bool] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://company-urban.newavera.co.il", "http://localhost:5180", "http://localhost:5173", "http://127.0.0.1:5180"],
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    db.init_db()


class NewRoom(BaseModel):
    title: str
    kind: str = "1:1"
    participants: list[str] = []
    chair: str | None = None


class NewMessage(BaseModel):
    text: str


class NewParticipant(BaseModel):
    agent: str


class RoomStatus(BaseModel):
    status: str  # 'active' (open) | 'closed' (ended)


class AgentPost(BaseModel):
    agent: str
    text: str


# Optional shared secret for /post (background jobs posting agent messages).
# If set on the backend AND on the worker, the worker must send it as X-Post-Token.
RESEARCH_POST_TOKEN = os.environ.get("RESEARCH_POST_TOKEN", "")


def _greeting(agent):
    """כלל 1 ב-comms/Room-Conduct.md — הצגה עצמית בכניסה לחדר (פעם אחת)."""
    role = agents.ROLES.get(agent, "")
    suffix = f" — {role}" if role else ""
    return f"שלום, כאן {agent}{suffix}. מאזין; אענה כשיפנו אליי (@{agent} או בשם)."


def _addressed(agent, text):
    """כלל 2 — פנייה לסוכן: ב-@<שם> או בשם בלבד. השם נבדק כמילה שלמה (גבול-מילה)
    כדי שלא תהיה התאמה שגויה כשהשם הוא חלק ממילה אחרת (למשל 'רן' בתוך 'קרן')."""
    return re.search(rf"(?<!\w){re.escape(agent)}(?!\w)", text) is not None


@app.get("/agents")
def get_agents():
    return {"agents": agents.known_agents(), "roles": agents.roles()}


@app.get("/rooms")
def get_rooms():
    return db.list_rooms()


@app.post("/rooms")
def post_room(body: NewRoom):
    unknown = [a for a in body.participants if a not in agents.known_agents()]
    if unknown:
        raise HTTPException(400, f"סוכנים לא מוכרים: {unknown}")
    if body.chair and body.chair not in body.participants:
        raise HTTPException(400, "היו״ר חייב להיות אחד המשתתפים")
    # רן (וכל AUTO_JOIN) מצטרף אוטומטית לכל חדר — "מוכנס לחדר".
    participants = list(body.participants)
    for a in AUTO_JOIN:
        if a not in participants:
            participants.append(a)
    # ה'גודל' של החדר נקבע לפי המשתתפים שאינם מאזינים (רן לא הופך 1:1 ל'ישיבה').
    speakers = [a for a in participants if a not in LISTENERS]
    kind = body.kind or ("meeting" if len(speakers) > 1 else "1:1")
    rid = db.create_room(body.title, kind, participants, body.chair)
    # כלל 1 — כל משתתף מציג את עצמו פעם אחת בפתיחת החדר.
    for a in participants:
        db.add_message(rid, a, _greeting(a))
    return {"id": rid}


@app.post("/rooms/{room_id}/status")
def post_room_status(room_id: int, body: RoomStatus):
    """End a conversation (status='closed') or reopen it (status='active').
    Separate from delete — a closed room keeps its history."""
    if body.status not in ("active", "closed"):
        raise HTTPException(400, "status חייב להיות 'active' או 'closed'")
    db.set_room_status(room_id, body.status)
    return {"ok": True, "status": body.status}


@app.delete("/rooms/{room_id}")
def delete_room(room_id: int):
    db.delete_room(room_id)
    ROUND_ACTIVE.pop(room_id, None)
    INTERRUPT.pop(room_id, None)
    return {"ok": True}


@app.get("/rooms/{room_id}/messages")
def get_messages(room_id: int):
    return db.list_messages(room_id)


@app.post("/rooms/{room_id}/participants")
def post_participant(room_id: int, body: NewParticipant):
    if body.agent not in agents.known_agents():
        raise HTTPException(400, f"סוכן לא מוכר: {body.agent}")
    db.add_participant(room_id, body.agent)
    # כלל 1 — הסוכן שנוסף מציג את עצמו בכניסתו.
    db.add_message(room_id, body.agent, _greeting(body.agent))
    return {"ok": True}


@app.post("/rooms/{room_id}/post")
def post_agent_message(room_id: int, body: AgentPost, x_post_token: str = Header(default="")):
    """Internal: a background job (e.g. the Fargate deep-research worker) posts a
    message into a room as an agent — no reply round is triggered. The idle-poll
    in the UI surfaces it live. Guarded by X-Post-Token only if RESEARCH_POST_TOKEN is set."""
    if RESEARCH_POST_TOKEN and x_post_token != RESEARCH_POST_TOKEN:
        raise HTTPException(403, "bad post token")
    msg = db.add_message(room_id, body.agent, body.text)
    return {"ok": True, "message": msg}


def _reply_in_room(room_id, agent):
    history = db.list_messages(room_id)  # everything so far, incl. this round
    try:
        reply = agents.agent_reply(agent, history, room_id=room_id)
    except Exception as e:  # noqa: BLE001
        reply = f"(שגיאה במוח של {agent}: {e})"
    if reply:
        db.add_message(room_id, agent, reply)


def _run_round(room_id, responders, summarizer):
    """Background round. Checks the interrupt flag before each turn so בועז's
    raised hand stops the floor immediately (the in-flight turn still finishes)."""
    try:
        for agent in responders:
            if INTERRUPT.get(room_id):
                return
            _reply_in_room(room_id, agent)
        if summarizer and not INTERRUPT.get(room_id):
            _reply_in_room(room_id, summarizer)
    finally:
        INTERRUPT[room_id] = False
        ROUND_ACTIVE[room_id] = False


@app.post("/rooms/{room_id}/messages")
def post_message(room_id: int, body: NewMessage):
    """Store the human message and kick off the reply round in the background
    (so בועז can interrupt mid-round). Addressing:
      • @mention → only the mentioned agents reply (targeted).
      • room has a chair → every other participant speaks once, chair sums up.
      • else (1:1 / no chair) → each participant replies once.
    The client polls /messages + /state to stream replies as they land."""
    parts = db.room_participants(room_id)
    if not parts:
        raise HTTPException(404, "חדר לא קיים או ללא משתתפים")
    text = body.text.strip()
    chair = db.room_chair(room_id)

    user_msg = db.add_message(room_id, agents.HUMAN, text)

    # כלל 2 ב-comms/Room-Conduct.md — מדברים רק כשמתבקשים (פנייה ב-@<שם> או בשם).
    mentioned = [a for a in parts if _addressed(a, text)]
    non_listeners = [a for a in parts if a not in LISTENERS]
    if mentioned:                                       # פנייה מפורשת ב-@<שם>
        responders, summarizer = mentioned, None
    elif chair and chair in parts and len(parts) > 1:   # חדר ישיבה — היו״ר מנהל את הסבב
        responders = [a for a in parts if a != chair]
        summarizer = chair
    elif len(parts) == 1:                               # סוכן יחיד (כולל מאזין) — שיחת 1:1
        responders, summarizer = list(parts), None
    elif len(non_listeners) == 1:                       # 1:1 אפקטיבי (סוכן + רן המאזין)
        responders, summarizer = non_listeners, None
    else:                                               # חדר קבוצתי ללא פנייה — כולם מאזינים
        responders, summarizer = [], None

    if not responders and not summarizer:
        # אף אחד לא התבקש לדבר — החדר מאזין בשתיקה (כלל 2).
        return {"messages": [user_msg], "round_active": False}

    INTERRUPT[room_id] = False
    ROUND_ACTIVE[room_id] = True
    threading.Thread(target=_run_round, args=(room_id, responders, summarizer),
                     daemon=True).start()

    return {"messages": [user_msg], "round_active": True}


@app.get("/rooms/{room_id}/state")
def get_state(room_id: int):
    return {"round_active": bool(ROUND_ACTIVE.get(room_id))}


@app.post("/rooms/{room_id}/interrupt")
def interrupt(room_id: int):
    """בועז raises his hand: stop the round and let everyone know he has the floor."""
    INTERRUPT[room_id] = True
    msg = db.add_message(room_id, SYSTEM,
                         "✋ בועז ביקש את רשות הדיבור — עוצרים את הסבב, הרצפה שלך.")
    return {"ok": True, "message": msg}


# ─── BoazTask read-only proxy ───
# The mobile app (/app) shows בועז's task list. The BoazTask API needs a Bearer
# token that must NOT ship in the browser bundle, so we proxy it here: the box
# holds RAN_TOKEN (already whitelisted in deploy/sync-box-env.sh) and fetches
# server-side. Read-only — the app only displays tasks, never writes.
TASKS_API = os.environ.get("TASKS_API", "https://task.newavera.co.il/api/tasks/")
RAN_TOKEN = os.environ.get("RAN_TOKEN", "")


@app.get("/my-tasks")
def my_tasks():
    """Proxy בועז's open + recent tasks from BoazTask (agent-tasks hidden by the
    API's default). Returns the raw list; the frontend sorts/filters for display."""
    if not RAN_TOKEN:
        raise HTTPException(status_code=503, detail="RAN_TOKEN not configured on the server")
    try:
        r = requests.get(TASKS_API, headers={"Authorization": f"Bearer {RAN_TOKEN}"}, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"BoazTask API unreachable: {e}")


# ─── Agent screen ───
# One screen per agent (reached from the org chart): its works (reports), its
# main definition MD, its run log, and a small chat about its material.
class AgentChat(BaseModel):
    text: str
    history: list[dict] = []  # prior turns [{author, text}] for light context


def _s3_text(key):
    """Read a UTF-8 text object from the agent-output bucket; '' if missing/unset."""
    if not AGENT_OUTPUT_BUCKET:
        return ""
    try:
        import boto3
        s3 = boto3.client("s3", region_name=S3_REGION)
        obj = s3.get_object(Bucket=AGENT_OUTPUT_BUCKET, Key=key)
        return obj["Body"].read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001 — missing object / no creds → just empty
        return ""


def _parse_reports_index(md):
    """Parse the agent's reports-index.md markdown table into [{date,topic,link}].
    Skips the header/separator and the index's own self-published row."""
    out = []
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        date, topic, link = cells[0], cells[1], cells[2]
        if date in ("תאריך", "") or set(date) <= {"-", ":", " "}:
            continue  # header or separator row
        if topic == "reports-index" or not link.startswith("http"):
            continue  # the index self-row / non-link row — not a real report
        out.append({"date": date, "topic": topic, "link": link})
    out.reverse()  # newest first
    return out


@app.get("/agents/{slug}/profile")
def agent_profile(slug: str):
    name = SLUG_TO_NAME.get(slug)
    if not name:
        raise HTTPException(404, f"סוכן לא מוכר: {slug}")
    md = ""
    md_path = os.path.join(VAULT, ".claude", "commands", f"{slug}.md")
    if os.path.exists(md_path):
        with open(md_path, encoding="utf-8") as f:
            md = f.read()
    reports = _parse_reports_index(_s3_text(f"{slug}/reports-index.md"))
    log = _s3_text(f"{slug}/log/runs.log")
    has_chat = agents._brain(name) is not None
    return {"name": name, "slug": slug, "role": agents.ROLES.get(name, ""),
            "md": md, "reports": reports, "log": log, "has_chat": has_chat}


@app.post("/agents/{slug}/chat")
def agent_chat(slug: str, body: AgentChat):
    """Small chat on the agent screen — Q&A about the agent's existing material.
    A new deep research needs a room to post the finished report back to, so we
    steer those requests to תקשורת instead of orphan-launching here."""
    name = SLUG_TO_NAME.get(slug)
    if not name:
        raise HTTPException(404, f"סוכן לא מוכר: {slug}")
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(400, "טקסט ריק")
    if name in cmd_brain.HEAVY and cmd_brain._wants_deep(text):
        return {"reply": ("כאן אפשר לשאול על החומר הקיים שלי. להפקת דוח חדש / מחקר מעמיק — "
                          "פִתחו חדר ב'תקשורת' ובקשו שם 'דוח מלא', כדי שהדוח יישלח אליכם כשיהיה מוכן.")}
    msgs = []
    for h in (body.history or []):
        a, t = h.get("author"), h.get("text")
        if a and t:
            msgs.append({"author": a, "text": t})
    msgs.append({"author": agents.HUMAN, "text": text})
    try:
        reply = agents.agent_reply(name, msgs, room_id=None)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"שגיאה במוח של {name}: {e}")
    return {"reply": reply or "(אין תשובה)"}


@app.get("/health")
def health():
    return {"ok": True, "agents": agents.known_agents()}
