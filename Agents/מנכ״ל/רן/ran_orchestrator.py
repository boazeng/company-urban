"""
ran_orchestrator — שכבת המרכזן (Front Door) של רן.

שני תפקידים, מעבר לעוזר-האישי הרגיל (ראה structure/Orchestration.md):

1. **ניתוב לסוכני מומחה** — רן מזהה בקשה ששייכת למומחה (עומרי לזמינות, גיא לשירות),
   "מעיר" אותו דרך `claude -p "/<agent> <שאלה>"`, ומחזיר את התשובה. summon_specialist().
2. **חנות שיחות (rooms)** — שיחות נשמרות לדיסק. רן **מצורף אוטומטית לכל חדר**
   (RAN_AUTO_JOIN) — כך שעל השרת הוא "מוכנס לחדר" מאליו. אפשר למחוק שיחות.

המודול channel-agnostic: גם הבוט וגם CLI/סוכני המשנה קוראים לאותן פונקציות.
"""
import os
import json
import shutil
import subprocess
import datetime

VAULT = r"C:/Users/User/Aiprojects/obsi_comp"
ROOMS_DIR = os.path.join(VAULT, "output", "ran", "conversations")
COMMS_API = "http://localhost:5181"  # מערכת החדרים (comms) — לצירוף משתתפים

# על השרת רן מוכנס אוטומטית לכל חדר חדש (זה ה-vision: "רן מצטרף לכל שיחה").
RAN_AUTO_JOIN = True

# ── טבלת ניתוב — מראָה של structure/Orchestration.md (מקור-האמת האנושי) ──
SPECIALISTS = {
    "omri": {"name": "עומרי", "command": "/omri",
             "keywords": ["זמינות", "תקול", "מושבת", "השבתה", "מתקן", "שמיש"]},
    "guy":  {"name": "גיא", "command": "/guy",
             "keywords": ["קריאת שירות", "דיווח תקלה", "לקוח", "שירות"]},
}


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


# ─── ניתוב + זימון מומחים ───
def route(text):
    """מחזיר את מפתח הסוכן המתאים לטקסט (omri/guy), או None אם זה לרן עצמו."""
    t = text or ""
    for key, spec in SPECIALISTS.items():
        if any(kw in t for kw in spec["keywords"]):
            return key
    return None


