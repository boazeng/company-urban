"""זובין — מוח bespoke לסוכן התזמון.

שלושה דברים במוח אחד:
  • שיחה — עונה על לוח הזמנים מתוך Schedule.md (מי מתוזמן מתי, ניתוח, המלצות),
    עם מודעות לתאריך/שעה בשעון ישראל.
  • עריכה — באמצעות כלים (tool-use) הוא **מוסיף / מוחק / מעדכן** שורות ב-Schedule.md
    בפועל (לא רק ממליץ).
  • פעימה — בקשה מפורשת ("הרץ פעימה" / "רוץ עכשיו") מריצה את `/conductor` דרך claude -p.

נטען ע״י comms/backend/agents.py (BESPOKE) — מוח bespoke גובר על סוכן-פקודה.
הערה: זובין רץ על הבוקס ולכן עורך את עותק ה-Schedule.md שעל הבוקס (שאותו קורא
המנצח בפעימות). כדי לשקף את השינויים באתר/git — ראה deploy/pull-schedule-from-box.sh.
"""
import os
import re
import shutil
import subprocess
from datetime import datetime

import requests

try:  # שעון ישראל — נכון בלי תלות באזור-הזמן של השרת (הבוקס לרוב UTC)
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Asia/Jerusalem")
except Exception:  # noqa: BLE001 — אם tzdata חסר, ניפול לשעון המקומי
    _TZ = None

VAULT = os.environ.get("VAULT", r"C:/Users/User/Aiprojects/obsi_comp")
SHARED_ENV = os.environ.get("SHARED_ENV", r"C:/Users/User/Aiprojects/env/.env")
SCHEDULE_PATH = rf"{VAULT}/schedule/Schedule.md"
MODEL = "claude-sonnet-4-6"

# Python weekday(): שני=0 ... ראשון=6. השבוע העברי מתחיל בראשון.
_HEB_DAYS = {6: "ראשון", 0: "שני", 1: "שלישי", 2: "רביעי", 3: "חמישי", 4: "שישי", 5: "שבת"}

# כוונת "הרץ פעימה עכשיו" — פעלי-פעולה מפורשים בלבד, לא שאלות.
_PULSE = re.compile(
    r"(הרץ|תריץ|בצע|תבצע|run)(?:\s+\S+){0,2}\s+\S*(פעימ|conductor|מתוזמנ)"
    r"|פעימה\s+עכשיו|רוץ\s+עכשיו|הרץ\s+עכשיו",
    re.IGNORECASE,
)


def _env_val(key, path=SHARED_ENV):
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip("\"'")
    except FileNotFoundError:
        pass
    return ""


ANTHROPIC_KEY = _env_val("ANTHROPIC_API_KEY")


def _now_str():
    now = datetime.now(_TZ) if _TZ else datetime.now()
    tz = " (שעון ישראל)" if _TZ else ""
    return f"{now:%Y-%m-%d %H:%M}, יום {_HEB_DAYS[now.weekday()]}{tz}"


def _schedule_text():
    try:
        return open(SCHEDULE_PATH, encoding="utf-8").read()
    except OSError:
        return "(לא הצלחתי לקרוא את לוח הזמנים)"


# ── עריכת טבלת לוח-הזמנים (Schedule.md) ─────────────────────────────────────
def _cells(line):
    return [p.strip() for p in line.strip().strip("|").split("|")]


def _load_table():
    """אתר את טבלת התזמון ב-Schedule.md. מחזיר מבנה לעריכה, או None."""
    try:
        lines = open(SCHEDULE_PATH, encoding="utf-8").read().split("\n")
    except OSError:
        return None
    hdr = next((i for i, ln in enumerate(lines)
                if ln.strip().startswith("|") and "סוכן" in ln and "פקודה" in ln), None)
    if hdr is None:
        return None
    cols = _cells(lines[hdr])
    i = hdr + 2  # דלג על שורת הכותרת ושורת ההפרדה
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append(i)
        i += 1
    return {"lines": lines, "hdr": hdr, "rows": rows, "cols": cols}


def _row_dict(line, cols):
    vals = _cells(line)
    return {c: (vals[j] if j < len(vals) else "") for j, c in enumerate(cols)}


def _fmt_row(d, cols):
    return "| " + " | ".join(d.get(c, "") or "" for c in cols) + " |"


def _norm(s):
    return (s or "").replace("`", "").strip()


def _matches(row, crit):
    return all(_norm(v) in _norm(row.get(k, "")) for k, v in crit.items() if v)


