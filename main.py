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
groq_key = os.getenv("GROQ_API_KEY")
pay_key = os.getenv("PAYSTACK_SECRET_KEY")
admin_pw = os.getenv("ADMIN_PASSWORD")
if not groq_key: groq_key = "dummy_key"
if not pay_key: pay_key = "dummy"
if not admin_pw: admin_pw = "admin123"
client = OpenAI(api_key=groq_key,
 base_url="https://api.groq.com/openai/v1")
SYS = "You are Exquisite AI."
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
    h = hashlib.sha256(s.encode())
    return h.hexdigest()[:16]
def get_list(u, p):
    if not u or not p:
        return gr.update(choices=[]), "Login"
    k = user_key(u, p)
    d = load_all()
    chats = d.get(k, {})
    items = sorted(chats.items(),
     key=lambda x: x[1].get("updated", 0),
     reverse=True)
    ch = []
    for cid, c in items:
        t = c.get("title", "Chat")[:30]
        ch.append(t + " | " + cid)
    m = "Welcome " + u
    m = m + " Chats: " + str(len(ch))
    return gr.update(choices=ch), m
def load_chat(sel, u, p, cur):
    if not sel or not u or not p:
        return [], cur, "Select chat"
    cid = sel.split(" | ")[-1]
    k = user_key(u, p)
    d = load_all()
    chat = d.get(k, {}).get(cid, {})
    hist = chat.get("history", [])
    t = "Opened: " + chat.get("title", "Chat")
    return hist, cid, t
def new_chat(u, p):
    cid = str(uuid.uuid4())[:8]
    if u and p:
        k = user_key(u, p)
        d = load_all()
        if k not in d: d[k] = {}
        d[k][cid] = {"title": "New",
         "history": [], "updated": time.time()}
        save_all(d)
    return [], cid, "New chat"
def save_chat(u, p, cid, hist):
    if not u or not p or not hist: return cid
    k = user_key(u, p)
    d = load_all()
    if k not in d: d[k] = {}
    if not cid: cid = str(uuid.uuid4())[:8]
    title = "New Chat"
    for h in hist:
        if isinstance(h, dict):
            if h.get("role") == "user":
                title = str(h.get("content", ""))[:40]
                break
    d[k][cid] = {"title": title,
     "history": hist, "updated": time.time()}
    save_all(d)
    return cid
def ask_ai(prompt, hist):
    msgs = [{"role": "system", "content": SYS}]
    for h in hist[-6:]:
        if isinstance(h, dict):
            r = h.get("role")
            if r in ["user", "assistant"]:
                c = str(h.get("content", ""))
                msgs.append({"role": r, "content": c})
    msgs.append({"role": "user", "content": prompt})
    models = ["llama-3.1-8b-instant",
     "openai/gpt-oss-120b"]
    for m in models:
        try:
            r = client.chat.completions.create(
             model=m, messages=msgs)
            return r.choices[0].message.content
        except: continue
    return "Error, try again"
def chat_fn(msg, hist, u, p, cid):
    if not msg: return hist, "", cid, "Type"
    if hist is None: hist = []
    reply = ask_ai(msg, hist)
    hist.append({"role": "user", "content": msg})
    hist.append({"role": "assistant",
     "content": reply})
    nid = save_chat(u, p, cid, hist)
    if u and p: st = "Saved"
    else: st = "Login to save"
    return hist, "", nid, st
def real_image(prompt):
    if not prompt: return "Type", None
    safe = urllib.parse.quote(prompt)
    url = "https://image.pollinations.ai/prompt/"
    url = url + safe + "?width=1024&height=1024"
    try:
        r = requests.get(url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(
         delete=False, suffix=".jpg")
        tmp.write(r.content)
        tmp.close()
        return "Image: " + prompt, tmp.name
    except: return "Image error", None
def doc_fn(file, q):
    if file is None: return "Upload first"
    try:
        path = file.name if hasattr(file, "name") else file
        text = ""
        if path.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            for pg in reader.pages[:5]:
                text = text + (pg.extract_text() or "")
        elif path.endswith(".txt"):
            f = open(path, "r", errors
