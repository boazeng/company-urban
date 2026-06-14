"""Command-agent brain — for agents whose intelligence is a Claude Code slash
command (e.g. /omri, /guy) run headless via `claude -p`. The comms analog of
exec_brain: it makes such agents first-class room participants that speak
directly in the room (not only via Ran relaying).

Adding a command-agent = one line in COMMANDS.

Heavy agents (deep research like דפנה) can't finish inside a chat turn — a real
market study can run 30min+. For those, a deep-research request runs DETACHED in
a background thread (no chat timeout); the room gets a fast acknowledgement now,
and the finished report is posted back into the room when it's ready.
"""
import os
import shutil
import subprocess
import threading

import db

VAULT = os.environ.get("VAULT", r"C:/Users/User/Aiprojects/obsi_comp")

COMMANDS = {
    "עומרי": "/omri",
    "גיא": "/guy",
    "דפנה": "/dafna",
    "דרור": "/dror",
}

# Agents whose deep mode is long-running → run detached + ack; never block the room.
HEAVY = {"דפנה"}
# A request containing any of these = a deep job (run detached). Otherwise = quick chat.
DEEP_KEYWORDS = ("דוח מלא", "מחקר מעמיק", "מעמיק", "לעומק", "תחקרי", "מחקר שוק")
CHAT_TIMEOUT = 180     # quick chat replies
DEEP_TIMEOUT = 3600    # detached deep-research safety cap (1h) — raise if needed


def has_agent(agent):
    return agent in COMMANDS


def _last_user(history):
    for m in reversed(history):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _wants_deep(text):
    return any(k in (text or "") for k in DEEP_KEYWORDS)


def _run_claude(cmd, prompt_arg, timeout):
    """Run `claude -p "<cmd> <prompt_arg>"` headless. Returns (reply, error)."""
    exe = shutil.which("claude")
    if not exe:
        return None, "claude CLI לא נמצא — זמין על השרת/מקומית"
    prompt = f"{cmd} {prompt_arg}".strip()
    # ב-Windows צריך claude.CMD; מסירים CLAUDECODE כדי ש-claude -p לא יסרב על "סשן מקונן".
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        out = subprocess.run([exe, "-p", prompt], capture_output=True, text=True,
                             encoding="utf-8", timeout=timeout, cwd=VAULT, env=env)
        return (out.stdout or "").strip() or (out.stderr or "").strip() or "(אין תשובה)", None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _deep_research(agent, cmd, message, room_id):
    """Background thread: run the full deep research (no chat timeout) and post the
    finished report back into the room when done."""
    # מאלצים מצב 'דוח מלא' במנוע של דפנה, לא משנה איך נוסחה הבקשה.
    prompt_arg = f"{message}\n\n(מצב: דוח מלא — בצע את המחקר המעמיק המלא)"
    reply, err = _run_claude(cmd, prompt_arg, timeout=DEEP_TIMEOUT)
    if room_id is None:
        return
    if err == "timeout":
        db.add_message(room_id, agent,
                       f"({agent}: המחקר נמשך מעבר לזמן המוקצב ונעצר. אפשר לצמצם את ההיקף ולנסות שוב.)")
    elif err:
        db.add_message(room_id, agent, f"({agent}: המחקר נכשל — {err})")
    else:
        db.add_message(room_id, agent, f"✅ סיימתי את המחקר המעמיק:\n\n{reply}")


def make_chat(agent):
    """Return chat(history)->str that runs the agent's slash command via claude -p."""
    cmd = COMMANDS[agent]

    def chat(history, room_id=None):  # room_id used to post async results back
        message = _last_user(history)
        # סוכן-מחקר כבד + בקשת עומק → רץ ברקע, מאשר מיד, ושולח את הדוח כשמוכן.
        if agent in HEAVY and _wants_deep(message):
            threading.Thread(target=_deep_research,
                             args=(agent, cmd, message, room_id), daemon=True).start()
            return ("קיבלתי — מתחילה **מחקר מעמיק**. זה ייקח זמן (עד חצי שעה ויותר): "
                    "חיפוש רב-זוויתי, רשתות חברתיות, אתרים ומקורות, הצלבה ואימות. "
                    "אני עובדת על זה ברקע — הדוח ייכתב ל-`output/dafna` ואשלח אותו לכאן כשיהיה מוכן.")
        # ברירת מחדל — תשובת צ׳אט מהירה.
        reply, err = _run_claude(cmd, message, timeout=CHAT_TIMEOUT)
        if err == "timeout":
            return f"({agent} לא ענה בזמן)"
        if err:
            return f"(שגיאה במוח של {agent}: {err})"
        return reply

    return chat
