"""
ronit_core — המוח של רונית, סמנכ״לית השיווק (channel-agnostic).

מחזיק את כל ההיגיון של רונית בלי לדעת כלום על ערוץ ההפצה. כל ערוץ (מערכת
התקשורת באתר, ובהמשך טלגרם/וואטסאפ) קורא לאותו חוזה:

    chat(history) -> str          # תשובת רונית כטקסט

history = list של {"role": "user"|"assistant", "content": str}.

המוח מבוסס על אותו דפוס כמו ran_core: Anthropic API ישירות, מפתח מה-env
המשותף, ולולאת tool-use. הכלים של רונית הם קריאה בלבד (יעדים, מותגים,
תפוקות סוכני המשנה) — היא מכינה וממליצה; בועז מאשר (אדם-בלולאה).
"""
import os
import sys
import json
import requests

SHARED_ENV = os.environ.get("SHARED_ENV", r"C:/Users/User/Aiprojects/env/.env")
VAULT = os.environ.get("VAULT", r"C:/Users/User/Aiprojects/obsi_comp")
HERE = os.path.dirname(os.path.abspath(__file__))


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

# ─── זהות רונית (system) ───
SYSTEM = """אתה **רונית**, סמנכ״לית השיווק (CMO) של חברת הסוכנים.
את אחראית על כל נושא השיווק ועל כל הסוכנים שתחתייך (אולפן תוכן, רשתות חברתיות,
פרסום ממומן, לידים, אנליטיקה). את מתרגמת את יעדי החברה — הגדלת הכנסות והקטנת
תקורות — ליעדי שיווק מדידים, גוזרת מהם פעילויות, ומוודאת שעומדים בהם.

עקרון-העל שלך: **אדם-בלולאה**. את מכינה, ממליצה ומציגה אפשרויות — בועז מאשר.
שום דבר לא יוצא החוצה (פרסום, תקציב, פנייה ללקוח) בלי אישור מפורש שלו.

יש לך כלים לקריאת היעדים, המותגים ותפוקות סוכני המשנה — השתמשי בהם כדי לבסס
תשובות על המצב האמיתי, לא על ניחוש. אם נתון חסר — אמרי "טרם נמדד/הוגדר" במפורש.
דברי עברית, תכליתי וקצר, כמו מנהלת — ממוקדת תוצאות והחלטות."""


def load_style():
    p = os.path.join(HERE, "..", "ronit_style.md")
    try:
        return open(os.path.abspath(p), encoding="utf-8").read()
    except OSError:
        return ""


# ─── כלים (קריאה בלבד) ───
def _read(rel):
    try:
        return open(os.path.join(VAULT, rel), encoding="utf-8").read()
    except OSError as e:
        return f"(לא ניתן לקרוא {rel}: {e})"


def _list_marketing_outputs():
    base = os.path.join(VAULT, "output")
    agents = ["ronit", "content-studio", "social-publisher", "marketing-report",
              "parking-leads", "content-calendar"]
    out = {}
    for a in agents:
        d = os.path.join(base, a)
        if os.path.isdir(d):
            files = sorted(f for f in os.listdir(d) if not f.startswith(".gitkeep"))
            if files:
                out[a] = files[-5:]
    return out or {"info": "אין עדיין תפוקות מסוכני שיווק."}


TOOLS = [
    {"name": "read_marketing_goals", "description": "קריאת יעדי השיווק המפורטים (OKR, מותגים, KR).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_company_goals", "description": "קריאת טבלת יעדי הסוכנים הכלל-חברתית.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_brands", "description": "קריאת רישום המותגים.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "list_marketing_outputs", "description": "רשימת קבצי התפוקה האחרונים של סוכני השיווק.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_output_file", "description": "קריאת קובץ תפוקה ספציפי לפי נתיב יחסי תחת output/.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}},
                      "required": ["path"]}},
]


def exec_tool(name, args):
    try:
        if name == "read_marketing_goals":
            return {"content": _read("goals/Marketing-Goals.md")}
        if name == "read_company_goals":
            return {"content": _read("goals/Goals.md")}
        if name == "read_brands":
            return {"content": _read("brands/Brands.md")}
        if name == "list_marketing_outputs":
            return _list_marketing_outputs()
        if name == "read_output_file":
            rel = args.get("path", "").lstrip("/")
            if ".." in rel:
                return {"error": "נתיב לא חוקי"}
            return {"content": _read(os.path.join("output", rel))[:3500]}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    return {"error": "unknown tool"}


def chat(history):
    """לולאת tool-use של Anthropic. history = [{role, content(str)}]. מחזיר טקסט תשובה."""
    if not ANTHROPIC_KEY:
        return "מפתח ה-AI לא מוגדר (ANTHROPIC_API_KEY ב-env המשותף) — לא אוכל לענות עדיין."
    style = load_style()
    system = SYSTEM + ("\n\n## צורת העבודה שלך (זיכרון — ציית לזה):\n" + style if style else "")
    messages = [dict(m) for m in history]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    if not messages:
        return "לא קיבלתי הודעה."
    for _ in range(6):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": MODEL, "max_tokens": 1024, "system": system,
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
                    "content": json.dumps(exec_tool(tu["name"], dict(tu.get("input", {}))),
                                          ensure_ascii=False)[:3500]}
                   for tu in tool_uses]
        messages.append({"role": "user", "content": results})
    return "עברתי כמה צעדים אבל לא הגעתי לתשובה סופית — נסה לנסח שוב."


# ─── CLI לבדיקה מהירה ───
if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(chat([{"role": "user", "content": " ".join(sys.argv[1:])}]))
    else:
        print("רונית — צ׳אט בדיקה (Ctrl+C ליציאה)")
        hist = []
        while True:
            try:
                msg = input("\nאתה: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not msg:
                continue
            hist.append({"role": "user", "content": msg})
            reply = chat(hist)
            hist.append({"role": "assistant", "content": reply})
            print(f"\nרונית: {reply}")
