---
description: רן — סקירת ערב (מריץ את המוח האחד ran_core.py). זובין מפעיל ב-19:00; ניתן גם ידנית.
allowed-tools: Bash
---

אתה מפעיל את **סקירת הערב של רן**. כל ההיגיון נמצא במוח האחד `ran_core.py` (אותו מוח של הבוט החי) — הפקודה הזו רק מפעילה אותו, בלי לשכפל לוגיקה.

הרץ:
```
cd "c:/Users/User/Aiprojects/obsi_comp/Agents/מנכ״ל/רן"
PYTHONUTF8=1 python ran_core.py evening-review
```

זה: שולף את המטלות הפתוחות → מנסח סקירת ערב לפי `ran_style.md` → כותב ל-`output/ran/{תאריך} Evening Review.md` → שולח תקציר לבועז ב-Telegram.

דווח בקצרה את הפלט (כמה מטלות, נתיב הקובץ, והאם הטלגרם נשלח). אל תוסיף לוגיקה כאן — היחיד מקור האמת הוא `ran_core.py`.
