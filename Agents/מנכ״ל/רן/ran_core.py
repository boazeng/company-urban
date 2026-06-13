"""
ran_core — המוח של רן (channel-agnostic).

מחזיק את כל ההיגיון של רן: לקוח BoazTask API, קריאת מייל, ניתוח Haiku,
הסוכן השיחתי (Sonnet tool-use), וזרימות הכפתורים המובנות — בלי לדעת כלום על
ערוץ ההפצה. כל ערוץ (טלגרם, ובהמשך וואטסאפ) קורא לאותו חוזה:

    start(session)        -> Response
    handle(session, text) -> Response

session = dict שהערוץ שומר פר-משתמש (ממוטט in-place; מחזיק flow/step/nt/chat).
Response = {"text": str, "buttons": [{"id","title"}] | None, "menu": bool, "md": bool}
  buttons = כפתורי בחירה (inline). menu = להציג את התפריט הראשי הקבוע.
  md      = לרנדר כ-Markdown (False לתשובות חופשיות של הסוכן).

ראה [[RAN_BOT_TELEGRAM]] / הדף של רן לפרטי הפעלה.
"""
import os
import sys
import json
import datetime
import threading
import requests

# כדי שהמודול ייטען נכון גם כשמייבאים אותו לפי-נתיב (למשל ממערכת ה-comms) —
# נוסיף את תיקיית הסוכן ל-path לפני ייבוא שכבת המרכזן.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import ran_orchestrator  # שכבת המרכזן: זימון מומחים + חנות שיחות
except ImportError:  # רן עדיין עובד גם בלי שכבת המרכזן
    ran_orchestrator = None

SHARED_ENV = os.environ.get("SHARED_ENV", r"C:/Users/User/Aiprojects/env/.env")
VAULT = os.environ.get("VAULT", r"C:/Users/User/Aiprojects/obsi_comp")


def env_val(key, path=SHARED_ENV):
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip("\"'")
    except FileNotFoundError:
        pass
    return ""


API_TOKEN = env_val("RAN_TOKEN")
ANTHROPIC_KEY = env_val("ANTHROPIC_API_KEY")
GMAIL_USER = env_val("BOAZ_GMAIL_USER")
GMAIL_PASS = env_val("BOAZ_GMAIL_APP_PASSWORD")
API = "https://task.newavera.co.il/api/tasks/"
AUTH = {"Authorization": f"Bearer {API_TOKEN}"}
OPEN = {"חדש", "בטיפול"}
URG_ICON = {"דחוף": "🔴", "גבוה": "🟠", "בינוני": "🟡", "נמוך": "🟢"}
URG_MAP = {"1": "דחוף", "2": "גבוה", "3": "בינוני", "4": "נמוך"}

# התפריט הראשי הקבוע — הערוץ מצייר אותו; ה-id של כל כפתור = הטקסט עצמו.
MENU = [["➕ מטלה חדשה", "⚡ מטלה מהירה"], ["⚡ מטלות מיידיות", "📋 מטלות לפי אחראי"]]
URG_BUTTONS = [
    {"id": "urg_1", "title": "🔴 דחוף"}, {"id": "urg_2", "title": "🟠 גבוה"},
    {"id": "urg_3", "title": "🟡 בינוני"}, {"id": "urg_4", "title": "🟢 נמוך"},
]


def _resp(text, buttons=None, menu=False, md=True):
    return {"text": text, "buttons": buttons, "menu": menu, "md": md}


# ─── working-style memory (ran_style.md, נטען ל-SYSTEM בכל קריאה) ───
STYLE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ran_style.md")


