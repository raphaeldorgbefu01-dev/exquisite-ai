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
            f = open(path, "r", errors="ignore")
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
def admin_manual(ref, plan, is_admin):
    if not is_admin: return "Unlock Admin"
    if not ref: return "Enter Ref"
    PAID[ref] = plan
    return "OK " + ref
C1 = "@keyframes cc{0%{background:#fff}"
C2 = "20%{background:#1a0033}"
C3 = "40%{background:#1e3aff}"
C4 = "60%{background:#ff69b4}"
C5 = "80%{background:#00a651}"
C6 = "100%{background:#ffd700}}"
C7 = "body,.gradio-container{animation:cc 300s infinite;}"
T1 = ".chatbot table{display:block;overflow-x:auto;}"
T2 = ".chatbot table{white-space:normal;min-width:100%;}"
T3 = ".chatbot th,.chatbot td{white-space:nowrap;}"
T4 = ".chatbot th,.chatbot td{min-width:140px;}"
T5 = ".chatbot th,.chatbot td{word-break:keep-all;}"
T6 = ".chatbot th,.chatbot td{padding:10px;text-align:left;}"
T7 = ".chatbot td{white-space:normal;min-width:220px;}"
COLOR_CSS = C1 + C2 + C3 + C4 + C5 + C6 + C7
COLOR_CSS = COLOR_CSS + T1 + T2 + T3 + T4 + T5 + T6 + T7
with gr.Blocks(title="Exquisite AI",
 css=COLOR_CSS) as demo:
    gr.Markdown("# Exquisite AI")
    gr.Markdown("Ask anything, upload documents, voice, photos")
    paid_state = gr.State(False)
    admin_state = gr.State(False)
    chat_id_state = gr.State("")
    with gr.Tab("All"):
        chatbot = gr.Chatbot(height=450, elem_classes="chatbot")
        msg = gr.Textbox(label="Ask",
         placeholder="Type here...")
        ask_btn = gr.Button("Ask",
         variant="primary")
        chat_st = gr.Textbox(label="Status",
         value="Login to save")
    with gr.Tab("Login"):
        gr.Markdown("### Login to save")
        user_in = gr.Textbox(label="Username")
        pin_in = gr.Textbox(label="PIN",
         type="password")
        login_btn = gr.Button("Login")
        hist_drop = gr.Dropdown(
         label="My Chats", choices=[],
         interactive=True)
        new_btn = gr.Button("New Chat")
        save_st = gr.Textbox(label="Status",
         value="Login to save")
    login_btn.click(get_list,
     [user_in, pin_in], [hist_drop, save_st])
    new_btn.click(new_chat,
     [user_in, pin_in],
     [chatbot, chat_id_state, chat_st])
    hist_drop.change(load_chat,
     [hist_drop, user_in, pin_in, chat_id_state],
     [chatbot, chat_id_state, chat_st])
    msg.submit(chat_fn,
     [msg, chatbot, user_in, pin_in, chat_id_state],
     [chatbot, msg, chat_id_state, chat_st])
    ask_btn.click(chat_fn,
     [msg, chatbot, user_in, pin_in, chat_id_state],
     [chatbot, msg, chat_id_state, chat_st])
    with gr.Tab("Realistic Photo"):
        inp = gr.Textbox(label="Describe photo")
        out = gr.Textbox(label="Result")
        img = gr.Image(label="Your Photo")
        gr.Button("Generate").click(
         real_image, inp, [out, img])
    with gr.Tab("Document"):
        file = gr.File(label="Upload PDF TXT")
        q = gr.Textbox(label="Question")
        doc_out = gr.Textbox(label="Answer",
         lines=10)
        gr.Button("Ask").click(doc_fn,
         [file, q], doc_out)
    with gr.Tab("Audio / Voice"):
        aud_in = gr.Audio(type="filepath",
         label="Upload voice")
        q2 = gr.Textbox(label="Question")
        aud_out = gr.Textbox(label="Answer",
         lines=8)
        aud_reply = gr.Audio(label="Voice Reply")
        gr.Button("Listen").click(audio_fn,
         [aud_in, q2], [aud_out, aud_reply])
    with gr.Tab("Pay"):
        email = gr.Textbox(label="Email")
        plan = gr.Radio(["Logo GH5", "Video GH10"],
         value="Logo GH5", label="Plan")
        pay_out = gr.Textbox(label="Pay Link",
         lines=3)
        ref_in = gr.Textbox(label="Paste Reference")
        status = gr.Textbox(label="Status",
         value="Not paid")
        ref_holder = gr.Textbox(label="Ref",
         visible=False)
        gr.Button("Get Pay Link").click(
         start_pay, [email, plan],
         [pay_out, ref_holder])
        gr.Button("I Have Paid").click(
         verify_pay, [ref_in, plan],
         [pay_out, paid_state, status])
    with gr.Tab("Logo GH5"):
        logo_in = gr.Textbox(label="Describe logo")
        logo_out = gr.Textbox(label="Result")
        logo_img = gr.Image(label="Your Logo")
        gr.Button("Generate Logo").click(
         logo_fn, [logo_in, paid_state, status],
         [logo_out, logo_img])
    with gr.Tab("Video GH10"):
        vid_in = gr.Textbox(label="Describe video")
        vid_out = gr.Textbox(label="Result")
        vid_img = gr.Image(label="Thumbnail")
        gr.Button("Generate Video").click(
         video_fn, [vid_in, paid_state],
         [vid_out, vid_img])
    with gr.Tab("Admin"):
        adm_pw_in = gr.Textbox(
         label="Admin Password", type="password")
        adm_out = gr.Textbox(label="Dashboard",
         lines=8)
        gr.Button("Unlock Admin").click(
         admin_login, adm_pw_in,
         [adm_out, admin_state])
        adm_ref = gr.Textbox(label="Ref to approve")
        adm_plan = gr.Radio(
         ["Logo GH5", "Video GH10"],
         value="Logo GH5", label="Plan")
        adm_m_out = gr.Textbox(label="Result")
        gr.Button("Approve").click(
         admin_manual,
         [adm_ref, adm_plan, admin_state],
         adm_m_out)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("Starting on port", port)
    demo.launch(server_name="0.0.0.0",
     server_port=port)
