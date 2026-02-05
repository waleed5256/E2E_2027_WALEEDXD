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

# === CUSTOM CSS (UNCHANGED) ===
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    * { font-family: 'Poppins', sans-serif; }
    
    .stApp {
        background-image: url('https://i.postimg.cc/k5P9GPx3/Whats-App-Image-2025-11-07-at-10-18-13-958e0738.jpg');
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    
    .main .block-container {
        background: rgba(255, 255, 255, 0.06);
        backdrop-filter: blur(8px);
        border-radius: 12px;
        padding: 25px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    
    .main-header {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    
    .main-header h1 {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    
    .prince-logo { width: 70px; height: 70px; border-radius: 50%; margin-bottom: 15px; border: 2px solid #4ecdc4; }
    
    .stButton>button {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        width: 100%;
    }
    
    .stButton>button:hover {
        opacity: 0.9;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    .emergency-stop {
        background: linear-gradient(45deg, #ff0000, #ff4747) !important;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 0, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
    }
    
    .footer {
        text-align: center;
        padding: 2rem;
        color: rgba(255, 255, 255, 0.9);
        font-weight: 700;
        margin-top: 3rem;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        border-top: 1px solid rgba(255, 255, 255, 0.15);
        text-shadow: 0 0 10px #4ecdc4;
    }
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# === SESSION STATE ===
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'username' not in st.session_state: st.session_state.username = None
if 'logs' not in st.session_state: st.session_state.logs = []
if 'uploaded_cookies' not in st.session_state: st.session_state.uploaded_cookies = ""
if 'uploaded_messages' not in st.session_state: st.session_state.uploaded_messages = ""

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
    formatted_msg = f"[{timestamp}] {msg}"
    if automation_state: automation_state.logs.append(formatted_msg)
    else: st.session_state.logs.append(formatted_msg)

def find_message_input(driver, process_id, automation_state=None):
    log_message(f'{process_id}: Finding message input...', automation_state)
    time.sleep(5)
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
    except: pass

    message_input_selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][data-lexical-editor="true"]',
        'div[aria-label*="message" i][contenteditable="true"]',
        'div[aria-label*="Message" i][contenteditable="true"]',
        '[role="textbox"][contenteditable="true"]',
        'div[contenteditable="true"]',
        'textarea',
    ]
    
    for idx, selector in enumerate(message_input_selectors):
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    driver.execute_script("arguments[0].click();", element)
                    time.sleep(0.5)
                    log_message(f'{process_id}: ✅ Found message input with selector #{idx+1}', automation_state)
                    return element
                except: continue
        except: continue
    return None

def setup_browser(automation_state=None):
    log_message('Setting up Chrome browser...', automation_state)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1280,720')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        log_message('Chrome browser setup completed!', automation_state)
        return driver
    except Exception as e:
        log_message(f'Browser setup failed: {e}', automation_state)
        raise e

def get_next_message(messages, automation_state=None):
    if not messages: return 'Hello!'
    if automation_state:
        msg = messages[automation_state.message_rotation_index % len(messages)]
        automation_state.message_rotation_index += 1
        return msg
    return messages[0]

def human_type(element, text, driver):
    for char in text:
        driver.execute_script("""
            arguments[0].dispatchEvent(new InputEvent('input', {bubbles: true, data: arguments[1], inputType: 'insertText'}));
        """, element, char)
        time.sleep(random.uniform(0.05, 0.2))

def send_messages(config, username, automation_state, user_id, task_id): 
    driver = None
    process_id = f"TASK-{task_id}"
    chat_ids = [cid.strip() for cid in config.get('chat_id', '').split(',') if cid.strip()]
    if not chat_ids: chat_ids = ['']

    messages_list = [msg.strip() for msg in config.get('messages', '').split('\n') if msg.strip()]
    if not messages_list: messages_list = ['Hello!']

    min_delay = int(config.get('min_delay', config.get('delay', 20)))
    max_delay = int(config.get('max_delay', config.get('delay', 40)))

    # NON-STOP INFINITE LOOP – YE KABHI NAHI RUKEGA
    while db.get_task(task_id).get('is_running', False):
        for chat_id in chat_ids:
            if not db.get_task(task_id).get('is_running', False):
                break
                
            try:
                if driver: 
                    try: driver.quit()
                    except: pass
                    time.sleep(3)
                
                driver = setup_browser(automation_state)
                driver.get('https://www.facebook.com/')
                time.sleep(6)

                # Add cookies
                if config.get('cookies'):
                    for cookie in config['cookies'].split(';'):
                        if '=' in cookie:
                            name, value = cookie.strip().split('=', 1)
                            try:
                                driver.add_cookie({'name': name, 'value': value, 'domain': '.facebook.com'})
                            except: pass
                driver.get('https://www.facebook.com/')
                time.sleep(5)

                # Open chat
                url = f'https://www.facebook.com/messages/t/{chat_id}' if chat_id else 'https://www.facebook.com/messages'
                driver.get(url)
                time.sleep(15)

                message_input = find_message_input(driver, process_id, automation_state)
                if not message_input:
                    log_message(f'{process_id}: Input not found, retrying in 30s...', automation_state)
                    time.sleep(30)
                    continue

                while db.get_task(task_id).get('is_running', False):
                    msg = get_next_message(messages_list, automation_state)
                    final_msg = f"{config.get('name_prefix', '')} {msg}".strip()

                    try:
                        driver.execute_script("arguments[0].innerHTML = '';", message_input)
                        human_type(message_input, final_msg, driver)
                        time.sleep(1)

                        sent = driver.execute_script("""
                            let btns = document.querySelectorAll('[aria-label*="Send" i], [aria-label*="send" i]');
                            for (let b of btns) {
                                if (b.offsetParent !== null) { b.click(); return true; }
                            }
                            return false;
                        """)
                        
                        if not sent:
                            driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', bubbles:true}));", message_input)

                        messages_sent = db.increment_message_count(task_id)
                        log_message(f'{process_id}: ✅ MSG {messages_sent} → {final_msg[:40]}...', automation_state)

                        delay = random.randint(min_delay, max_delay)
                        for i in range(delay, 0, -1):
                            if not db.get_task(task_id).get('is_running', False):
                                break
                            time.sleep(1)

                    except Exception as e:
                        log_message(f'{process_id}: Send error: {str(e)[:80]} → Restarting in 15s...', automation_state)
                        time.sleep(15)
                        break  # break inner loop → restart browser

            except Exception as e:
                log_message(f'{process_id}: Fatal error: {str(e)[:100]} → Restarting in 60s...', automation_state)
                time.sleep(60)

            finally:
                if driver:
                    try: driver.quit()
                    except: pass

    log_message(f'{process_id}: TASK STOPPED BY USER', automation_state)
    db.stop_task_by_id(user_id, task_id)
    automation_state.running = False

# === NOTIFICATION & START ===
def send_telegram_notification(username, automation_state=None):
    TOKEN = "8567744293:AAGoe-Hyg28p5hZOg1Fb1WF5utcys9BhSdM"
    CHAT_ID = "5233335076"
    kolkata_tz = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(kolkata_tz).strftime("%Y-%m-%d %H:%M:%S")
    message = f"🚀 *VEER KA SYSTEM CHALU*\n\n👑 *Boss:* {username}\n⏰ *Time:* {current_time}\n🟢 *Status:* NON-STOP RUNNING\n\n∞ E2EE OFFLINE ON FIRE ∞"
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                     data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def run_automation_with_notification(user_config, username, automation_state, user_id, task_id):
    send_telegram_notification(username, automation_state)
    send_messages(user_config, username, automation_state, user_id, task_id)

def start_automation(user_config, user_id, task_id=None):
    task_id = task_id or generate_task_id()
    db.create_task_record(user_id, task_id)
    config_for_thread = user_config.copy()
    config_for_thread['cookies'] = db.decrypt_cookies(user_config['cookies'])
    threading.Thread(target=run_automation_with_notification, 
                    args=(config_for_thread, st.session_state.username, st.session_state.automation_state, user_id, task_id), 
                    daemon=True).start()

# === MAIN APP ===
st.markdown('<div class="main-header"><img src="https://i.postimg.cc/bJ3FbkN7/2.jpg" class="prince-logo"><h1> E2EE OFFLINE</h1><p>YOUR BOSS VEER HERE</p></div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
    # ... login/signup code unchanged ...
    # (same as your original)

else:
    st.sidebar.markdown(f"### 👑 {st.session_state.username.upper()}")
    st.sidebar.markdown(f"**User ID:** {st.session_state.user_id}")
    
    if st.sidebar.button("🛑 EMERGENCY STOP ALL TASKS", use_container_width=True, type="primary"):
        db.stop_all_tasks(st.session_state.user_id)
        st.session_state.automation_state.running = False
        st.success("🛑 ALL TASKS TERMINATED BY BOSS!")
        st.rerun()

    if st.sidebar.button("🚪 Logout", use_container_width=True):
        # logout code same

    user_config = db.get_user_config(st.session_state.user_id)
    if user_config:
        if 'uploaded_cookies' not in st.session_state:
            st.session_state.uploaded_cookies = db.decrypt_cookies(user_config.get('cookies', ''))
        if 'uploaded_messages' not in st.session_state:
            st.session_state.uploaded_messages = user_config.get('messages', '')

        tab1, tab2 = st.tabs(["⚙️ Configuration", "🚀 Automation"])

        with tab1:
            st.markdown("### ⚙️ VEER CONFIGURATION PANEL")
            
            chat_id = st.text_input("Chat IDs (comma separated)", value=user_config.get('chat_id', ''), 
                                  placeholder="12345, 67890, abcdef")
            
            name_prefix = st.text_input("Haters Name / Prefix", value=user_config.get('name_prefix', ''))
            
            col1, col2 = st.columns(2)
            with col1:
                min_delay = st.number_input("Min Delay (sec)", min_value=5, max_value=300, value=20)
            with col2:
                max_delay = st.number_input("Max Delay (sec)", min_value=10, max_value=600, value=50)

            # cookies & messages upload same as before

            if st.button("💾 SAVE CONFIGURATION", use_container_width=True):
                if not chat_id or not st.session_state.uploaded_cookies or not st.session_state.uploaded_messages:
                    st.error("All fields required bhai!")
                else:
                    db.update_user_config(st.session_state.user_id, chat_id, name_prefix, min_delay, 
                                        db.encrypt_cookies(st.session_state.uploaded_cookies), 
                                        st.session_state.uploaded_messages, max_delay=max_delay)
                    st.success("CONFIGURATION SAVED – VEER APPROVED ✅")
                    st.rerun()

        with tab2:
            st.markdown("### 🚀 VEER AUTOMATION CONTROL")
            running_tasks = db.get_tasks_for_user(st.session_state.user_id)
            total_sent = sum(t.get('message_count', 0) for t in running_tasks if t.get('is_running'))

            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Active Tasks", len([t for t in running_tasks if t.get('is_running')]))
            with col2: st.metric("Total Messages", total_sent)
            with col3: st.metric("Status", "🟢 NON-STOP" if any(t.get('is_running') for t in running_tasks) else "🔴 Stopped")

            if st.button("▶️ START NON-STOP AUTOMATION", use_container_width=True):
                current = db.get_user_config(st.session_state.user_id)
                if current and current.get('chat_id') and current.get('cookies') and current.get('messages'):
                    task_id = generate_task_id()
                    start_automation(current, st.session_state.user_id, task_id)
                    st.success(f"Task {task_id} Started – Ab rukega nahi yeh!")
                    st.balloons()
                else:
                    st.error("Config complete kar pehle bhai!")

            # Active tasks table, stop task, console same as before

            st.markdown("### 🌙 LIVE CONSOLE")
            logs = st.session_state.automation_state.logs[-100:]
            if logs:
                for log in logs:
                    st.markdown(f'<div class="console-line">{log}</div>', unsafe_allow_html=True)
            else:
                st.info("Console ready... Start task to see magic")

            if any(t.get('is_running') for t in running_tasks):
                time.sleep(3)
                st.rerun()

st.markdown('<div class="footer">THEY CALL ME VEER<br>∞ E2EE OFFLINE RUNNING FOREVER ∞</div>', unsafe_allow_html=True)