def load_style():
    """קריאת זיכרון צורת העבודה (טרי בכל קריאה — עדכון נכנס לתוקף מיד)."""
    try:
        with open(STYLE_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def save_style(content):
    """דריסת קובץ הסגנון, עם שמירת .bak של הגרסה הקודמת."""
    try:
        if os.path.exists(STYLE_FILE):
            with open(STYLE_FILE, encoding="utf-8") as f:
                prev = f.read()
            with open(STYLE_FILE + ".bak", "w", encoding="utf-8") as f:
                f.write(prev)
    except Exception:
        pass
    with open(STYLE_FILE, "w", encoding="utf-8") as f:
        f.write((content or "").rstrip() + "\n")
    return {"ok": True, "saved_chars": len(content or "")}


# ─── BoazTask API ───
def api_list():
    try:
        return requests.get(API, headers=AUTH, timeout=30).json()
    except Exception:
        return []


def api_create(payload):
    return requests.post(API, headers={**AUTH, "Content-Type": "application/json"},
                         data=json.dumps(payload).encode("utf-8"), timeout=30)


def analyze_quick(text):
    """Use Claude to turn free text into a structured task. Falls back to raw text."""
    if not ANTHROPIC_KEY:
        return {"subject": text[:50], "description": text}
    prompt = (
        "נתח את הטקסט הבא למטלה אחת. החזר אך ורק JSON עם השדות: "
        "subject (נושא קצר), sub_subject (תת-נושא או \"\"), description (תיאור), "
        "urgency (אחד מ: דחוף/גבוה/בינוני/נמוך), immediate (true/false). "
        f"הטקסט: {text}"
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 512,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        raw = r.json()["content"][0]["text"]
        import re
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0))
        return {k: data.get(k) for k in ("subject", "sub_subject", "description", "urgency", "immediate") if data.get(k) is not None}
    except Exception:
        return {"subject": text[:50], "description": text}


# ─── email (read-only, IMAP) ───
def _dh(s):
    """Decode a MIME-encoded email header (handles Hebrew)."""
    from email.header import decode_header
    if not s:
        return ""
    out = ""
    for txt, enc in decode_header(s):
        out += txt.decode(enc or "utf-8", "ignore") if isinstance(txt, bytes) else txt
    return out


def fetch_emails(limit=10, unread_only=False):
    """Read recent inbox emails for Boaz via IMAP (app password). Read-only (BODY.PEEK)."""
    if not GMAIL_USER or not GMAIL_PASS:
        return {"error": "חסר BOAZ_GMAIL_USER / BOAZ_GMAIL_APP_PASSWORD ב-env"}
    import imaplib
    import email
    try:
        M = imaplib.IMAP4_SSL("imap.gmail.com")
        M.login(GMAIL_USER, GMAIL_PASS)
        M.select("INBOX")
        _, data = M.search(None, "UNSEEN" if unread_only else "ALL")
        ids = data[0].split()[-max(1, min(limit, 25)):][::-1]
        out = []
        for i in ids:
            _, md = M.fetch(i, "(BODY.PEEK[])")
            msg = email.message_from_bytes(md[0][1])
            snippet = ""
            try:
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            snippet = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "ignore"); break
                else:
                    snippet = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "ignore")
            except Exception:
                snippet = ""
            out.append({"from": _dh(msg.get("From")), "subject": _dh(msg.get("Subject")),
                        "date": msg.get("Date"), "snippet": " ".join(snippet.split())[:160]})
        M.logout()
        return out
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ─── calendar (read-only, secret iCal URL; cached ~30 min — the feed is large) ───
_CAL_CACHE = {"cal": None, "ts": 0.0}


