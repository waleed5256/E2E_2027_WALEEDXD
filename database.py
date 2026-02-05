import json
import os
import hashlib

DB_FILE = "users_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    db = load_db()
    if username in db:
        return False, "User already exists"
    
    db[username] = {
        "password": hash_password(password),
        "config": {
            "chat_id": "",
            "chat_type": "E2EE",
            "delay": 15,
            "cookies": "",
            "messages": "",
            "running": False
        }
    }
    save_db(db)
    return True, "User created successfully"

def verify_user(username, password):
    db = load_db()
    if username in db:
        if db[username]["password"] == hash_password(password):
            return username
    return None

def get_user_config(user_id):
    db = load_db()
    if user_id in db:
        return db[user_id]["config"]
    return {}

def update_user_config(user_id, chat_id, chat_type, delay, cookies, messages, running=False):
    db = load_db()
    if user_id in db:
        db[user_id]["config"] = {
            "chat_id": chat_id,
            "chat_type": chat_type,
            "delay": delay,
            "cookies": cookies,
            "messages": messages,
            "running": running
        }
        save_db(db)
        return True
    return False
