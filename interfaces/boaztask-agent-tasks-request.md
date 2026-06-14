# בקשה: הוספת שדה "מטלת-סוכן" לטבלת המטלות (BoazTask)

## רקע ומטרה
הוסף לטבלת המטלות הקיימת (`tasks`) שדה בוליאני אחד: **`is_agent_task`**.
- מטלה עם `is_agent_task = true` היא **מטלת-סוכן** ולא מוצגת לבועז (לא ב-list ולא ב-stats).
- מי שמחזיק ב-API token ניגש למטלות-הסוכנים במפורש עם פרמטר query.
- **השרת נשאר "טיפש":** רק מאחסן ומסנן לפי הדגל. אין שום הכרה של "רן" / "מאמת" / לוגיקת אימות בצד השרת.

## אסור לגעת
- אין ליצור טבלאות חדשות — שינוי על `tasks` הקיימת בלבד.
- אין להזכיר רן / verifier / אימות בקוד.
- אין צורך בשינוי frontend — ברירת המחדל מסתירה מטלות-סוכנים אוטומטית.

## נקודה קריטית — מיגרציה
טבלת `tasks` כבר קיימת בפרודקשן (PostgreSQL). `Base.metadata.create_all()` **לא** מוסיף עמודה לטבלה קיימת. לכן חובה להוסיף `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` אידמפוטנטי, בדיוק כמו התבנית הקיימת ב-`_ensure_position_columns()`.

---

## שינוי 1 — `backend/app/models.py`
במחלקת `Task`, אחרי השדה `immediate` ולפני `created_at`, הוסף שורה אחת:

```python
    is_agent_task = Column(Boolean, default=False, nullable=False, server_default="false")
```

(`Boolean` כבר מיובא בראש הקובץ — אל תוסיף import.)

---

## שינוי 2 — `backend/app/main.py` (מיגרציה — חובה)
בתוך הפונקציה `_ensure_position_columns()`, ליד שתי שורות ה-`ALTER` הקיימות, הוסף:

```python
        conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_agent_task BOOLEAN NOT NULL DEFAULT FALSE"))
```

זה רץ בעלייה ומוסיף את העמודה ל-DB הקיים בלי לפגוע בנתונים.

---

## שינוי 3 — `backend/app/schemas.py`
- ב-`TaskCreate` הוסף: `is_agent_task: bool = False`
- ב-`TaskUpdate` הוסף: `is_agent_task: Optional[bool] = None`
- ב-`TaskResponse` הוסף: `is_agent_task: bool`

---

## שינוי 4 — `backend/app/routers/tasks.py` (הסתרה מבועז)

ב-`list_tasks` — הוסף פרמטר וברירת מחדל שמסתירה מטלות-סוכנים:

```python
def list_tasks(
    status: Optional[TaskStatus] = None,
    urgency: Optional[UrgencyLevel] = None,
    category1: Optional[str] = None,
    category2: Optional[str] = None,
    search: Optional[str] = None,
    is_agent_task: Optional[bool] = None,   # None/False → רק מטלות בועז · True → רק מטלות-סוכנים
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    # ברירת מחדל (פרמטר חסר) מחזירה רק מטלות בועז — מטלות-סוכנים מוסתרות אלא אם ביקשו במפורש.
    query = query.filter(Task.is_agent_task == (is_agent_task is True))
    if status:
        query = query.filter(Task.status == status)
    # ... שאר הפילטרים הקיימים (urgency/category1/category2/search) ללא שינוי ...
    return query.order_by(Task.created_at.desc()).all()
```

ב-`get_stats` — שיהיה עקבי (סטטיסטיקות בועז לא יספרו מטלות-סוכנים):

```python
def get_stats(is_agent_task: Optional[bool] = None, db: Session = Depends(get_db)):
    base = db.query(Task).filter(Task.is_agent_task == (is_agent_task is True))
    total = base.count()
    by_status = {s.value: base.filter(Task.status == s).count() for s in TaskStatus}
    by_urgency = {u.value: base.filter(Task.urgency == u).count() for u in UrgencyLevel}
    return {"total": total, "by_status": by_status, "by_urgency": by_urgency}
```

`POST /` ו-`PUT /{id}` הקיימים לא דורשים שינוי — `is_agent_task` זורם דרך `model_dump()`.

---

## בדיקות קבלה (עם Bearer token)
1. `POST /api/tasks/` עם `{"is_agent_task": true, ...}` → 201.
2. `GET /api/tasks/` (בלי פרמטר) → **לא** מחזיר את המטלה הזו (תצוגת בועז נקייה).
3. `GET /api/tasks/?is_agent_task=true` → מחזיר רק מטלות-סוכנים.
4. `GET /api/tasks/stats/summary` → לא סופר מטלות-סוכנים.
5. מטלות בועז הקיימות → מופיעות כרגיל.

זה כל השינוי: עמודה אחת + מיגרציה אידמפוטנטית + סינון ברירת-מחדל.
