# 🤖 RAN_BOT_TELEGRAM

ערוץ הטלגרם של [[Ran (Personal Assistant)|רן]] — **שכבה דקה בלבד**. כל החכמה יושבת ב-🧠 `ran_core.py` (בתיקיית הסוכן, רמה אחת מעל). מודל זהה לגיא: המוח מנהל את השיחה, הערוץ רק מתרגם לטלגרם. כך אפשר להוסיף וואטסאפ בלי לגעת בהיגיון.

**סטטוס:** ✅ פעיל
**ערוץ:** Telegram (long polling)

## זהות הבוט
- **בוט:** @Ran_myassist_bot ("Ran_assist")
- **טוקן:** `RAN_BOT_TOKEN` ב-env המשותף · **chat של בועז:** `RAN_TELEGRAM_CHAT_ID=540402813`

## ארכיטקטורה
- 🧠 **`../ran_core.py`** — המוח (channel-agnostic). מחזיק: לקוח BoazTask API, קריאת מייל, ניתוח Haiku, הסוכן השיחתי (Sonnet tool-use), וזרימות הכפתורים. חוזה: `start(session)` / `handle(session, text)` → `{text, buttons, menu, md}`. לא יודע כלום על טלגרם.
- 📡 **`ran_telegram_bot.py`** — ערוץ דק. מאזין (python-telegram-bot), מעביר כל הודעה/לחיצה ל-`ran_core.handle`, ומצייר את התשובה ככפתורי טלגרם. **אפס היגיון עסקי.**
- 📤 **`ran_telegram.py`** — שולח בלבד (outbound, urllib). דוחף הודעה אחת ל-chat של בועז. משמש את הסוכן `/ran` לסקירת הערב.
- 🗄️ **`ran_bot.py.bak`** — הגרסה הישנה (מונוליט) לפני ה-refactor, נשמרת כגיבוי עד אימות מלא.
- **`requirements.txt`** — `python-telegram-bot`, `requests`. **API:** `https://task.newavera.co.il/api/tasks/`

## יכולות (כולן ב-ran_core)
- ➕ מטלה חדשה (איסוף שלב-שלב → `POST`)
- ⚡ מטלה מהירה (טקסט חופשי → ניתוח Claude Haiku → `POST`)
- ⚡ מטלות מיידיות · 📋 מטלות לפי אחראי (דוחות)
- 💬 טקסט חופשי → הסוכן השיחתי (Sonnet tool-use): מבין, עונה, יוצר/מעדכן מטלות, קורא מייל

## הרצה
```powershell
# הבוט האינטראקטיבי (ערוץ דק → ran_core):
cd C:\Users\User\Aiprojects\obsi_comp
python "Agents/מנכ״ל/רן/RAN_BOT_TELEGRAM/ran_telegram_bot.py"

# שליחה חד-פעמית (מה שהסוכן /ran מריץ):
PYTHONUTF8=1 python "Agents/מנכ״ל/רן/RAN_BOT_TELEGRAM/ran_telegram.py" "טקסט"
```
> אומת (12/06/2026): המוח נטען וזרימת הכפתורים עובדת; הערוץ מייבא את `ran_core` והטוקן נטען.

## פריסה על הקופסה (systemd) — תמידי
הבוט הוא long-polling, ולכן צריך תהליך תמידי. הוא **לא** חלק מ-stack ה-AWS (Lambda לא יכול long-polling) ו**לא** משירות ה-`comms`. הוא רץ כשירות systemd נפרד על הקופסה:
- **שירות:** `ran-telegram.service` ([deploy/ran-telegram.service](../../../../deploy/ran-telegram.service)) — רץ מ-`/home/ubuntu/company-urban/ran_bot/` (נתיב ASCII), קורא env מ-`.env` של הקופסה.
- **פריסה:** `bash deploy/deploy-ran-bot-box.sh` — מסנכרן את `ran_core.py` + `ran_orchestrator.py` + הערוץ הדק, מתקין venv ותלויות, ומפעיל את השירות. (קודם `deploy/sync-box-env.sh` כדי לוודא `RAN_BOT_TOKEN` על הקופסה.)
- **תלות יחידה אמיתית:** `getUpdates` מותר רק לתהליך אחד פר-טוקן (אחרת 409). `ran_telegram.py` (שליחה בלבד) ו-`ran_core` בחדרי comms לא מתנגשים.
- **לוגים:** `journalctl -u ran-telegram -f`.

## הצעד הבא
- [ ] להריץ `deploy/deploy-ran-bot-box.sh` ולאמת שיחה מהטלפון (`/start` ל-@Ran_myassist_bot).
- [ ] לאחר אימות — למחוק את `ran_bot.py.bak`.
- [ ] בעתיד: ערוץ `RAN_BOT_WHATSAPP/` דק שקורא לאותו `ran_core`.