def _load_calendar():
    import time
    url = env_val("BOAZ_CALENDAR_ICS_URL")
    if not url:
        return None, "חסר BOAZ_CALENDAR_ICS_URL ב-env"
    now = time.time()
    if _CAL_CACHE["cal"] is not None and now - _CAL_CACHE["ts"] < 1800:
        return _CAL_CACHE["cal"], None
    try:
        import urllib.request
        import icalendar
        data = urllib.request.urlopen(url, timeout=40).read()
        cal = icalendar.Calendar.from_ical(data)
        _CAL_CACHE["cal"], _CAL_CACHE["ts"] = cal, now
        return cal, None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def fetch_calendar(days=7):
    """Upcoming events in the next `days` days (recurring expanded): [{start,end,summary,location}]."""
    cal, err = _load_calendar()
    if err:
        return {"error": err}
    try:
        import datetime as _dt
        import recurring_ical_events
        today = _dt.date.today()
        evs = recurring_ical_events.of(cal).between(today, today + _dt.timedelta(days=max(1, min(days, 60))))
        out = []
        for e in evs:
            s = e.get("DTSTART").dt
            en = e.get("DTEND").dt if e.get("DTEND") else None
            out.append({"start": str(s)[:16], "end": str(en)[:16] if en else "",
                        "summary": str(e.get("SUMMARY") or ""), "location": str(e.get("LOCATION") or "")})
        out.sort(key=lambda x: x["start"])
        return out
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ─── conversational agent (free text → Ran understands, replies, can act) ───
SYSTEM = (
    "אתה רן, העוזר האישי של בועז. אתה מנהל את המטלות שלו במערכת BoazTask. "
    "כשבועז כותב לך בחופשי — הבן, ענה קצר ובעברית, ובמידת הצורך השתמש בכלים כדי להציג/ליצור/לעדכן מטלות, לקרוא את המייל שלו, או לקרוא את היומן שלו. "
    "ערכים חוקיים: urgency ∈ {דחוף, גבוה, בינוני, נמוך}; status ∈ {חדש, בטיפול, הושלם, בוטל}. "
    "## תפקיד המרכזן (Front Door) — חלק ממי שאתה\n"
    "אתה גם נקודת הכניסה של בועז לכל הסוכנים. שלושה דברים שאתה עושה תמיד, לצד ניהול המטלות:\n"
    "1. **מאזין** — כשעולה בשיחה דבר-מה שצריך לעשות (מטלה/החלטה/מעקב), רשום אותו עם create_task ואשר בקצרה. אל תיתן לדברים ליפול בין הכיסאות.\n"
    "2. **מנתב/מצרף מומחים** — כששאלה שייכת לסוכן מומחה (זמינות/תקלות מתקנים → עומרי; שירות לקוחות מתקנים → גיא):\n"
    "   • לשאלה נקודתית — העֵר אותו עם ask_specialist (agent 'omri'/'guy') והחזר את תשובתו, וציין שהיא מהמומחה.\n"
    "   • כשבועז מבקש **לצרף/להוסיף** מישהו לשיחה — קרא ל-invite_to_room (שם בעברית, למשל 'עומרי') **מיד ובלי לשאול שאלות**. הוא יהפוך למשתתף וידבר בעצמו מההודעה הבאה. אשר בקצרה שצירפת.\n"
    "3. **מנהל שיחות** — אם בועז מבקש, השתמש ב-list_conversations להצגת השיחות וב-delete_conversation למחיקה לפי id.\n"
    "לפני יצירה/עדכון משמעותיים — ודא שהבנת נכון, אבל אל תהיה מסורבל. אתה ידידותי ותכליתי. "
    "צורת העבודה שלך מתועדת בקובץ הסגנון שמוצג לך למטה — ציית לה תמיד (טון, פורמט דיווחים, ברירות מחדל). "
    "כשבועז מבקש לשנות או להוסיף כלל עבודה (למשל איך ייראה דיווח) — עדכן את הקובץ עם הכלי save_working_style "
    "(החזר את התוכן המלא והמעודכן), ואז אשר לו בקצרה מה נשמר. "
    "אם אתה מזהה בעצמך הרגל או העדפה חוזרת — הצע אותה לבועז ושמור רק אחרי אישור. "
    "לעולם אל תשנה את צורת העבודה בלי שבועז ביקש או אישר."
)
TOOLS = [
    {"name": "read_email", "description": "קרא מיילים אחרונים מתיבת הדואר של בועז (boazen@gmail.com). unread_only=true למיילים שלא נקראו; limit = כמה (ברירת מחדל 10).",
     "input_schema": {"type": "object", "properties": {
         "limit": {"type": "integer"}, "unread_only": {"type": "boolean"}}}},
    {"name": "read_calendar", "description": "קרא את האירועים הקרובים מהיומן של בועז. days = כמה ימים קדימה (ברירת מחדל 7).",
     "input_schema": {"type": "object", "properties": {"days": {"type": "integer"}}}},
    {"name": "list_tasks", "description": "החזר את כל המטלות הקיימות (לסינון/סיכום/חיפוש).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "create_task", "description": "צור מטלה חדשה.",
     "input_schema": {"type": "object", "properties": {
         "subject": {"type": "string"}, "sub_subject": {"type": "string"},
         "description": {"type": "string"},
         "urgency": {"type": "string", "enum": ["דחוף", "גבוה", "בינוני", "נמוך"]},
         "category1": {"type": "string"}, "category2": {"type": "string"},
         "immediate": {"type": "boolean"}}, "required": ["subject"]}},
    {"name": "update_task", "description": "עדכן מטלה קיימת לפי id (רק שדות לשינוי).",
     "input_schema": {"type": "object", "properties": {
         "task_id": {"type": "integer"}, "subject": {"type": "string"},
         "sub_subject": {"type": "string"}, "description": {"type": "string"},
         "urgency": {"type": "string", "enum": ["דחוף", "גבוה", "בינוני", "נמוך"]},
         "status": {"type": "string", "enum": ["חדש", "בטיפול", "הושלם", "בוטל"]},
         "category1": {"type": "string"}, "category2": {"type": "string"},
         "immediate": {"type": "boolean"}}, "required": ["task_id"]}},
    {"name": "save_working_style",
     "description": "עדכן את קובץ צורת העבודה של רן (ran_style.md) — הכללים שמעצבים איך אתה מתנהג ומדווח. "
                    "content = התוכן המלא והמעודכן של הקובץ (Markdown). אתה רואה את הגרסה הנוכחית בהוראות — ערוך אותה והחזר בשלמותה. "
                    "השתמש כשבועז מבקש לשנות/להוסיף כלל עבודה, או אחרי שאישר הצעה שלך.",
     "input_schema": {"type": "object", "properties": {
         "content": {"type": "string"}}, "required": ["content"]}},
    {"name": "ask_specialist",
     "description": "העֵר סוכן מומחה לשאלה חד-פעמית והחזר את תשובתו (אתה מתווך). agent = 'omri' (זמינות/תקלות מתקני חניה) או 'guy' (שירות לקוחות מתקנים). "
                    "question = השאלה בעברית. השתמש לשאלה נקודתית. אם בועז רוצה שהמומחה ידבר ישירות בחדר — השתמש ב-invite_to_room במקום.",
     "input_schema": {"type": "object", "properties": {
         "agent": {"type": "string", "enum": ["omri", "guy"]},
         "question": {"type": "string"}}, "required": ["agent", "question"]}},
    {"name": "invite_to_room",
     "description": "צרף סוכן כמשתתף בחדר הנוכחי כך שידבר ישירות בשיחה (לא דרכך). "
                    "agent = שם הסוכן בעברית (למשל 'עומרי', 'גיא', 'רונית'). "
                    "כשבועז מבקש לצרף/להוסיף מישהו לשיחה — קרא לזה מיד, בלי לשאול שאלות.",
     "input_schema": {"type": "object", "properties": {
         "agent": {"type": "string"}}, "required": ["agent"]}},
    {"name": "list_conversations",
     "description": "החזר את כל השיחות השמורות (id, כותרת, עדכון אחרון, מספר הודעות). להצגה לפני מחיקה.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "delete_conversation",
     "description": "מחק שיחה שמורה לפי id. room_id = המזהה מ-list_conversations. השתמש רק כשבועז מבקש למחוק.",
     "input_schema": {"type": "object", "properties": {
         "room_id": {"type": "string"}}, "required": ["room_id"]}},
]


