# 🤖 GUY_BOT_TELEGRAM

כרטיס הבוט של [[Guy (Parking Service)|גיא]] בטלגרם. **מרכז ההפעלה** — הקוד עצמו נשאר ב-takt-bots כי הוא תלוי במנוע שלו, אבל כל מה שצריך כדי להריץ ולתחזק את הבוט מתועד כאן.

**סטטוס:** ✅ חי (long polling) · נבדק `getMe` · ממתין לבדיקת שיחה מקצה-לקצה
**ערוץ:** Telegram · long polling (ללא webhook / כתובת ציבורית)

## זהות הבוט
- **בוט:** @Tack_check_bot ("Tack-check") · id `8819131259`
- **טוקן:** `TACT_CHECK_BOT_TOKEN` ב-env המשותף (`C:\Users\User\Aiprojects\env\.env`)
- הרץ ממפה אותו אוטומטית ל-`TELEGRAM_BOT_TOKEN` הגנרי (override עם `TELEGRAM_TOKEN_ENV`).

## תסריט
- **מזהה:** `guy-parking-service` (שכפול של "דיווח תקלה", 14 שלבים)
- הערוץ נעול לתסריט הזה דרך `TELEGRAM_SCRIPT_ID` (ברירת מחדל `guy-parking-service`) — בלתי תלוי ב-WhatsApp.

## איפה הקוד (ב-takt-bots)
- [run_telegram_guy.py](../../../../../takt-bots/run_telegram_guy.py) — הרץ (polling → מנוע M1000→M10010 → שליחה חזרה)
- [tools/telegram/telegram_bot.py](../../../../../takt-bots/tools/telegram/telegram_bot.py) — עטיפת Telegram Bot API
- [seed_guy.py](../../../../../takt-bots/seed_guy.py) — טעינת/סנכרון התסריט
> הקוד תלוי במנוע (`agents.bot_engine`), ב-`shared_env` וב-venv של takt-bots — לכן הוא רץ רק משורש הפרויקט.

## הרצה
```powershell
cd C:\Users\User\Aiprojects\takt-bots
backend\.venv\Scripts\python.exe run_telegram_guy.py
```
בטלגרם: `/start` (או "התחל") מאתחל שיחה. `Ctrl+C` לעצירה.

## הצעד הבא
- [ ] בדיקת שיחה מקצה-לקצה מהטלפון.
- [ ] לפרודקשן: להריץ כשירות קבוע (לא תלוי-סשן).
