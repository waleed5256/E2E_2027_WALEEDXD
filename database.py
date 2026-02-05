# database.py
import os
import sqlite3
import hashlib
from cryptography.fernet import Fernet
import json
from datetime import datetime

# === SECRET KEY (auto generate if not exist) ===
KEY_FILE = "secret.key"
DB_FILE = "veer_database.db"

def get_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key

fernet = Fernet(get_key())

# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            chat_id TEXT,
            name_prefix TEXT,
            min_delay INTEGER DEFAULT 20,
            max_delay INTEGER DEFAULT 70,
            cookies_encrypted TEXT,
            messages TEXT,
            created_at TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task_id TEXT,
            is_running BOOLEAN DEFAULT 1,
            message_count INTEGER DEFAULT 0,
            started_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# === HELPER FUNCTIONS ===
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# === USER FUNCTIONS ===
def create_user(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        hashed = hash_password(password)
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                  (username.lower(), hashed, created))
        conn.commit()
        conn.close()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already taken!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def verify_user(username, password):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        hashed = hash_password(password)
        c.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (username.lower(), hashed))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    except:
        return None

def get_user_config(user_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""SELECT chat_id, name_prefix, min_delay, max_delay, cookies_encrypted, messages 
                     FROM users WHERE id = ?""", (user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                'chat_id': row[0] or '',
                'name_prefix': row[1] or '',
                'min_delay': row[2] or 20,
                'max_delay': row[3] or 70,
                'cookies': row[4] or '',
                'messages': row[5] or ''
            }
        return None
    except:
        return {}

def update_user_config(user_id, chat_id, name_prefix, min_delay, cookies_plain, messages, max_delay=None):
    try:
        encrypted = fernet.encrypt(cookies_plain.encode()).decode()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""UPDATE users SET 
                     chat_id = ?, name_prefix = ?, min_delay = ?, max_delay = ?, 
                     cookies_encrypted = ?, messages = ? 
                     WHERE id = ?""", 
                  (chat_id, name_prefix, min_delay, max_delay or min_delay+30, encrypted, messages, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(e)
        return False

def encrypt_cookies(cookies):
    return fernet.encrypt(cookies.encode()).decode()

def decrypt_cookies(encrypted):
    try:
        return fernet.decrypt(encrypted.encode()).decode()
    except:
        return ""

# === TASK FUNCTIONS ===
def create_task_record(user_id, task_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO tasks (user_id, task_id, started_at) VALUES (?, ?, ?)",
                  (user_id, task_id, started))
        conn.commit()
        conn.close()
        return task_id
    except:
        return None

def get_task(task_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT is_running, message_count FROM tasks WHERE task_id = ?", (task_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {'is_running': bool(row[0]), 'message_count': row[1] or 0}
        return {'is_running': False, 'message_count': 0}
    except:
        return {'is_running': False, 'message_count': 0}

def get_tasks_for_user(user_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT task_id, is_running, message_count, started_at FROM tasks WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
        conn.close()
        return [
            {
                'task_id': r[0],
                'is_running': bool(r[1]),
                'message_count': r[2] or 0,
                'started_at': r[3]
            } for r in rows
        ]
    except:
        return []

def increment_message_count(task_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE tasks SET message_count = message_count + 1 WHERE task_id = ?", (task_id,))
        c.execute("SELECT message_count FROM tasks WHERE task_id = ?", (task_id,))
        count = c.fetchone()[0]
        conn.commit()
        conn.close()
        return count
    except:
        return 0

def stop_task_by_id(user_id, task_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE tasks SET is_running = 0 WHERE task_id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def stop_all_tasks(user_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE tasks SET is_running = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except:
        pass

# === FIRST ADMIN (OPTIONAL) ===
# Agar pehli baar deploy kar rahe ho to ek admin bana do
def create_first_admin():
    if verify_user("veer", "veer123") is None:
        create_user("veer", "veer123")
        print("Admin created: veer / veer123")

# Uncomment this line only first time
# create_first_admin()