def exec_tool(name, inp):
    try:
        if name == "read_email":
            return fetch_emails(inp.get("limit", 10), bool(inp.get("unread_only", False)))
        if name == "read_calendar":
            return fetch_calendar(inp.get("days", 7))
        if name == "list_tasks":
            return api_list()[:60]
        if name == "create_task":
            r = api_create(inp)
            return r.json() if r.status_code == 201 else {"error": r.status_code, "body": r.text[:200]}
        if name == "update_task":
            tid = inp.pop("task_id")
            r = requests.put(API + str(tid), headers={**AUTH, "Content-Type": "application/json"},
                             data=json.dumps(inp, ensure_ascii=False).encode("utf-8"), timeout=30)
            return r.json() if r.status_code == 200 else {"error": r.status_code, "body": r.text[:200]}
        if name == "save_working_style":
            return save_style(inp.get("content", ""))
        if name == "ask_specialist":
            if not ran_orchestrator:
                return {"error": "שכבת המרכזן (ran_orchestrator) לא זמינה"}
            return ran_orchestrator.summon_specialist(inp.get("agent", ""), inp.get("question", ""))
        if name == "invite_to_room":
            if not ran_orchestrator:
                return {"error": "שכבת המרכזן (ran_orchestrator) לא זמינה"}
            return ran_orchestrator.invite_to_room(getattr(_ctx, "room_id", None), inp.get("agent", ""))
        if name == "list_conversations":
            return ran_orchestrator.list_conversations() if ran_orchestrator else {"error": "אין שכבת מרכזן"}
        if name == "delete_conversation":
            return ran_orchestrator.delete_conversation(inp.get("room_id", "")) if ran_orchestrator else {"error": "אין שכבת מרכזן"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    return {"error": "unknown tool"}


def run_ran_agent(history):
    """Anthropic tool-use loop. history = list of {role, content(str)}. Returns reply text."""
    if not ANTHROPIC_KEY:
        return "מפתח ה-AI לא מוגדר — אני יכול לעבוד עם הכפתורים בינתיים."
    style = load_style()
    system = SYSTEM + ("\n\n## צורת העבודה שלך (זיכרון — ציית לזה):\n" + style if style else "")
    messages = [dict(m) for m in history]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    for _ in range(6):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": "claude-sonnet-4-6", "max_tokens": 1024, "system": system,
                      "tools": TOOLS, "messages": messages}, timeout=60,
            ).json()
        except Exception as e:  # noqa: BLE001
            return f"שגיאה בחיבור ל-AI: {e}"
        blocks = resp.get("content", [])
        if not blocks:
            return resp.get("error", {}).get("message", "לא קיבלתי תשובה.")
        messages.append({"role": "assistant", "content": blocks})
        tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
        if not tool_uses:
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text") or "✓"
        results = [{"type": "tool_result", "tool_use_id": tu["id"],
                    "content": json.dumps(exec_tool(tu["name"], dict(tu.get("input", {}))), ensure_ascii=False)[:3500]}
                   for tu in tool_uses]
        messages.append({"role": "user", "content": results})
    return "סיימתי כמה צעדים אבל לא הגעתי לתשובה סופית — נסה לנסח שוב."


