import streamlit as st
import time
import threading 
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import database as db 
import requests
import uuid
from datetime import datetime
import pytz
import random

st.set_page_config(
    page_title="😊 Veer",
    page_icon="🫶🏻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (unchanged + emergency button style)
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    * { font-family: 'Poppins', sans-serif; }
    .stApp { 
        background-image: url('https://i.postimg.cc/k5P9GPx3/Whats-App-Image-2025-11-07-at-10-18-13-958e0738.jpg');
        background-size: cover; background-attachment: fixed;
    }
    .main-header { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); padding: 2rem; border-radius: 15px; text-align: center; margin-bottom: 2rem; }
    .main-header h1 { background: linear-gradient(45deg, #ff6b6b, #4ecdc4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5rem; font-weight: 700; }
    .prince-logo { width: 70px; height: 70px; border-radius: 50%; margin-bottom: 15px; border: 2px solid #4ecdc4; }
    .stButton>button { background: linear-gradient(45deg, #ff6b6b, #4ecdc4); color: white; border: none; border-radius: 10px; padding: 0.75rem 2rem; font-weight: 600; width: 100%; }
    .emergency-stop { background: linear-gradient(45deg, #ff0000, #ff4747) !important; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(255,0,0,0.7); } 70% { box-shadow: 0 0 0 10px rgba(255,0,0,0); } 100% { box-shadow: 0 0 0 0 rgba(255,0,0,0); } }
    .footer { text Rosemary: center; padding: 2rem; color: rgba(255,255,255,0.9); font-weight: 700; margin-top: 3rem; background: rgba(255,255,255,0.05); border-radius: 10px; text-shadow: 0 0 10px #4ecdc4; }
    .console-line { background: rgba(78,205,196,0.08); padding: 8px 12px; border-left: 3px solid #4ecdc4; margin: 4px 0; border-radius: 4px; color: #00ff88; font-family: Consolas; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Session State
for key in ['logged_in', 'user_id', 'username', 'logs', 'uploaded_cookies', 'uploaded_messages']:
    if key not in st.session_state:
        st.session_state[key] = False if key == 'logged_in' else None if key in ['user_id', 'username'] else [] if key == 'logs' else ""

def generate_task_id(): return str(uuid.uuid4())[:8].upper()

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    if automation_state:
        automation_state.logs.append(formatted)
    else:
        st.session_state.logs.append(formatted)

def find_message_input(driver, process_id, automation_state=None):
    log_message(f'{process_id}: Finding input box...', automation_state)
    time.sleep(5)
    selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"]',
        '[role="textbox"]',
        'textarea'
    ]
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for el in elements:
                driver.execute_script("arguments[0].click();", el)
                time.sleep(0.5)
                log_message(f'{process_id}: Input found!', automation_state)
                return el
        except: continue
    return None

def setup_browser():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1280,720')
    return webdriver.Chrome(options=options)

def human_type(element, text, driver):
    for char in text:
        driver.execute_script("arguments[0].dispatchEvent(new InputEvent('input', {bubbles:true, data:arguments[1]}));", element, char)
        time.sleep(random.uniform(0.05, 0.18))

def send_messages(config, username, automation_state, user_id, task_id):
    driver = None
    process_id = f"TASK-{task_id}"
    chat_ids = [x.strip() for x in config.get('chat_id', '').split(',') if x.strip()]
    messages_list = [x.strip() for x in config.get('messages', '').split('\n') if x.strip()]
    min_d = int(config.get('min_delay', 20))
    max_d = int(config.get('max_delay', 50))
    prefix = config.get('name_prefix', '')

    while db.get_task(task_id).get('is_running', False):
        for chat_id in chat_ids or ['']:
            if not db.get_task(task_id).get('is_running', False):
                break
            try:
                if driver:
                    try: driver.quit()
                    except: pass
                    time.sleep(3)
                driver = setup_browser()
                driver.get('https://www.facebook.com/')
                time.sleep(6)

                # Add cookies
                for cookie in config['cookies'].split(';'):
                    if '=' in cookie:
                        n, v = cookie.strip().split('=', 1)
                        try: driver.add_cookie({'name': n, 'value': v, 'domain': '.facebook.com'})
                        except: pass
                driver.get('https://www.facebook.com/')
                time.sleep(5)

                url = f'https://www.facebook.com/messages/t/{chat_id}' if chat_id else 'https://www.facebook.com/messages'
                driver.get(url)
                time.sleep(15)

                input_box = find_message_input(driver, process_id, automation_state)
                if not input_box:
                    log_message(f'{process_id}: Input not found → retry in 30s', automation_state)
                    time.sleep(30)
                    continue

                while db.get_task(task_id).get('is_running', False):
                    msg = messages_list[automation_state.message_rotation_index % len(messages_list)]
                    automation_state.message_rotation_index += 1
                    final_msg = f"{prefix} {msg}".strip()

                    try:
                        driver.execute_script("arguments[0].innerHTML = '';", input_box)
                        human_type(input_box, final_msg, driver)
                        time.sleep(1)

                        sent = driver.execute_script("""
                            let btns = document.querySelectorAll('[aria-label*="Send" i]');
                            for (let b of btns) {
                                if (b.offsetParent !== null) { b.click(); return true; }
                            }
                            return false;
                        """)
                        if not sent:
                            driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', bubbles:true}));", input_box)

                        count = db.increment_message_count(task_id)
                        log_message(f'{process_id}: MSG {count} SENT → {final_msg[:50]}', automation_state)

                        delay = random.randint(min_d, max_d)
                        for i in range(delay, 0, -1):
                            if not db.get_task(task_id).get('is_running', False):
                                break
                            time.sleep(1)

                    except Exception as e:
                        log_message(f'{process_id}: Send error → restart in 15s ({str(e)[:60]})', automation_state)
                        time.sleep(15)
                        break

            except Exception as e:
                log_message(f'{process_id}: FATAL → restart in 60s ({str(e)[:80]})', automation_state)
                time.sleep(60)
            finally:
                if driver:
                    try: driver.quit()
                    except: pass

    log_message(f'{process_id}: STOPPED BY BOSS VEER', automation_state)
    db.stop_task_by_id(user_id, task_id)
    automation_state.running = False

def start_automation(user_config, user_id, task_id=None):
    task_id = task_id or generate_task_id()
    db.create_task_record(user_id, task_id)
    config_copy = user_config.copy()
    config_copy['cookies'] = db.decrypt_cookies(user_config['cookies'])
    threading.Thread(
        target=send_messages,
        args=(config_copy, st.session_state.username, st.session_state.automation_state, user_id, task_id),
        daemon=True
    ).start()

# MAIN HEADER
st.markdown('<div class="main-header"><img src="https://i.postimg.cc/bJ3FbkN7/2.jpg" class="prince-logo"><h1>E2EE OFFLINE</h1><p>YOUR BOSS VEER HERE</p></div>', unsafe_allow_html=True)

# LOGIN / SIGNUP (unchanged)
if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
    with tab1:
        username = st.text_input("Username", key="login_u")
        password = st.text_input("Password", type="password", key="login_p")
        if st.button("Login", use_container_width=True):
            uid = db.verify_user(username, password)
            if uid:
                st.session_state.logged_in = True
                st.session_state.user_id = uid
                st.session_state.username = username
                st.success("Welcome back Boss!")
                st.rerun()
            else:
                st.error("Wrong credentials")
    with tab2:
        nu = st.text_input("New Username", key="nu")
        np = st.text_input("New Password", type="password", key="np")
        cp = st.text_input("Confirm", type="password", key="cp")
        if st.button("Create Account", use_container_width=True):
            if np == cp and nu and np:
                ok, msg = db.create_user(nu, np)
                st.write(msg if not ok else "Account created! Login now")
            else:
                st.error("Passwords don't match")

else:
    # SIDEBAR
    st.sidebar.markdown(f"### 👑 {st.session_state.username.upper()}")
    st.sidebar.markdown(f"**ID:** {st.session_state.user_id}")
    
    if st.sidebar.button("🛑 EMERGENCY STOP ALL", use_container_width=True, type="primary"):
        db.stop_all_tasks(st.session_state.user_id)
        st.success("ALL TASKS KILLED BY VEER!")
        st.rerun()

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        for key in ['logged_in', 'user_id', 'username']:
            st.session_state[key] = False if key == 'logged_in' else None
        st.rerun()

    # Load user config properly
    user_config = db.get_user_config(st.session_state.user_id)
    
    if user_config:
        if 'uploaded_cookies' not in st.session_state or not st.session_state.uploaded_cookies:
            st.session_state.uploaded_cookies = db.decrypt_cookies(user_config.get('cookies', ''))
        if 'uploaded_messages' not in st.session_state or not st.session_state.uploaded_messages:
            st.session_state.uploaded_messages = user_config.get('messages', '')

        tab1, tab2 = st.tabs(["⚙️ Configuration", "🚀 Automation"])

        with tab1:
            st.markdown("### ⚙️ VEER CONFIGURATION")
            chat_id = st.text_input("Chat IDs (comma separated)", value=user_config.get('chat_id', ''))
            name_prefix = st.text_input("Prefix / Hater Name", value=user_config.get('name_prefix', ''))
            col1, col2 = st.columns(2)
            with col1:
                min_delay = st.number_input("Min Delay", min_value=5, value=20)
            with col2:
                max_delay = st.number_input("Max Delay", min_value=10, value=60)

            cookie_text = st.text_area("Paste Cookies", value=st.session_state.uploaded_cookies, height=120)
            if cookie_text != st.session_state.uploaded_cookies:
                st.session_state.uploaded_cookies = cookie_text

            msg_file = st.file_uploader("Upload msg.txt", type="txt")
            if msg_file:
                st.session_state.uploaded_messages = msg_file.read().decode("utf-8")

            if st.session_state.uploaded_messages:
                st.success(f"Messages loaded: {len([x for x in st.session_state.uploaded_messages.split('\n') if x.strip()])}")

            if st.button("💾 SAVE CONFIG", use_container_width=True):
                if chat_id and st.session_state.uploaded_cookies and st.session_state.uploaded_messages:
                    db.update_user_config(
                        st.session_state.user_id, chat_id, name_prefix, min_delay,
                        db.encrypt_cookies(st.session_state.uploaded_cookies),
                        st.session_state.uploaded_messages, max_delay
                    )
                    st.success("SAVED BY VEER ✅")
                    st.rerun()
                else:
                    st.error("Fill all fields bhai")

        with tab2:
            st.markdown("### 🚀 NON-STOP AUTOMATION")
            tasks = db.get_tasks_for_user(st.session_state.user_id)
            active = [t for t in tasks if t.get('is_running')]
            total_sent = sum(t.get('message_count', 0) for t in tasks)

            c1, c2, c3 = st.columns(3)
            c1.metric("Active Tasks", len(active))
            c2.metric("Total Messages", total_sent)
            c3.metric("Status", "🟢 NON-STOP" if active else "🔴 Stopped")

            if st.button("▶️ START UNLIMITED AUTOMATION", use_container_width=True):
                cfg = db.get_user_config(st.session_state.user_id)
                if cfg.get('chat_id') and cfg.get('cookies') and cfg.get('messages'):
                    tid = generate_task_id()
                    start_automation(cfg, st.session_state.user_id, tid)
                    st.success(f"Task {tid} Started – AB YE KABHI NAHI RUKEGA!")
                    st.balloons()
                else:
                    st.error("Config save kar pehle")

            if active:
                st.dataframe([{
                    "Task ID": t['task_id'],
                    "Messages": t['message_count'],
                    "Status": "RUNNING 🟢"
                } for t in active], use_container_width=True)

            stop_id = st.text_input("Enter Task ID to stop")
            if st.button("⏹️ Stop Task"):
                if stop_id:
                    db.stop_task_by_id(st.session_state.user_id, stop_id)
                    st.success("Task stopped!")
                    st.rerun()

            st.markdown("### 🌙 LIVE CONSOLE")
            for log in st.session_state.automation_state.logs[-80:]:
                st.markdown(f'<div class="console-line">{log}</div>', unsafe_allow_html=True)

            if active:
                time.sleep(3)
                st.rerun()

st.markdown('<div class="footer">THEY CALL ME VEER<br>∞ E2EE OFFLINE NEVER DIES ∞</div>', unsafe_allow_html=True)
