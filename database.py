import sqlite3
from config import DB_PATH

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)

# ── settings ────────────────────────────────────────────────────────────────
def get_setting(key, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

def set_setting(key, value):
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

import json as _json

def get_api_keys() -> list:
    """Return ordered list of user API keys."""
    raw = get_setting("groq_api_keys")
    return _json.loads(raw) if raw else []

def set_api_keys(keys: list):
    set_setting("groq_api_keys", _json.dumps(keys))

def add_api_key(key: str):
    keys = get_api_keys()
    if key and key not in keys:
        keys.append(key)
        set_api_keys(keys)

def remove_api_key(key: str):
    keys = get_api_keys()
    if key in keys:
        keys.remove(key)
        set_api_keys(keys)

def get_selected_model() -> str:
    return get_setting("selected_model", "")

def set_selected_model(model: str):
    set_setting("selected_model", model)

def get_theme():
    return get_setting("theme", "dark")

def set_theme(theme):
    set_setting("theme", theme)

def get_stealth():
    return get_setting("stealth", "true") == "true"

def set_stealth(enabled: bool):
    set_setting("stealth", "true" if enabled else "false")

def get_startup():
    return get_setting("startup", "false") == "true"

def set_startup(enabled: bool):
    set_setting("startup", "true" if enabled else "false")

def create_conversation(title="New Chat"):
    with get_conn() as conn:
        conn.execute("UPDATE conversations SET is_active = 0")
        cur = conn.execute("INSERT INTO conversations (title, is_active) VALUES (?, 1)", (title,))
        return cur.lastrowid

def get_active_conversation():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM conversations WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1").fetchone()
        if not row:
            conv_id = create_conversation()
            return get_conversation(conv_id)
        return row

def get_conversation(conv_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()

def set_active_conversation(conv_id):
    with get_conn() as conn:
        conn.execute("UPDATE conversations SET is_active = 0")
        conn.execute("UPDATE conversations SET is_active = 1 WHERE id = ?", (conv_id,))

def get_all_conversations():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM conversations ORDER BY created_at DESC").fetchall()

def add_message(conv_id, role, content):
    with get_conn() as conn:
        conn.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)", (conv_id, role, content))
    update_conversation_title(conv_id)

def get_messages(conv_id):
    with get_conn() as conn:
        return conn.execute("SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp", (conv_id,)).fetchall()

def update_conversation_title(conv_id):
    with get_conn() as conn:
        first_msg = conn.execute(
            "SELECT content FROM messages WHERE conversation_id = ? AND role = 'user' ORDER BY timestamp LIMIT 1",
            (conv_id,)
        ).fetchone()
        if first_msg:
            title = first_msg[0][:20] + ("..." if len(first_msg[0]) > 30 else "")
            conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (title, conv_id))

def delete_conversation(conv_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