def _write_lines(lines):
    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _tool_add(inp):
    t = _load_table()
    if not t:
        return "לא הצלחתי לקרוא את טבלת לוח-הזמנים."
    cmd = (inp.get("command") or "").strip()
    if cmd and not cmd.startswith("`"):
        cmd = f"`{cmd}`"
    d = {
        "סוכן": inp.get("agent", ""),
        "פקודה": cmd,
        "טריגר": inp.get("trigger") or "מתוזמן",
        "מתי": inp.get("when", ""),
        "ימים": inp.get("days", ""),
        "בעלים": inp.get("owner", ""),
        "סטטוס": inp.get("status") or "פעיל",
    }
    line = _fmt_row(d, t["cols"])
    at = (t["rows"][-1] + 1) if t["rows"] else (t["hdr"] + 2)
    t["lines"].insert(at, line)
    _write_lines(t["lines"])
    return f"✅ נוספה שורה:\n{line}"


def _crit_from(inp):
    crit = {"סוכן": inp.get("agent", "")}
    for key, col in (("when", "מתי"), ("days", "ימים"), ("command", "פקודה")):
        if inp.get(key):
            crit[col] = inp[key]
    return {k: v for k, v in crit.items() if v}


def _tool_remove(inp):
    t = _load_table()
    if not t:
        return "לא הצלחתי לקרוא את טבלת לוח-הזמנים."
    crit = _crit_from(inp)
    if not crit:
        return "צריך לפחות מזהה אחד (סוכן/יום/שעה) כדי למחוק."
    matched = [i for i in t["rows"] if _matches(_row_dict(t["lines"][i], t["cols"]), crit)]
    if not matched:
        return "לא נמצאה שורה תואמת למחיקה."
    removed = [t["lines"][i] for i in matched]
    for i in sorted(matched, reverse=True):
        del t["lines"][i]
    _write_lines(t["lines"])
    return f"🗑️ נמחקו {len(removed)} שורות:\n" + "\n".join(removed)


def _tool_update(inp):
    t = _load_table()
    if not t:
        return "לא הצלחתי לקרוא את טבלת לוח-הזמנים."
    crit = _crit_from(inp)
    if not crit:
        return "צריך לפחות מזהה אחד (סוכן/יום/שעה) כדי לעדכן."
    changes = {}
    for key, col in (("new_when", "מתי"), ("new_days", "ימים"),
                     ("new_status", "סטטוס"), ("new_owner", "בעלים")):
        if inp.get(key):
            changes[col] = inp[key]
    if inp.get("new_command"):
        c = inp["new_command"].strip()
        changes["פקודה"] = c if c.startswith("`") else f"`{c}`"
    if not changes:
        return "לא צוין מה לעדכן."
    matched = [i for i in t["rows"] if _matches(_row_dict(t["lines"][i], t["cols"]), crit)]
    if not matched:
        return "לא נמצאה שורה תואמת לעדכון."
    after = []
    for i in matched:
        d = _row_dict(t["lines"][i], t["cols"])
        d.update(changes)
        t["lines"][i] = _fmt_row(d, t["cols"])
        after.append(t["lines"][i])
    _write_lines(t["lines"])
    return f"✏️ עודכנו {len(after)} שורות:\n" + "\n".join(after)


TOOLS = [
    {
        "name": "add_event",
        "description": "הוסף שורה חדשה ללוח הזמנים (Schedule.md).",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "שם הסוכן/המטלה כפי שיוצג בעמודת 'סוכן'"},
                "command": {"type": "string", "description": "הפקודה, למשל /parking-leads holon"},
                "when": {"type": "string", "description": "שעה HH:MM, או ריק עבור זמן-אמת"},
                "days": {"type": "string", "description": "יומי / יום בשבוע (ראשון..) / רשימה"},
                "owner": {"type": "string", "description": "הבעלים האחראי"},
                "trigger": {"type": "string", "description": "מתוזמן (ברירת מחדל) או זמן-אמת"},
                "status": {"type": "string", "description": "פעיל (ברירת מחדל) / מתוכנן / כבוי"},
            },
            "required": ["agent", "command", "when", "days", "owner"],
        },
    },
    {
        "name": "remove_event",
        "description": "מחק שורות מלוח הזמנים. ציין מזהים מספיק ספציפיים (סוכן + יום/שעה) כדי לא למחוק יותר מדי.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "שם הסוכן/המטלה (תת-מחרוזת)"},
                "when": {"type": "string", "description": "שעה לסינון (אופציונלי)"},
                "days": {"type": "string", "description": "יום לסינון (אופציונלי)"},
                "command": {"type": "string", "description": "פקודה לסינון (אופציונלי)"},
            },
            "required": ["agent"],
        },
    },
    {
        "name": "update_event",
        "description": "עדכן שורות קיימות (שעה/ימים/סטטוס/בעלים/פקודה). זהה את השורה לפי סוכן + יום/שעה.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "שם הסוכן לזיהוי"},
                "when": {"type": "string", "description": "שעה לזיהוי (אופציונלי)"},
                "days": {"type": "string", "description": "יום לזיהוי (אופציונלי)"},
                "new_when": {"type": "string"},
                "new_days": {"type": "string"},
                "new_status": {"type": "string", "description": "פעיל / מתוכנן / כבוי"},
                "new_owner": {"type": "string"},
                "new_command": {"type": "string"},
            },
            "required": ["agent"],
        },
    },
]

