"""
ran_telegram_bot — ערוץ הטלגרם הדק של רן.

אפס היגיון עסקי: מקבל הודעות/לחיצות מטלגרם, מעביר ל-ran_core (המוח),
ומצייר את התשובה ({text, buttons, menu}) ככפתורי טלגרם. אותו ran_core ישמש
גם ערוץ וואטסאפ עתידי — בלי לגעת במוח.

מבנה ה-Response מ-ran_core:
    {"text", "buttons": [{id,title}]|None, "menu": bool, "md": bool}
  buttons → inline keyboard (callback_data=id) · menu → התפריט הראשי הקבוע.

הרצה (משורש ה-vault):
    python "Agents/מנכ״ל/רן/RAN_BOT_TELEGRAM/ran_telegram_bot.py"
"""
import sys
import os
import asyncio

# המוח יושב בתיקיית הסוכן (רמה אחת מעל) — נוסיף אותה ל-path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ran_core  # noqa: E402
import ran_orchestrator  # noqa: E402  — שכבת המרכזן: חדרים + ניתוב

from telegram import (  # noqa: E402
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
)
from telegram.ext import (  # noqa: E402
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters,
)

BOT_TOKEN = ran_core.env_val("RAN_BOT_TOKEN")
MENU_KB = ReplyKeyboardMarkup(ran_core.MENU, resize_keyboard=True)
SESSIONS = {}  # chat_id -> session dict (held by the channel, owned by the brain)


def _session(uid):
    return SESSIONS.setdefault(uid, {})


def _markup(resp):
    if resp.get("buttons"):
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(b["title"], callback_data=b["id"])] for b in resp["buttons"]]
        )
    if resp.get("menu"):
        return MENU_KB
    return None


async def _reply(target, resp):
    await target.reply_text(
        resp["text"],
        parse_mode="Markdown" if resp.get("md", True) else None,
        reply_markup=_markup(resp),
    )


async def on_start(update, ctx):
    uid = update.effective_chat.id
    ran_orchestrator.open_conversation(uid)  # רן מצורף אוטומטית לחדר ("מוכנס לחדר")
    await _reply(update.message, ran_core.start(_session(uid)))


async def on_text(update, ctx):
    uid = update.effective_chat.id
    await ctx.bot.send_chat_action(chat_id=uid, action="typing")
    ran_orchestrator.append_message(uid, "user", update.message.text)
    resp = await asyncio.to_thread(ran_core.handle, _session(uid), update.message.text)
    ran_orchestrator.append_message(uid, "assistant", resp.get("text", ""))
    await _reply(update.message, resp)


async def on_command(update, ctx):
    # /skip, /cancel — pass the raw command text to the brain
    uid = update.effective_chat.id
    resp = await asyncio.to_thread(ran_core.handle, _session(uid), update.message.text)
    await _reply(update.message, resp)


async def on_callback(update, ctx):
    q = update.callback_query
    await q.answer()
    uid = q.message.chat.id
    resp = await asyncio.to_thread(ran_core.handle, _session(uid), q.data)
    ran_orchestrator.append_message(uid, "assistant", resp.get("text", ""))
    await _reply(q.message, resp)


def main():
    if not BOT_TOKEN:
        print("ERROR: RAN_BOT_TOKEN missing in shared env")
        sys.exit(1)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler(["skip", "cancel"], on_command))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    print("Ran bot (thin Telegram channel → ran_core) is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