# הקשר החדר הנוכחי (per-thread — ה-comms מריץ סבבים ב-threads) כדי ש-invite_to_room
# ידע לאיזה חדר לצרף.
_ctx = threading.local()


def chat(history, room_id=None):
    """נקודת כניסה לחדרי ה-comms (כמו ronit_core.chat). מקבל היסטוריית הודעות
    בפורמט [{role, content}] ומחזיר טקסט תשובה — אותו מוח, אותה צורת עבודה (ran_style),
    ואותם כלים (מטלות, מייל, יומן, זימון/צירוף מומחים) כמו בבוט החי."""
    _ctx.room_id = room_id
    try:
        return run_ran_agent([dict(m) for m in history])
    finally:
        _ctx.room_id = None


# ─── reports ───
def _immediate_report():
    tasks = [t for t in api_list() if t.get("immediate") and t.get("status") in OPEN]
    if not tasks:
        return _resp("⚡ אין מטלות מיידיות פתוחות.", menu=True)
    lines = [f"⚡ *מטלות מיידיות* ({len(tasks)})", ""]
    for t in sorted(tasks, key=lambda x: x.get("urgency", "")):
        lines.append(f"{URG_ICON.get(t.get('urgency'), '⚪')} *{t.get('subject')}*"
                     f"{' · ' + t['sub_subject'] if t.get('sub_subject') else ''}"
                     f"{' · אחראי: ' + t['category1'] if t.get('category1') else ''}  #{t.get('id')}")
    return _resp("\n".join(lines)[:4000], menu=True)


def _by_responsible_report():
    tasks = [t for t in api_list() if t.get("status") in OPEN]
    if not tasks:
        return _resp("📋 אין מטלות פתוחות.", menu=True)
    groups = {}
    for t in tasks:
        groups.setdefault(t.get("category1") or "ללא אחראי", []).append(t)
    lines = [f"📋 *מטלות לפי אחראי* ({len(tasks)})", ""]
    for resp, items in groups.items():
        lines.append(f"👤 *{resp}* ({len(items)})")
        for t in items:
            lines.append(f"  {URG_ICON.get(t.get('urgency'), '⚪')} {t.get('subject')} · {t.get('status')}  #{t.get('id')}")
        lines.append("")
    return _resp("\n".join(lines)[:4000], menu=True)


