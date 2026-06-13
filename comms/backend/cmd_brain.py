"""Command-agent brain — for agents whose intelligence is a Claude Code slash
command (e.g. /omri, /guy) run headless via `claude -p`. The comms analog of
exec_brain: it makes such agents first-class room participants that speak
directly in the room (not only via Ran relaying).

Adding a command-agent = one line in COMMANDS.
"""
import os
import shutil
import subprocess

VAULT = os.environ.get("VAULT", r"C:/Users/User/Aiprojects/obsi_comp")

COMMANDS = {
    "עומרי": "/omri",
    "גיא": "/guy",
    # זובין עבר למוח bespoke (zubin_core) — שיחה על הלוח + פעימה לפי בקשה מפורשת.
}


def has_agent(agent):
    return agent in COMMANDS


def _last_user(history):
    for m in reversed(history):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def make_chat(agent):
    """Return chat(history)->str that runs the agent's slash command via claude -p."""
    cmd = COMMANDS[agent]

    def chat(history, room_id=None):  # room_id accepted for a uniform signature
        # ב-Windows צריך claude.CMD (לא "claude" החשוף); ומסירים CLAUDECODE כדי
        # ש-claude -p לא יסרב על "סשן מקונן". ראה project_agent_company_orchestrator.
        exe = shutil.which("claude")
        if not exe:
            return f"({agent}: claude CLI לא נמצא — זמין על השרת/מקומית)"
        prompt = f"{cmd} {_last_user(history)}".strip()
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        try:
            out = subprocess.run([exe, "-p", prompt], capture_output=True, text=True,
                                 encoding="utf-8", timeout=180, cwd=VAULT, env=env)
            return (out.stdout or "").strip() or (out.stderr or "").strip() or "(אין תשובה)"
        except subprocess.TimeoutExpired:
            return f"({agent} לא ענה בזמן)"
        except Exception as e:  # noqa: BLE001
            return f"(שגיאה במוח של {agent}: {e})"

    return chat
