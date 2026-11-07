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
CSS = ".chatbot table{display:block}"
SYS = "You are Exquisite AI. Answer simply."
JS = "setInterval(function(){},60000);"
PAID = {}
CHAT_FILE = "exquisite_chats.json"
AT = chr(64)
def load_all():
    if not os.path.exists(CHAT_FILE): return {}
    try:
        f = open(CHAT_FILE, "r")
        d = json.load(f)
        f.close()
        return d
    except: return {}
def save_all(d):
    try:
        f = open(CHAT_FILE, "w")
        json.dump(d, f)
        f.close()
    except: pass
def user_key(u, p):
    s = u.strip().lower() + "|" + p.strip()
    return hashlib.sha256(s.encode()).hexdigest()[:16]
def get_list(u, p):
    if not u or not p: return gr.update(choices=[], value=None), "Login first"
    k = user_key(u, p)
    d = load_all()
    chats = d.get(k, {})
    items = sorted(chats.items(), key=lambda x: x[1].get("updated", 0), reverse=True)
    ch = []
    for cid, c in items:
        t = c.get("title", "Chat")[:30]
        ch.append(t + " | " + cid)
    msg = "Welcome " + u + " You have " + str(len(ch)) + " chats"
    return gr.update(choices=ch, value=None), msg
def load_chat(sel, u, p, cur):
    if not sel or not u or not p: return [], cur, "Select a chat"
    cid = sel.split(" | ")[-1]
    k = user_key(u, p)
    d = load_all()
    chat = d.get(k, {}).get(cid, {})
    hist = chat.get("history", [])
    return hist, cid, "Opened: " + chat.get("title", "Chat")
def new_chat(u, p):
    cid = str(uuid.uuid4())[:8]
    if u and p:
        k = user_key(u, p)
        d = load_all()
        if k not in d: d[k] = {}
        d[k][cid] = {"title": "New Chat", "history": [], "updated": time.time()}
        save_all(d)
    return [], cid, "New chat started"
def save_chat(u, p, cid, hist):
    if not u or not p or not hist: return cid
    k = user_key(u, p)
    d = load_all()
    if k not in d: d[k] = {}
    if not cid: cid = str(uuid.uuid4())[:8]
    title = "New Chat"
    for h in hist:
        if isinstance(h, dict) and h.get("role") == "user":
            title = str(h.get("content", ""))[:40]
            break
    d[k][cid] = {"title": title, "history": hist, "updated": time.time()}
    save_all(d)
    return cid
def ask_ai(prompt, hist):
    msgs = [{"role": "system", "content": SYS}]
    for h in hist[-6:]:
        if isinstance(h, dict) and h.get("role") in ["user", "assistant"]: msgs.append({"role": h.get("role"), "content": str(h.get("content", ""))})
    msgs.append({"role": "user", "content": prompt})
    models = ["llama-3.1-8b-instant", "openai/gpt-oss-120b"]
    for m in models:
        try:
            r = client.chat.completions.create(model=m, messages=msgs)
            return r.choices[0].message.content
        except: continue
    return "Error, try again"
def chat_fn(msg, hist, u, p, cid):
    if not msg: return hist, "", cid, "Type something"
    if hist is None: hist = []
    reply = ask_ai(msg, hist)
    hist.append({"role": "user", "content": msg})
    hist.append({"role": "assistant", "content": reply})
    nid = save_chat(u, p, cid, hist)
    if u and p: st = "Saved"
    else: st = "Not saved - Login first"
    return hist, "", nid, st
def real_image(prompt):
    if not prompt: return "Type something", None
   