def _report_via_brain(kind):
    """דוח כפתור שעובר דרך המוח: הנתונים נשלפים דטרמיניסטית (מדויק), רן מעצב לפי ran_style.md.

    נופל חזרה לדוח הקוד הקבוע אם אין מפתח AI.
    """
    if kind == "immediate":
        tasks = [t for t in api_list() if t.get("immediate") and t.get("status") in OPEN]
        title = "מטלות מיידיות פתוחות"
        fallback = _immediate_report
    else:  # by_owner
        tasks = [t for t in api_list() if t.get("status") in OPEN]
        title = "מטלות פתוחות לפי אחראי (category1)"
        fallback = _by_responsible_report
    if not ANTHROPIC_KEY:
        return fallback()
    data = [{k: t.get(k) for k in ("id", "subject", "sub_subject", "urgency", "status", "category1", "immediate")}
            for t in tasks]
    instruction = (
        f"הצג דיווח: {title}. הנה כל המטלות הרלוונטיות — אל תשמיט אף אחת ואל תמציא נתונים: "
        f"{json.dumps(data, ensure_ascii=False)}. "
        "עצב את הדיווח לפי צורת העבודה שלך (ran_style.md). בלי כוכביות Markdown — השתמש באימוג'ים ובמרווחים. "
        "אם הרשימה ריקה — אמור זאת במשפט קצר."
    )
    reply = run_ran_agent([{"role": "user", "content": instruction}])
    return _resp(reply, menu=True, md=False)


# ─── structured "new task" wizard (channel-agnostic state machine) ───
def _nt_step(session, text):
    nt = session["nt"]
    step = session["step"]
    skip = text in ("/skip", "דלג")
    if step == "subject":
        nt["subject"] = text
        session["step"] = "sub"
        return _resp("תת-נושא? (או /skip)")
    if step == "sub":
        nt["sub_subject"] = "" if skip else text
        session["step"] = "desc"
        return _resp("תיאור? (או /skip)")
    if step == "desc":
        nt["description"] = "" if skip else text
        session["step"] = "urg"
        return _resp("בחר דחיפות:", buttons=URG_BUTTONS)
    if step == "urg":
        if text.startswith("urg_"):
            nt["urgency"] = URG_MAP.get(text.split("_")[1], "בינוני")
            session["step"] = "cat1"
            return _resp(f"דחיפות: {nt['urgency']}\nמי האחראי? (או /skip)")
        return _resp("בחר דחיפות מהכפתורים:", buttons=URG_BUTTONS)
    if step == "cat1":
        nt["category1"] = "" if skip else text
        session["step"] = "cat2"
        return _resp("קטגוריה נוספת? (או /skip)")
    if step == "cat2":
        nt["category2"] = "" if skip else text
        return _nt_save(session)
    return start(session)


def _nt_save(session):
    nt = session.pop("nt", {})
    session.pop("flow", None)
    session.pop("step", None)
    r = api_create(nt)
    if r.status_code == 201:
        t = r.json()
        return _resp(f"✅ נוצרה מטלה #{t['id']}: *{t['subject']}*", menu=True)
    return _resp(f"❌ שגיאה ({r.status_code})", menu=True)


def _quick_step(session, text):
    session.pop("flow", None)
    session.pop("step", None)
    payload = analyze_quick(text)
    r = api_create(payload)
    if r.status_code == 201:
        t = r.json()
        sub = ("\n├ " + t["sub_subject"]) if t.get("sub_subject") else ""
        return _resp(f"✅ נוצרה מטלה #{t['id']}\n📌 *{t['subject']}*{sub}"
                     f"\n├ דחיפות: {t.get('urgency')}\n└ {(t.get('description', '') or '')[:120]}", menu=True)
    return _resp(f"❌ שגיאה ({r.status_code})", menu=True)


# ─── public entry points (the channel calls only these) ───
def start(session):
    """Reset the active flow and show the greeting + main menu."""
    for k in ("flow", "nt", "step"):
        session.pop(k, None)
    return _resp("👋 *שלום בועז, אני רן.*\nבחר פעולה מהתפריט, או כתוב לי בחופשי:", menu=True)


