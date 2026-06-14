"""SQLite layer for the comms system — rooms, participants, messages."""
import os
import sqlite3
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comms.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # wait (up to 3s) for a lock instead of erroring — reduces intermittent
    # slowness/errors when polls and writes hit the DB concurrently.
    conn.execute("PRAGMA busy_timeout = 3000")
    return conn


def init_db():
    conn = get_conn()
    # WAL: readers don't block the writer (and vice-versa) — removes the main
    # source of intermittent 1–2s latency when polling while messages are written.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT '1:1',   -- '1:1' | 'meeting'
            chair TEXT,                          -- chair agent for meetings (NULL for 1:1)
            status TEXT NOT NULL DEFAULT 'active', -- 'active' (open) | 'closed' (ended)
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS participants (
            room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            agent TEXT NOT NULL,
            PRIMARY KEY (room_id, agent)
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            author TEXT NOT NULL,               -- 'בועז' | <agent name>
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    # migration: add `chair` to pre-existing rooms tables
    try:
        conn.execute("ALTER TABLE rooms ADD COLUMN chair TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    # migration: add `status` (existing rooms default to 'active')
    try:
        conn.execute("ALTER TABLE rooms ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.commit()
    conn.close()


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


# ─── rooms ───
def create_room(title, kind, participants, chair=None):
    conn = get_conn()
    cur = conn.execute("INSERT INTO rooms (title, kind, chair, created_at) VALUES (?,?,?,?)",
                       (title, kind, chair, now()))
    rid = cur.lastrowid
    for a in participants:
        conn.execute("INSERT OR IGNORE INTO participants (room_id, agent) VALUES (?,?)", (rid, a))
    conn.commit()
    conn.close()
    return rid


def delete_room(room_id):
    """מוחק חדר. participants ו-messages נמחקים בקסקייד (ON DELETE CASCADE)."""
    conn = get_conn()
    conn.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    conn.commit()
    conn.close()


def list_rooms():
    conn = get_conn()
    rooms = []
    # active (open) conversations first, then closed ones; newest first within each group.
    q = ("SELECT * FROM rooms "
         "ORDER BY CASE COALESCE(status,'active') WHEN 'active' THEN 0 ELSE 1 END, id DESC")
    for r in conn.execute(q).fetchall():
        parts = [p["agent"] for p in
                 conn.execute("SELECT agent FROM participants WHERE room_id=?", (r["id"],)).fetchall()]
        rooms.append({"id": r["id"], "title": r["title"], "kind": r["kind"],
                      "chair": r["chair"], "status": r["status"] if "status" in r.keys() else "active",
                      "created_at": r["created_at"], "participants": parts})
    conn.close()
    return rooms


def set_room_status(room_id, status):
    conn = get_conn()
    conn.execute("UPDATE rooms SET status=? WHERE id=?", (status, room_id))
    conn.commit()
    conn.close()


def room_chair(room_id):
    conn = get_conn()
    row = conn.execute("SELECT chair FROM rooms WHERE id=?", (room_id,)).fetchone()
    conn.close()
    return row["chair"] if row else None


def room_participants(room_id):
    conn = get_conn()
    parts = [p["agent"] for p in
             conn.execute("SELECT agent FROM participants WHERE room_id=?", (room_id,)).fetchall()]
    conn.close()
    return parts


def add_participant(room_id, agent):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO participants (room_id, agent) VALUES (?,?)", (room_id, agent))
    conn.commit()
    conn.close()


# ─── messages ───
def add_message(room_id, author, text):
    conn = get_conn()
    cur = conn.execute("INSERT INTO messages (room_id, author, text, created_at) VALUES (?,?,?,?)",
                       (room_id, author, text, now()))
    mid = cur.lastrowid
    conn.commit()
    row = conn.execute("SELECT * FROM messages WHERE id=?", (mid,)).fetchone()
    conn.close()
    return dict(row)


def list_messages(room_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM messages WHERE room_id=? ORDER BY id", (room_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
