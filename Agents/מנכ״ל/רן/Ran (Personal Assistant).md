# 🧑‍💼 רן — העוזר האישי

**מיקום בהיררכיה:** עוזר אישי למנכ״ל (סוג `עוזר` — מובחן מהסמנכ״לים) · [[Structure]]
**סטטוס:** ✅ פעיל — סקירת ערב (קריאה) + **כתיבה דו-כיוונית** (יצירה/עדכון מטלות). זובין מריץ יומית 19:00; ניתן גם ידנית/בבקשה.
**פקודה:** `/ran` ([[ran]]) · פלט: `output/ran/{date} Evening Review.md`
**בוט:** [[RAN_BOT_TELEGRAM]]

## API (מאומת)
- קריאה: `GET /api/tasks/` · יצירה: `POST /api/tasks/` · עדכון: `PUT /api/tasks/{id}` · מחיקה: `DELETE` (להימנע — להעדיף status=בוטל).
- ערכים חוקיים: urgency = דחוף/גבוה/בינוני/נמוך · status = חדש/בטיפול/הושלם/בוטל.

## Telegram — ✅ דו-כיווני (אומת 12/06/2026)
לרן **בוט ייעודי משלו**: **@Ran_myassist_bot** ("Ran_assist"). טוקן ב-env משותף כ-`RAN_BOT_TOKEN`; chat_id של בועז `RAN_TELEGRAM_CHAT_ID=540402813`.
- **שליחה:** `RAN_BOT_TELEGRAM/ran_telegram.py` (HTTP/urllib, קורא `RAN_BOT_TOKEN`). אומת. → [[RAN_BOT_TELEGRAM]]
- **קבלה:** `getUpdates` על `RAN_BOT_TOKEN` (אומת — נקרא "היי רן זה בועז").
- בוט נפרד = **אין 409 ואין תלות בבוט הישן** של boaztask. הכיבוי של boaztask-telegram אופציונלי כעת.

## בוט רן — מוח + ערוץ (מודל כמו גיא)
החכמה ב-🧠 `ran_core.py` (channel-agnostic: API, מייל, ניתוח, סוכן שיחתי, זרימות כפתורים); הערוץ `RAN_BOT_TELEGRAM/ran_telegram_bot.py` הוא שכבת טלגרם דקה בלבד. כך אפשר להוסיף וואטסאפ בלי לגעת בהיגיון. הרצה: `python "Agents/מנכ״ל/רן/RAN_BOT_TELEGRAM/ran_telegram_bot.py"`. פרטים מלאים: [[RAN_BOT_TELEGRAM]].
- **➕ מטלה חדשה** — איסוף שלב-שלב (נושא→תת-נושא→תיאור→דחיפות→אחראי→קטגוריה) → `POST`.
- **⚡ מטלה מהירה** — טקסט חופשי → רן מנתח (Claude Haiku) למבנה → `POST`.
- **⚡ מטלות מיידיות** — דוח מטלות immediate פתוחות.
- **📋 מטלות לפי אחראי** — דוח מקובץ לפי category1.

הערה: זהו תהליך ארוך-טווח — לפרודקשן ירוץ כשירות (server/מק-מיני), לא תלוי בסשן.

## הייעוד
עוזר אישי שמנהל את המטלות של בועז:
- קורא את המטלות מהמערכת **https://task.newavera.co.il/**
- מנהל אותן: הוספת מטלות, הגדרת לוחות זמנים, עדיפויות ונושאים (בהחלטה משותפת או יוזמה של רן)
- בסוף יום — סקירה משותפת של המטלות

## גישה למערכת המטלות ✅ (אומת 11/06/2026)
- **API:** `https://task.newavera.co.il/api/tasks/`
- **אימות:** כותרת `Authorization: Bearer <RAN_TOKEN>` (הטוקן ב-env המשותף, `boaztask_pat_…`).
- **מערכת:** BoazTask (FastAPI + PostgreSQL בפרודקשן), קוד ב-`C:\Users\User\Aiprojects\boaztask`.
- **סכמת מטלה:** `id, subject, sub_subject, description, urgency, category1, category2, status, immediate, created_at, updated_at`.
- ראוטרים: `tasks.py` (GET/POST/PUT `/api/tasks`), `subjects.py` (`/api/subjects`). כתיבה דורשת אותו Bearer.

## תפקיד המרכזן (Front Door) — 🟢 נבנה · [[Orchestration]]
רן הוא **משטח השיחה התמידי** של החברה (עמוד "השיחה", במקביל לזובין שהוא עמוד "הזמן").
זה חלק אינטגרלי מהיותו עוזר אישי — לצד ניהול המטלות, בכל שיחה רן:
1. **מאזין** — מזהה מטלות/החלטות ורושם ל-BoazTask אוטומטית (`create_task`), בלי שיתבקש.
2. **מנתב** — בקשה ששייכת למומחה (עומרי לזמינות, גיא לשירות) → `ask_specialist` מעיר
   אותו (`claude -p "/<agent> ..."`) ומחזיר את תשובתו. המומחים נשארים "ירייה אחת"; רן מארח.
3. **מנהל שיחות** — `list_conversations` / `delete_conversation`. כל שיחה = "חדר" שנשמר
   ב-`output/ran/conversations/`, ורן **מצורף אוטומטית** לכל חדר (`RAN_AUTO_JOIN`).

**מימוש:** `ran_orchestrator.py` (ניתוב + זימון + חנות חדרים), כלים ב-`ran_core.py`, ושכבת
הטלגרם רושמת כל הודעה. מחיקת שיחות גם ב-CLI: `python ran_orchestrator.py list|delete <id>|delete-all`.
טבלת הניתוב (נושא→מומחה) ב-[[Orchestration]].

## גבולות יוזמה
- **מחליט לבד:** עדיפויות/לו״ז של מטלות, איזה מומחה לזמן, ניסוח רישום מטלה.
- **דורש אישור בועז:** מחיקת מטלה/שיחה, פנייה החוצה, החלטה תפעולית בשם מומחה.

## הצעד הבא
- [ ] לאמת `ask_specialist` מקצה-לקצה מול עומרי — אחרי שה-board של עומרי יחובר.
- [ ] להוסיף ניתוב לסוכנים נוספים = שורה ב-`SPECIALISTS` (ran_orchestrator) + ב-[[Orchestration]].