def handle(session, text):
    """Process one inbound message (button id or free text) and return a Response."""
    text = (text or "").strip()

    if text in ("/cancel", "ביטול"):
        for k in ("flow", "nt", "step"):
            session.pop(k, None)
        return _resp("❌ בוטל.", menu=True)
    if text in ("/start", "start"):
        return start(session)

    # active structured flow takes precedence
    flow = session.get("flow")
    if flow == "new_task":
        return _nt_step(session, text)
    if flow == "quick":
        return _quick_step(session, text)

    # main-menu actions
    if text == "➕ מטלה חדשה":
        session["flow"], session["nt"], session["step"] = "new_task", {}, "subject"
        return _resp("➕ *מטלה חדשה*\n\nמה הנושא?")
    if text == "⚡ מטלה מהירה":
        session["flow"], session["step"] = "quick", "text"
        return _resp("⚡ *מטלה מהירה*\n\nכתוב מה צריך, ואני אנתח ואסדר:")
    if text == "⚡ מטלות מיידיות":
        return _report_via_brain("immediate")
    if text == "📋 מטלות לפי אחראי":
        return _report_via_brain("by_owner")

    # anything else → conversational agent (Ran understands & can act)
    hist = session.setdefault("chat", [])
    hist.append({"role": "user", "content": text})
    reply = run_ran_agent(hist)
    hist.append({"role": "assistant", "content": reply})
    del hist[:-12]  # keep last ~6 turns
    return _resp(reply, menu=True, md=False)


# ─── scheduled job: evening review (same brain & style as the live bot) ───
def evening_review():
    """Compose the daily evening review from open tasks, write it to output/ran/,
    and return {full, summary, path, count}. Uses run_ran_agent so the review
    speaks in the exact same voice as the live chat (ran_style.md)."""
    tasks = [t for t in api_list() if t.get("status") in OPEN]
    today = datetime.date.today().isoformat()
    count = len(tasks)
    if ANTHROPIC_KEY and tasks:
        data = [{k: t.get(k) for k in ("id", "subject", "sub_subject", "urgency", "status", "category1", "immediate")}
                for t in tasks]
        instruction = (
            f"חבר 'סקירת ערב' מ-{count} המטלות הפתוחות הבאות — אל תשמיט אף אחת ואל תמציא נתונים: "
            f"{json.dumps(data, ensure_ascii=False)}. "
            "סעיפים: 🔴 מיידי/דחוף (immediate=true או urgency דחוף/גבוה) · 📋 לפי נושא · 🎯 סדר עדיפויות למחר · 🤔 דורש את ההחלטה שלך. "
            "עברית, לפי צורת העבודה שלך (ran_style.md). "
            "בשורה האחרונה הוסף שורה שמתחילה ב-'TLDR:' עם תקציר במשפט אחד (כמה פתוחות, הדחוף ביותר, כמה מחכות להחלטה)."
        )
        full = run_ran_agent([{"role": "user", "content": instruction}])
    else:
        lines = [f"# 🌙 סקירת ערב — {today}", "", f"{count} מטלות פתוחות.", ""]
        lines += [f"- {URG_ICON.get(t.get('urgency'), '⚪')} {t.get('subject')} · {t.get('status')}  #{t.get('id')}" for t in tasks]
        lines.append(f"TLDR: {count} מטלות פתוחות.")
        full = "\n".join(lines)

    summary = next((l.split(":", 1)[1].strip() for l in full.splitlines()
                    if l.strip().upper().startswith("TLDR")), f"{count} מטלות פתוחות בסקירת הערב.")

    out_dir = os.path.join(VAULT, "output", "ran")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{today} Evening Review.md")
    header = f"---\ndate: {today}\ntype: ran-evening-review\nopen_tasks: {count}\n---\n\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + full.strip() + "\n")
    return {"full": full, "summary": summary, "path": path, "count": count}


def notify_telegram(text):
    """Proactive outbound push to Boaz via Ran's Telegram bot (does not conflict with polling)."""
    import urllib.request
    token = env_val("RAN_BOT_TOKEN")
    chat = env_val("RAN_TELEGRAM_CHAT_ID")
    if not token or not chat:
        return {"error": "missing RAN_BOT_TOKEN / RAN_TELEGRAM_CHAT_ID"}
    payload = json.dumps({"chat_id": chat, "text": text}).encode("utf-8")
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "evening-review":
        res = evening_review()
        push = notify_telegram(f"🌙 סקירת ערב מוכנה — {res['summary']}")
        print(f"[evening-review] {res['count']} open tasks → {res['path']} | telegram: {push}")
    else:
        print("usage: python ran_core.py evening-review")
