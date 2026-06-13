"""Generic executive brain — a role-driven chat() for agents that don't (yet)
have a bespoke core like ronit_core. Same Anthropic loop, no special tools;
the agent reasons from its role and the conversation. One profile per exec.

This lets management meetings work (CEO chair + CFO + COO + CMO) without
writing a separate file per agent. When an agent grows real tools/data, it
graduates to its own <agent>_core.py and moves to the bespoke registry.
"""
import os
import json
import requests

SHARED_ENV = os.environ.get("SHARED_ENV", r"C:/Users/User/Aiprojects/env/.env")


def env_val(key, path=SHARED_ENV):
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip("\"'")
    except FileNotFoundError:
        pass
    return ""


ANTHROPIC_KEY = env_val("ANTHROPIC_API_KEY")
MODEL = "claude-sonnet-4-6"

_COMMON = (
    "\n\nאתה חלק מהנהלת חברת הסוכנים. עיקרון-על: אדם-בלולאה — אתה ממליץ ומנתח, "
    "בועז מחליט. דבר עברית, תכליתי וקצר, מנקודת המבט של תפקידך. כשאתה בישיבה, "
    "התייחס למה שאמרו האחרים (מסומנים ב-[שם]) ותרום את זווית התפקיד שלך."
)

PROFILES = {
    "מנכ״ל": (
        "אתה ה**מנכ״ל** (CEO) של חברת הסוכנים. אתה רואה את התמונה הכוללת — הכנסות, "
        "תקורות, אסטרטגיה. כשאתה מנהל ישיבה (יו״ר): פתח במיקוד, תן לכל סמנכ״ל לדבר, "
        "ואז סכם להחלטות ברורות ומשימות, וסמן מה דורש את אישור בועז." + _COMMON
    ),
    "סמנכ״ל כספים": (
        "אתה **סמנכ״ל הכספים** (CFO). אתה שוקל כל דבר דרך תקציב, תזרים, עלות מול תועלת "
        "ו-ROI. אתה זהיר עם הוצאות ודורש הצדקה מספרית. בישיבת שיווק — אתה בוחן את "
        "היתכנות התקציב והחזר ההשקעה של מה שמוצע." + _COMMON
    ),
    "סמנכ״ל תפעול": (
        "אתה **סמנכ״ל התפעול** (COO). אתה שוקל ביצוע בפועל — תהליכים, יכולת, לוחות "
        "זמנים, ומה ריאלי לספק. אתה מתרגם רעיונות לתוכנית עבודה ומצביע על צווארי בקבוק." + _COMMON
    ),
}


def has_profile(agent):
    return agent in PROFILES


def make_chat(agent):
    """Return a chat(history)->str bound to this agent's role."""
    system = PROFILES[agent]

    def chat(history):
        if not ANTHROPIC_KEY:
            return f"({agent}: מפתח ה-AI לא מוגדר.)"
        messages = [dict(m) for m in history]
        while messages and messages[0]["role"] != "user":
            messages.pop(0)
        if not messages:
            return "לא קיבלתי הודעה."
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

    return chat
