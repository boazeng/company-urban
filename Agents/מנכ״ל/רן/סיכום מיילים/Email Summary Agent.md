# 📧 סוכן סיכום מיילים יומי

**פקודה:** `/daily-email-summary`
**סטטוס:** ✅ פעיל (מקומי)
**הגדרה:** [[daily-email-summary]] (`.claude/commands/daily-email-summary.md`)

## מה הוא עושה
בסוף כל יום מושך את המיילים החשובים שהגיעו ל-Inbox, מסנן רעש (קידום מכירות, רשתות חברתיות, פורומים, מיילים שנשלחו לעצמך), מסווג ל-3 רמות חשיבות, וכותב סיכום בעברית לתיקיית `Daily Summaries/`.

## קלט
- חיבור Gmail (כרגע דרך claude.ai MCP — מקומי בלבד)

## פלט
- `output/daily-email-summary/{YYYY-MM-DD} Email Summary.md`

## הרצה
```powershell
claude -p "/daily-email-summary"
```

## TODO למעבר לשרת
- [ ] להחליף חיבור Gmail לאסימון OAuth קבוע (`shared-auth`) במקום claude.ai MCP
- [ ] להגדיר cron להרצה בסוף כל יום
- [ ] לשלוח התראה (אימייל/וואטסאפ) כשהסיכום מוכן