def summon_specialist(agent_key, question, timeout=180):
    """מעיר סוכן מומחה דרך claude -p ומחזיר {agent, answer} או {error}."""
    spec = SPECIALISTS.get(agent_key)
    if not spec:
        return {"error": f"אין סוכן בשם '{agent_key}'. זמינים: {', '.join(SPECIALISTS)}"}
    # resolve the real executable — ב-Windows זה claude.CMD, לא "claude" החשוף
    exe = shutil.which("claude")
    if not exe:
        return {"error": "claude CLI לא נמצא — זמין על השרת/מקומית עם Claude Code מותקן"}
    prompt = f"{spec['command']} {question}".strip()
    # אם רן רץ במקרה בתוך סשן Claude Code — הסר את הסימון כדי ש-claude -p לא יסרב על "סשן מקונן".
    child_env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        out = subprocess.run(
            [exe, "-p", prompt],
            capture_output=True, text=True, encoding="utf-8",
            timeout=timeout, cwd=VAULT, env=child_env,
        )
        ans = (out.stdout or "").strip() or (out.stderr or "").strip()
        return {"agent": spec["name"], "answer": (ans or "(אין תשובה)")[:3500]}
    except subprocess.TimeoutExpired:
        return {"error": f"{spec['name']} לא ענה בזמן ({timeout}s)"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ─── צירוף סוכן לחדר comms (רן מצרף מומחה כמשתתף, לא רק מתשאל) ───
def invite_to_room(room_id, agent):
    """מצרף סוכן כמשתתף בחדר comms הנוכחי — הוא יוכל לדבר ישירות בשיחה."""
    if not room_id:
        return {"error": "אין חדר נוכחי — הצירוף עובד רק בתוך חדר comms"}
    try:
        import requests
        r = requests.post(f"{COMMS_API}/rooms/{room_id}/participants",
                          json={"agent": agent}, timeout=15)
        if r.status_code == 200:
            return {"ok": True, "added": agent}
        return {"error": f"{r.status_code}: {r.text[:200]}"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ─── חנות שיחות (rooms) ───
def _room_path(room_id):
    return os.path.join(ROOMS_DIR, f"{room_id}.json")


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(convo):
    os.makedirs(ROOMS_DIR, exist_ok=True)
    with open(_room_path(convo["id"]), "w", encoding="utf-8") as f:
        json.dump(convo, f, ensure_ascii=False, indent=2)


def open_conversation(room_id, title=None):
    """פותח/מחזיר חדר. רן מצורף אוטומטית (RAN_AUTO_JOIN) — 'מוכנס לחדר'."""
    p = _room_path(room_id)
    if os.path.exists(p):
        return _load(p)
    convo = {
        "id": str(room_id),
        "title": title or f"שיחה {room_id}",
        "participants": (["רן"] if RAN_AUTO_JOIN else []),
        "created": _now(), "updated": _now(), "messages": [],
    }
    _save(convo)
    return convo


def append_message(room_id, role, text):
    """מוסיף הודעה לחדר (יוצר אותו עם רן מצורף אם לא קיים). role = user/assistant."""
    p = _room_path(room_id)
    convo = _load(p) if os.path.exists(p) else open_conversation(room_id)
    convo["messages"].append({"role": role, "text": (text or "")[:4000], "at": _now()})
    convo["updated"] = _now()
    # כותרת מההודעה הראשונה של בועז
    if convo["title"].startswith("שיחה ") and role == "user" and text:
        convo["title"] = text.strip()[:40]
    _save(convo)
    return convo


def list_conversations():
    """כל השיחות, מהאחרונה: [{id, title, updated, messages}]."""
    if not os.path.isdir(ROOMS_DIR):
        return []
    out = []
    for fn in os.listdir(ROOMS_DIR):
        if not fn.endswith(".json"):
            continue
        try:
            c = _load(os.path.join(ROOMS_DIR, fn))
            out.append({"id": c["id"], "title": c.get("title", ""),
                        "updated": c.get("updated", ""), "messages": len(c.get("messages", []))})
        except Exception:  # noqa: BLE001
            pass
    out.sort(key=lambda x: x.get("updated", ""), reverse=True)
    return out


def delete_conversation(room_id):
    """מוחק שיחה אחת לפי id."""
    p = _room_path(room_id)
    if os.path.exists(p):
        os.remove(p)
        return {"ok": True, "deleted": str(room_id)}
    return {"error": f"שיחה '{room_id}' לא נמצאה"}


def delete_all_conversations():
    """מוחק את כל השיחות."""
    n = 0
    if os.path.isdir(ROOMS_DIR):
        for fn in os.listdir(ROOMS_DIR):
            if fn.endswith(".json"):
                os.remove(os.path.join(ROOMS_DIR, fn))
                n += 1
    return {"ok": True, "deleted": n}


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if not a or a[0] == "list":
        rows = list_conversations()
        if not rows:
            print("אין שיחות שמורות.")
        for c in rows:
            print(f"{c['id']:>14}  [{c['messages']:>3} הודעות]  {c['updated']:<16}  {c['title']}")
    elif a[0] == "delete" and len(a) > 1:
        print(delete_conversation(a[1]))
    elif a[0] == "delete-all":
        print(delete_all_conversations())
    elif a[0] == "summon" and len(a) > 2:
        print(json.dumps(summon_specialist(a[1], " ".join(a[2:])), ensure_ascii=False, indent=2))
    else:
        print("usage: ran_orchestrator.py [list | delete <id> | delete-all | summon <omri|guy> <question>]")
