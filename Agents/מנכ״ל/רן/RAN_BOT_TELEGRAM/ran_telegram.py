"""Send a Telegram message as the BoazTask bot, on Ran's behalf (outbound only).

Bot token is read from the BoazTask backend .env; the destination chat id from
RAN_TELEGRAM_CHAT_ID (shared env or environment). Message text from argv[1] or stdin.

Usage:
    python ran_telegram.py "שלום מבוט"
    echo "טקסט" | python ran_telegram.py
"""
import sys, os, json, urllib.request

BOT_ENV = r"C:/Users/User/Aiprojects/boaztask/backend/.env"
SHARED_ENV = r"C:/Users/User/Aiprojects/env/.env"


def env_val(path, key):
    try:
        for line in open(path, encoding="utf-8"):
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip("\"'")
    except FileNotFoundError:
        pass
    return ""


def main():
    # Prefer Ran's own dedicated bot token (no polling conflict with anything else);
    # fall back to the BoazTask bot token if a dedicated one isn't set yet.
    bot = (
        os.getenv("RAN_BOT_TOKEN")
        or env_val(SHARED_ENV, "RAN_BOT_TOKEN")
        or env_val(BOT_ENV, "TELEGRAM_BOT_TOKEN")
    )
    chat = os.getenv("RAN_TELEGRAM_CHAT_ID") or env_val(SHARED_ENV, "RAN_TELEGRAM_CHAT_ID")
    text = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    if not bot:
        print("ERROR: TELEGRAM_BOT_TOKEN missing"); sys.exit(1)
    if not chat:
        print("ERROR: RAN_TELEGRAM_CHAT_ID missing — send the bot a message and capture it first"); sys.exit(2)
    payload = json.dumps({"chat_id": chat, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot}/sendMessage",
        data=payload, headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=20)
        body = json.loads(resp.read().decode("utf-8"))
        print("sent ok" if body.get("ok") else "failed:", body.get("description", ""))
    except Exception as exc:  # noqa: BLE001
        print("ERROR sending:", exc); sys.exit(3)


if __name__ == "__main__":
    main()
