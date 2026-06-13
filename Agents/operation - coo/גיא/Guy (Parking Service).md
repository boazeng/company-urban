# 🅿️ גיא — שירות מתקני חניה

**מיקום בהיררכיה:** רמה 2 · תחת **סמנכ״ל תפעול** (COO) · [[Structure]]
**סטטוס:** 🟡 בפיתוח — תסריט שכפול מדויק של "דיווח תקלה" רץ בטלגרם (long polling, נבדק `getMe` ✅). ממתין לבדיקת שיחה מקצה-לקצה מהטלפון.
**סוג:** בוט שיחה (לא פקודת `claude -p` כמו שאר הסוכנים) — בנוי על פלטפורמת **takt-bots**.
**מערכת:** מוזג ל-monorepo תחת [`guy/`](../../../guy/) (מקור היסטורי: `C:\Users\User\Aiprojects\takt-bots`).
**בוט:** [[GUY_BOT_TELEGRAM]]

## הייעוד
בוט שירות התפעול של TACT. משוחח עם לקוחות שיש להם מתקני חניה שהחברה מתחזקת:
מקבל דיווחי תקלה, פותח קריאת שירות, או מעביר הודעה. בשלב ראשון דרך **טלגרם**, בהמשך גם וואטסאפ.

## התסריט (script)
- **מזהה:** `guy-parking-service` · **שם:** "גיא — שירות מתקני חניה"
- שכפול מדויק של תסריט "דיווח תקלה" (`maintenance-troubleshoot`, 14 שלבים) — נטען מה-DB החי דרך [seed_guy.py](../../../guy/seed_guy.py). ההבדל היחיד מהמקור: `script_id` ושם התצוגה.
- נערך ויזואלית בעורך הזרימה של takt-bots (`http://localhost:5210`).
- הברכה כרגע עדיין "הבוט החכם של חברת האחזקה" (כמו המקור) — לשנות ל"גיא" כשנחדד.

## Telegram — ✅ בוט ייעודי משלו (כמו לרן)
- בוט: **@Tack_check_bot** ("Tack-check", id `8819131259`).
- טוקן ב-env המשותף כ-`TACT_CHECK_BOT_TOKEN` (הרץ ממפה אותו ל-`TELEGRAM_BOT_TOKEN` הגנרי).
- **ערוץ נעול לגיא בנפרד** דרך `TELEGRAM_SCRIPT_ID` (ברירת מחדל `guy-parking-service`) — לא נוגע ב-`ROUTING_SCRIPT_ID` של הוואטסאפ.
- הרצה (long polling, ללא webhook/כתובת ציבורית):
  ```powershell
  cd C:\Users\User\Aiprojects\takt-bots
  backend\.venv\Scripts\python.exe run_telegram_guy.py
  ```
  בטלגרם: `/start` (או "התחל") מאתחל שיחה.

## קבצים (ב-takt-bots)
- [tools/telegram/telegram_bot.py](../../../guy/tools/telegram/telegram_bot.py) — עטיפת Telegram Bot API (טקסט, כפתורי inline, polling, נירמול הודעות). מקביל ל-`whatsapp_bot.py`.
- [run_telegram_guy.py](../../../guy/run_telegram_guy.py) — מריץ את גיא בטלגרם דרך אותו מנוע (M1000 → M10010).
- [seed_guy.py](../../../guy/seed_guy.py) — טוען/מסנכרן את התסריט מ-`maintenance-troubleshoot`.

## הצעד הבא
- [ ] בדיקת שיחה מקצה-לקצה מהטלפון (`/start` → דיווח תקלה → פתיחת קריאה).
- [ ] לחדד את התסריט לגיא: ברכה בשם "גיא", ניסוחים למתקני חניה, ענפים רלוונטיים.
- [ ] להחליט מתי האינטגרציות לפריוריטי נכנסות (כרגע כבויות → צמתי הבדיקה נופלים למסלול "לא נמצא").
- [ ] לפרודקשן: להריץ כשירות קבוע (לא תלוי-סשן), ובהמשך לחבר וואטסאפ.
