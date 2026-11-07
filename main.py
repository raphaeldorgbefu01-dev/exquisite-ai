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
if not groq_key:
    groq_key = "dummy_key"
pay_key = os.getenv("PAYSTACK_SECRET_KEY")
if not pay_key:
    pay_key = "dummy"
admin_pw = os.getenv("ADMIN_PASSWORD")
if not admin_pw:
    admin_pw = "admin123"
client = OpenAI(
    api_key=groq_key,
    base_url="https://api.groq.com/openai/v1"
)
CSS = ".chatbot table{display:block}"
SYS = "You are Exquisite AI. Answer simply."
JS = "setInterval(function(){},60000);"
PAID = {}
CHAT_FILE = "exquisite_chats.json"

def load_all():
    if not os.path.exists(CHAT_FILE):
        return {}
    try:
        f = open(CHAT_FILE, "r")
        d = json.load(f)
        f.close()
        return d
    except:
        return {}

def save_all(d):
    try:
        f = open(CHAT_FILE, "w")
        json.dump(d, f)
        f.close()
    except:
        pass

def user_key(u, p):
    s = u.strip().lower() + "|" + p.strip()
    h = hashlib.sha256(s.encode())
    return h.hexdigest()[:16]

def get_list(u, p):
    if not u or not p:
        return gr.update(
            choices=[],
            value=None
        ), "Login first"
    k = user_key(u, p)
    d = load_all()
    chats = d.get(k, {})
    items = sorted(
        chats.items(),
        key=lambda x: x[1].get("updated", 0),
        reverse=True
    )
    ch = []
    for cid, c in items:
        t = c.get("title", "Chat")[:30]
        ch.append(t + " | " + cid)
    msg = "Welcome " + u
    msg = msg + " You have "
    msg = msg + str(len(ch))
    msg = msg + " chats"
    return gr.update(
        choices=ch,
        value=None
    ), msg

def load_chat(sel, u, p, cur):
    if not sel or not u or not p:
        return [], cur, "Select a chat"
    cid = sel.split(" | ")[-1]
    k = user_key(u, p)
    d = load_all()
    chat = d.get(k, {}).get(cid, {})
    hist = chat.get("history", [])
    t = chat.get("title", "Chat")
    return hist, cid, "Opened: " + t

def new_chat(u, p):
    cid = str(uuid.uuid4())[:8]
    if u and p:
        k = user_key(u, p)
        d = load_all()
        if k not in d:
            d[k] = {}
        d[k][cid] = {
            "title": "New Chat",
            "history": [],
            "updated": time.time()
        }
        save_all(d)
    return [], cid, "New chat started"

def save_chat(u, p, cid, hist):
    if not u or not p or not hist:
        return cid
    k = user_key(u, p)
    d = load_all()
    if k not in d:
        d[k] = {}
    if not cid:
        cid = str(uuid.uuid4())[:8]
    title = "New Chat"
    for h in hist:
        if isinstance(h, dict):
            if h.get("role") == "user":
                title = str(h.get("content", ""))[:40]
                break
    d[k][cid] = {
        "title": title,
        "history": hist,
        "updated": time.time()
    }
    save_all(d)
    return cid

def ask_ai(prompt, hist):
    msgs = []
    msgs.append(
        {"role": "system", "content": SYS}
    )
    for h in hist[-6:]:
        if isinstance(h, dict):
            r = h.get("role")
            if r in ["user", "assistant"]:
                msgs.append(
                    {"role": r, "content": str(h.get("content", ""))}
                )
    msgs.append({"role": "user", "content": prompt})
    models = [
        "llama-3.1-8b-instant",
        "openai/gpt-oss-120b"
    ]
    for m in models:
        try:
            r = client.chat.completions.create(
                model=m,
                messages=msgs
            )
            return r.choices[0].message.content
        except:
            continue
    return "Error, try again"

def chat_fn(msg, hist, u, p, cid):
    if not msg:
        return hist, "", cid, "Type something"
    if hist is None:
        hist = []
    reply = ask_ai(msg, hist)
    hist.append({"role": "user", "content": msg})
    hist.append({"role": "assistant", "content": reply})
    nid = save_chat(u, p, cid, hist)
    if u and p:
        st = "Saved"
    else:
        st = "Not saved - Login first"
    return hist, "", nid, st

def real_image(prompt):
    if not prompt:
        return "Type something", None
    safe = urllib.parse.quote(prompt)
    base = "https://image.pollinations.ai/prompt/"
    url = base + safe
    url = url + "?width=1024&height=1024"
    try:
        r = requests.get(url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        )
        tmp.write(r.content)
        tmp.close()
        return "Image for: " + prompt, tmp.name
    except:
        return "Error loading image", None

def doc_fn(file, q):
    if file is None:
        return "Upload a document first"
    try:
        path = file.name
        if hasattr(file, "name"):
            path = file.name
        else:
            path = file
        text = ""
        if path.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            for pg in reader.pages[:5]:
                t = pg.extract_text() or ""
                text = text + t + " "
        elif path.endswith(".txt"):
            f = open(path, "r", errors="ignore")
            text = f.read()[:8000]
            f.close()
        else:
            return "Upload PDF or TXT"
    except:
        return "Could not read file"
    if not q:
        q = "Summarize simply"
    full = "Document: " + text[:6000]
    full = full + " Question: " + q
    return ask_ai(full, [])

def audio_fn(aud, q):
    if aud is None:
        return "Upload audio first", None
    try:
        path = aud.name
        if hasattr(aud, "name"):
            path = aud.name
        else:
            path = aud
        f = open(path, "rb")
        tr = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=f
        )
        f.close()
        txt = tr.text
        if not q:
            q = "Summarize it"
        full = "Said: " + txt + " Q: " + q
        ans = ask_ai(full, [])
        tts = gTTS(text=ans[:500], lang="en")
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp3"
        )
        tts.save(tmp.name)
        out = "You said: " + txt
        out = out + " Answer: " + ans
        return out, tmp.name
    except:
        return "Audio error", None

def start_pay(email, plan):
    if not email or "@" not in email
