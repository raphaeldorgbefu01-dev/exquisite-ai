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
            f = open(path, "r")
            text = f.read()[:8000]
            f.close()
        else: return "PDF or TXT only"
    except: return "Could not read"
    if not q: q = "Summarize"
    return ask_ai("Doc: " + text[:6000] +
     " Q: " + q, [])
def audio_fn(aud, q):
    if aud is None: return "Upload first", None
    try:
        path = aud.name if hasattr(aud, "name") else aud
        f = open(path, "rb")
        tr = client.audio.transcriptions.create(
         model="whisper-large-v3-turbo", file=f)
        f.close()
        txt = tr.text
        if not q: q = "Summarize"
        ans = ask_ai("Said: " + txt + " Q: " + q, [])
        tts = gTTS(text=ans[:500], lang="en")
        tmp = tempfile.NamedTemporaryFile(
         delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return "Said: " + txt + " Ans: " + ans, tmp.name
    except: return "Audio error", None
def start_pay(email, plan):
    if not email or AT not in email:
        return "Enter email", ""
    if plan == "Logo GH5": amt = 500
    else: amt = 1000
    head = {"Authorization": "Bearer " + pay_key,
     "Content-Type": "application/json"}
    data = {"email": email, "amount": amt,
     "callback_url": "https://exquisite-ai.onrender.com"}
    try:
        r = requests.post(
         "https://api.paystack.co/transaction/initialize",
         json=data, headers=head, timeout=30)
        j = r.json()
        url = j["data"]["authorization_url"]
        ref = j["data"]["reference"]
        m = "Pay here: " + url
        m = m + " Ref: " + ref
        return m, ref
    except: return "Pay error", ""
def verify_pay(ref, plan):
    if not ref: return "Paste Ref", False, "Not paid"
    head = {"Authorization": "Bearer " + pay_key}
    try:
        u2 = "https://api.paystack.co/transaction/verify/"
        r = requests.get(u2 + ref,
         headers=head, timeout=30)
        j = r.json()
        ok = j["data"]["status"] == "success"
        if ok:
            PAID[ref] = plan
            return "Paid!", True, "PAID - " + plan
        return "Not yet", False, "Not paid"
    except: return "Verify error", False, "Not paid"
def logo_fn(prompt, paid, st):
    if not paid: return "Pay GH5 first", None
    return real_image("Logo: " + prompt)
def video_fn(prompt, paid):
    if not paid: return "Pay GH10 first", None
    return real_image("Thumb: " + prompt)
def admin_login(pwd):
    if pwd != admin_pw:
        return "Denied", False
    total = len(PAID)
    lc = 0
    vc = 0
    for v in PAID.values():
        if "Logo" in v: lc = lc + 1
        if "Video" in v: vc = vc + 1
    money = lc * 5 + vc * 10
    txt = "ADMIN OK Total: " + str(total)
    txt = txt + " Logo: " + str(lc)
    txt = txt + " Video: " + str(vc)
    txt = txt + " GH: " + str(money)
    return txt, True
def admin_manual