_TOOL_FNS = {"add_event": _tool_add, "remove_event": _tool_remove, "update_event": _tool_update}


def _last_user(history):
    for m in reversed(history):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _run_pulse():
    """הרץ פעימת מנצח אמיתית — claude -p /conductor (כמו cmd_brain)."""
    exe = shutil.which("claude")
    if not exe:
        return "(זובין: claude CLI לא נמצא — פעימה זמינה על השרת/מקומית)"
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        out = subprocess.run(
            [exe, "-p", "/conductor"], capture_output=True, text=True,
            encoding="utf-8", timeout=180, cwd=VAULT, env=env,
        )
        body = (out.stdout or "").strip() or (out.stderr or "").strip() or "(אין תשובה)"
        return f"🎼 הרצתי פעימת תזמון:\n\n{body}"
    except subprocess.TimeoutExpired:
        return "(זובין לא סיים את הפעימה בזמן)"
    except Exception as e:  # noqa: BLE001
        return f"(שגיאה בפעימה: {e})"


SYSTEM = (
    "אתה **זובין**, המנצח — סוכן התזמון של חברת הסוכנים. אתה מנהל את לוח הזמנים "
    "(Schedule.md) **ויכול לערוך אותו בפועל** דרך הכלים: add_event / remove_event / "
    "update_event. כשבועז מבקש להוסיף/למחוק/לשנות אירוע — בצע זאת בכלי המתאים, אל "
    "תסתפק בהמלצה. דבר עברית, תכליתי וקצר. עמודות הטבלה: סוכן · פקודה · טריגר · מתי "
    "(HH:MM) · ימים (יומי/ראשון.. /רשימה) · בעלים · סטטוס (פעיל/מתוכנן/כבוי). "
    "כשמוחקים/מעדכנים — זהה את השורה בצורה ספציפית (סוכן + יום/שעה) כדי לא לפגוע "
    "בשורות אחרות, ואשר לבועז בקצרה מה בוצע. כשנשאל על 'עכשיו'/'מחר'/'היום' — חשב לפי "
    "הזמן הנוכחי שמצורף. לפעימה אמיתית בקש 'הרץ פעימה'. עיקרון-על: אדם-בלולאה.\n\n"
    "=== הזמן הנוכחי ===\n{now}\n\n=== לוח הזמנים הנוכחי (schedule/Schedule.md) ===\n{schedule}"
)


def _api(messages, system):
    return requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": MODEL, "max_tokens": 1200, "system": system,
              "tools": TOOLS, "messages": messages},
        timeout=60,
    ).json()


def chat(history, room_id=None):  # room_id לחתימה אחידה
    user = _last_user(history)
    if _PULSE.search(user or ""):
        return _run_pulse()
    if not ANTHROPIC_KEY:
        return "(זובין: מפתח ה-AI לא מוגדר.)"

    messages = [dict(m) for m in history]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    if not messages:
        return "לא קיבלתי הודעה."

    for _ in range(6):  # לולאת כלים — מספר סבבי עריכה לכל היותר
        system = SYSTEM.format(now=_now_str(), schedule=_schedule_text())
        try:
            resp = _api(messages, system)
        except Exception as e:  # noqa: BLE001
            return f"שגיאה בחיבור ל-AI: {e}"
        blocks = resp.get("content")
        if not blocks:
            return resp.get("error", {}).get("message", "לא קיבלתי תשובה.")

        tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
        if not tool_uses:
            return "".join(b.get("text", "") for b in blocks if b.get("type") == "text") or "✓"

        messages.append({"role": "assistant", "content": blocks})
        results = []
        for tu in tool_uses:
            fn = _TOOL_FNS.get(tu.get("name"))
            out = fn(tu.get("input") or {}) if fn else f"(כלי לא מוכר: {tu.get('name')})"
            results.append({"type": "tool_result", "tool_use_id": tu.get("id"), "content": out})
        messages.append({"role": "user", "content": results})

    return "(זובין: יותר מדי שלבי עריכה — נסה שוב בבקשה ממוקדת יותר.)"
