# 🅿️ סוכן לידים — מתקני חניה

**פקודה:** `/parking-leads`
**מיקום בהיררכיה:** רמה 3 · תחת [[Conductor (Zubin)|סוכן לידים]] / סמנכ״ל שיווק ([[Structure]])
**סטטוס:** ✅ פעיל — אומת end-to-end על גבעתיים (11/06/2026): 468 פרוטוקולים → 47 פרויקטים → טיוטת מייל
**הגדרה:** [[parking-leads]] (`.claude/commands/parking-leads.md`)

## מה הוא עושה
פעם בשבוע סורק ועדות תכנון, מזהה פרויקטים שקיבלו אישור למתקני חניה (אוטומטי/חצי-אוטומטי/מכפילים), מכניס אותם ל-DB של פרויקט `newave land design`, ומכין טיוטת מייל ל-boazen@gmail.com עם הפרויקטים החדשים בלבד.

## איך זה עובד (v1 — גבעתיים)
מנצל את הפייפליין הקיים ב-`newave land design`:
1. **סריקה** — `complot_scraper.py --site-id 98 --city-name גבעתיים ... --output-dir data/protocols_search`
2. **חילוץ + DB** — `extract_parking_new_cities.py givatayim` (Claude Haiku + geocode) → `data/parking_protocols_givatayim.json`
3. **diff** — [[parking_leads_diff]] (`scripts/parking_leads_diff.py`) משווה ל-baseline ומוצא פרויקטים חדשים (מפתח: `{עיר, כתובת}`)
4. **טיוטה** — Gmail draft עם טבלת הפרויקטים החדשים

## קלט / תלויות
- פרויקט `newave land design` עם סביבת ה-Python שלו מותקנת (requirements + anthropic, geopandas וכו')
- `ANTHROPIC_API_KEY` (ל-Claude Haiku בחילוץ) — ב-env המשותף
- חיבור Gmail (כרגע טיוטה בלבד דרך claude.ai MCP)

## פלט
- **DB:** `newave land design/data/parking_protocols_givatayim.json` (לאן שהפרויקט מכניס)
- **דוח שבועי:** `output/parking-leads/{YYYY-MM-DD} גבעתיים.md`
- **מייל:** טיוטה ל-boazen@gmail.com

## TODO
- [ ] ריצת אימות end-to-end על גבעתיים, ואז להפוך סטטוס ל-`פעיל` בלוח הזמנים.
- [ ] הרחבה לערים נוספות (בת ים, ראשל״צ, נתניה, חיפה, ירושלים) — סוכן-משנה/קונפיג לכל עיר.
- [ ] מעבר משליחת טיוטה לשליחה אמיתית (SMTP/Gmail API) בשרת.
