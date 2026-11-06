import os
import requests
import gradio as gr
from openai import OpenAI
from gtts import gTTS
import tempfile
import urllib.parse
import json
import hashlib
import time
import uuid

groq_key = os.getenv("GROQ_API_KEY") or "dummy_key"
pay_key = os.getenv("PAYSTACK_SECRET_KEY") or "dummy"
admin_pw = os.getenv("ADMIN_PASSWORD") or "admin123"
client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
CSS = ".chatbot table{display:block;overflow-x:auto!important}"
SYS = "You are Exquisite AI. Answer simply. NEVER use LaTeX."
JS = "var C=['#ffffff','#1a0033','#1e3aff','#ff69b4','#00a651','#ffd700'];var i=0;function ch(){document.body.style.backgroundColor=C[i];i=(i+1)%C.length;}setInterval(ch,60000);"
PAID = {}

# --- PERMANENT CHAT STORAGE ---
CHAT_FILE = "exquisite_chats.json"

def load_all_chats():
    if not os.path.exists(CHAT_FILE):
        return {}
    try:
        with open(CHAT_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_all_chats(data):
    try:
        with open(CHAT_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Save error:", e)

def make_user_key(username, pin):
    return hashlib.sha256((username.strip().lower() + "|" + pin.strip()).encode()).hexdigest()[:16]

def get_chat_list(username, pin):
    if not username or not pin:
        return gr.update(choices=[], value=None), "Login with Username + PIN to see history"
    key = make_user_key(username, pin)
    data = load_all_chats()
    user_chats = data.get(key, {})
    items = sorted(user_chats.items(), key=lambda x: x[1].get("updated", 0), reverse=True)
    choices = []
    for cid, c in items:
        title = c.get("title", "Chat")[:35]
        choices.append(f"{title} | {cid}")
    return gr.update(choices=choices, value=None), f"Welcome {username}! You have {len(choices)} saved chats. Now go to All tab to chat."

def load_selected_chat(selected, username, pin, current_id):
    if not selected or not username or not pin:
        return [], current_id, "Select a chat in Login tab first"
    cid = selected.split(" | ")[-1]
    key = make_user_key(username, pin)
    data = load_all_chats()
    chat = data.get(key, {}).get(cid, {})
    history = chat.get("history", [])
    return history, cid, f"Opened: {chat.get('title','Chat')} - Go to All tab to continue"

def new_chat(username, pin):
    cid = str(uuid.uuid4())[:8]
    if username and pin:
        key = make_user_key(username, pin)
        data = load_all_chats()
        if key not in data:
            data[key] = {}
        data[key][cid] = {"title": "New Chat", "history": [], "updated": time.time()}
        save_all_chats(data)
    return [], cid, "New chat started - Go to All tab to chat. It will auto-save"

def save_current_chat(username, pin, chat_id, history):
    if not username or not pin or not history:
        return chat_id
    key = make_user_key(username, pin)
    data = load_all_chats()
    if key not in data:
        data[key] = {}
    if not chat_id:
        chat_id = str(uuid.uuid4())[:8]
    title = "New Chat"
    for h in history:
        if isinstance(h, dict) and h.get("role") == "user":
            title = str(h.get("content",""))[:40]
            break
    data[key][chat_id] = {"title": title, "history": history, "updated": time.time()}
    save_all_chats(data)
    return chat_id

def ask_ai(prompt, history):
    msgs = [{"role": "system", "content": SYS}]
    for h in history[-6:]:
        if isinstance(h, dict) and h.get("role") in ["user", "assistant"]:
            msgs.append({"role": h["role"], "content": str(h.get("content", ""))})
    msgs.append({"role": "user", "content": prompt})
    for m in ["llama-3.1-8b-instant", "openai/gpt-oss-120b"]:
        try:
            r = client.chat.completions.create(model=m, messages=msgs)
            return r.choices[0].message.content
        except Exception:
            continue
    return "Error, try again"

def chat_fn(message, history, username, pin, chat_id):
    if not message:
        return history, "", chat_id, "Type something"
    if history is None:
        history = []
    reply = ask_ai(message, history)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    new
