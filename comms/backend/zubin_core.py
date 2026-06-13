"""זובין — מוח bespoke לסוכן התזמון.

שני מצבים במוח אחד:
  • שיחה (ברירת מחדל) — עונה על לוח הזמנים מתוך Schedule.md (מי מתוזמן מתי,
    ניתוח, המלצות שינוי). role-driven, לא מפעיל כלום.
  • פעימה — כשבועז מבקש במפורש להריץ ("הרץ פעימה" / "רוץ עכשיו" / "בצע פעימה"),
    מריץ את `/conductor` האמיתי דרך claude -p (כמו cmd_brain).

נטען ע״י comms/backend/agents.py (BESPOKE) — מוח bespoke גובר על סוכן-פקודה.
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


def _now_str():
    now = datetime.now(_TZ) if _TZ else datetime.now()
    tz = " (שעון ישראל)" if _TZ else ""
    return f"{now:%Y-%m-%d %H:%M}, יום {_HEB_DAYS[now.weekday()]}{tz}"

# כוונת "הרץ פעימה עכשיו" — פעלי-פעולה מפורשים בלבד, לא שאלות.
# הפועל ואז עד 2 מילים ואז מילת מפתח (כדי לתפוס גם "תפעיל את התור").
_PULSE = re.compile(
    r"(הרץ|תריץ|הפעל|תפעיל|בצע|תבצע|run)(?:\s+\S+){0,2}\s+\S*(פעימ|תזמון|תור|conductor|מתוזמנ|סוכנ)"
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

SYSTEM = (
    "אתה **זובין**, המנצח — סוכן התזמון של חברת הסוכנים. אתה מנהל את לוח הזמנים "
    "ומפעיל את הסוכנים המתוזמנים. דבר עברית, תכליתי וקצר. אתה יכול: להסביר מי "
    "מתוזמן מתי, לנתח את הלוח, להמליץ על שינויי תזמון, ולומר מה צפוי לרוץ. עיקרון-על: "
    "אדם-בלולאה — אתה ממליץ, בועז מחליט. **אל תמציא** שורות לוח זמנים; התבסס אך ורק על "
    "לוח הזמנים שמצורף למטה. אם מבקשים ממך להריץ פעימה בפועל — אמור שתריץ; המערכת מפעילה "
    "את הפעימה בנפרד. כשנשאל על 'עכשיו'/'מחר'/'היום' — חשב לפי הזמן הנוכחי שמצורף.\n\n"
    "=== הזמן הנוכחי ===\n{now}\n\n=== לוח הזמנים הנוכחי (schedule/Schedule.md) ===\n{schedule}"
)


def _schedule_text():
    try:
        return open(SCHEDULE_PATH, encoding="utf-8").read()
    except OSError:
        return "(לא הצלחתי לקרוא את לוח הזמנים)"


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
    system = SYSTEM.format(now=_now_str(), schedule=_schedule_text())
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 900, "system": system, "messages": messages},
            timeout=60,
        ).json()
    except Exception as e:  # noqa: BLE001
        return f"שגיאה בחיבור ל-AI: {e}"
    blocks = resp.get("content", [])
    if not blocks:
        return resp.get("error", {}).get("message", "לא קיבלתי תשובה.")
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text") or "✓"
