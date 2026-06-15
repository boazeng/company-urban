"""Command-agent brain — for agents whose intelligence is a Claude Code slash
command (e.g. /omri, /guy) run headless via `claude -p`. The comms analog of
exec_brain: it makes such agents first-class room participants that speak
directly in the room (not only via Ran relaying).

Adding a command-agent = one line in COMMANDS.

Heavy agents (deep research like דפנה) can't finish inside a chat turn — a real
market study can run 30min+. A `claude -p` that long is memory-heavy and OOM'd the
small comms box, so on-box background research is OFF by default. When enabled on a
box with RAM headroom (ALLOW_BOX_DEEP_RESEARCH=1), it runs DETACHED, single-flight,
and posts the finished report back into the room.
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

# Agents whose deep mode is long-running.
HEAVY = {"דפנה"}
# A request containing any of these = a deep job. Otherwise = quick chat.
DEEP_KEYWORDS = ("דוח מלא", "מחקר מעמיק", "מעמיק", "לעומק", "תחקרי", "מחקר שוק")
CHAT_TIMEOUT = 180     # quick chat replies
DEEP_TIMEOUT = 3600    # detached deep-research safety cap (1h)

# A 30min+ `claude -p` OOM'd the small comms box. Heavy on-box research is OFF
# unless explicitly enabled on a box with RAM headroom. Single-flight either way.
ALLOW_BOX_DEEP_RESEARCH = os.environ.get("ALLOW_BOX_DEEP_RESEARCH", "") == "1"
_deep_lock = threading.Lock()
_deep_running = False

# ── Fargate per-job (preferred): deep research runs in an isolated ECS task ──
# Config comes from the stack outputs, set in the box env (see AWS-SETUP.md).
ECS_CLUSTER = os.environ.get("RESEARCH_ECS_CLUSTER", "")
ECS_TASKDEF = os.environ.get("RESEARCH_TASK_DEF", "")
ECS_SUBNET = os.environ.get("RESEARCH_SUBNET", "")
ECS_SG = os.environ.get("RESEARCH_SG", "")
ECS_REGION = os.environ.get("AWS_REGION", "us-east-1")
ECS_CONTAINER = os.environ.get("RESEARCH_CONTAINER", "research")
COMMS_PUBLIC_API = os.environ.get("COMMS_PUBLIC_API", "https://comms.newavera.co.il")
RESEARCH_POST_TOKEN = os.environ.get("RESEARCH_POST_TOKEN", "")  # optional postback auth


def _fargate_configured():
    return all([ECS_CLUSTER, ECS_TASKDEF, ECS_SUBNET, ECS_SG])


def _launch_fargate_research(topic, room_id):
    """Launch a one-off Fargate task that runs the deep research and posts the
    report back to the room. Returns nothing; raises on failure."""
    import boto3  # lazy — only needed when Fargate is configured
    env = [
        {"name": "TOPIC", "value": topic},
        {"name": "CMD", "value": "/dafna"},
        {"name": "AGENT", "value": "דפנה"},
        {"name": "COMMS_API", "value": COMMS_PUBLIC_API},
        {"name": "ROOM_ID", "value": str(room_id) if room_id is not None else ""},
    ]
    if RESEARCH_POST_TOKEN:
        env.append({"name": "POST_TOKEN", "value": RESEARCH_POST_TOKEN})
    boto3.client("ecs", region_name=ECS_REGION).run_task(
        cluster=ECS_CLUSTER,
        taskDefinition=ECS_TASKDEF,
        launchType="FARGATE",
        count=1,
        overrides={"containerOverrides": [{"name": ECS_CONTAINER, "environment": env}]},
        networkConfiguration={"awsvpcConfiguration": {
            "subnets": [ECS_SUBNET],
            "securityGroups": [ECS_SG],
            "assignPublicIp": "ENABLED",
        }},
    )


def has_agent(agent):
    return agent in COMMANDS


def _last_user(history):
    for m in reversed(history):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _wants_deep(text):
    return any(k in (text or "") for k in DEEP_KEYWORDS)


def _run_claude(cmd, prompt_arg, timeout, low_priority=False):
    """Run `claude -p "<cmd> <prompt_arg>"` headless. Returns (reply, error)."""
    exe = shutil.which("claude")
    if not exe:
        return None, "claude CLI לא נמצא — זמין על השרת/מקומית"
    prompt = f"{cmd} {prompt_arg}".strip()
    argv = [exe, "-p", prompt]
    # על POSIX, מריצים מחקר כבד בעדיפות-CPU נמוכה כדי לא לחנוק את השרת.
    if low_priority and os.name == "posix" and shutil.which("nice"):
        argv = ["nice", "-n", "15"] + argv
    # ב-Windows צריך claude.CMD; מסירים CLAUDECODE כדי ש-claude -p לא יסרב על "סשן מקונן".
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    try:
        out = subprocess.run(argv, capture_output=True, text=True,
                             encoding="utf-8", timeout=timeout, cwd=VAULT, env=env)
        return (out.stdout or "").strip() or (out.stderr or "").strip() or "(אין תשובה)", None
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def _deep_research(agent, cmd, message, room_id):
    """Background thread: run the full deep research (no chat timeout) and post the
    finished report back into the room when done."""
    global _deep_running
    try:
        prompt_arg = f"{message}\n\n(מצב: דוח מלא — בצע את המחקר המעמיק המלא)"
        reply, err = _run_claude(cmd, prompt_arg, timeout=DEEP_TIMEOUT, low_priority=True)
        if room_id is None:
            return
        if err == "timeout":
            db.add_message(room_id, agent,
                           f"({agent}: המחקר נמשך מעבר לזמן המוקצב ונעצר. אפשר לצמצם את ההיקף ולנסות שוב.)")
        elif err:
            db.add_message(room_id, agent, f"({agent}: המחקר נכשל — {err})")
        else:
            db.add_message(room_id, agent, f"✅ סיימתי את המחקר המעמיק:\n\n{reply}")
    finally:
        with _deep_lock:
            _deep_running = False


def make_chat(agent):
    """Return chat(history)->str that runs the agent's slash command via claude -p."""
    cmd = COMMANDS[agent]

    def chat(history, room_id=None):  # room_id used to post async results back
        global _deep_running
        message = _last_user(history)
        # סוכן-מחקר כבד + בקשת עומק.
        if agent in HEAVY and _wants_deep(message):
            # 1) מועדף — Fargate per-job: רץ מבודד, מאשר מיד, שולח דוח כשמסיים.
            if _fargate_configured():
                try:
                    _launch_fargate_research(message, room_id)
                    return ("קיבלתי — מתחילה **מחקר מעמיק** (רץ מבודד על Fargate). "
                            "ייקח זמן (עד חצי שעה ויותר); אני עובדת ברקע והדוח יישלח לכאן כשמוכן.")
                except Exception as e:  # noqa: BLE001
                    return f"(לא הצלחתי לשגר את המחקר ל-Fargate: {e})"
            # 2) על הקופסה — רק אם הופעל במפורש (קופסה עם זיכרון פנוי).
            if not ALLOW_BOX_DEEP_RESEARCH:
                # שרת ה-comms קטן מכדי להריץ מחקר עומק (30 דק׳+) בלי להיחנק, ו-Fargate לא מוגדר.
                return ("קיבלתי שזו בקשת **מחקר מעמיק**. כרגע אין יעד הרצה מוגדר (Fargate לא מחובר, "
                        "והרצה על שרת ה-comms כבויה כי הוא קטן מדי). אפשר להריץ ידנית: "
                        "`/dafna <נושא> דוח מלא` במכונה מתאימה. בינתיים אני זמינה לשאלות מהירות.")
            with _deep_lock:
                if _deep_running:
                    return "כבר רץ מחקר מעמיק כרגע — אסיים אותו ואז אפשר להזמין את הבא."
                _deep_running = True
            threading.Thread(target=_deep_research,
                             args=(agent, cmd, message, room_id), daemon=True).start()
            return ("קיבלתי — מתחילה **מחקר מעמיק**. זה ייקח זמן (עד חצי שעה ויותר). "
                    "אני עובדת ברקע — הדוח ייכתב ל-`output/dafna` ואשלח אותו לכאן כשיהיה מוכן.")
        # ברירת מחדל — תשובת צ׳אט מהירה.
        reply, err = _run_claude(cmd, message, timeout=CHAT_TIMEOUT)
        if err == "timeout":
            return f"({agent} לא ענה בזמן)"
        if err:
            return f"(שגיאה במוח של {agent}: {err})"
        return reply

    return chat
