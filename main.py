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
SYS = "You are Exquisite AI. Answer simply."
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
    safe = urllib.parse.quote(prompt)
    url = "https://image.pollinations.ai/prompt/" + safe + "?width=1024&height=1024"
    try:
        r = requests.get(url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.write(r.content)
        tmp.close()
        return "Image for: " + prompt, tmp.name
    except: return "Error loading image", None
def doc_fn(file, q):
    if file is None: return "Upload a document first"
    try:
        path = file.name if hasattr(file, "name") else file
        text = ""
        if path.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            for pg in reader.pages[:5]:
                text = text + (pg.extract_text() or "") + " "
        elif path.endswith(".txt"):
            f = open(path, "r", errors="ignore")
            text = f.read()[:8000]
            f.close()
        else: return "Upload PDF or TXT"
    except: return "Could not read file"
    if not q: q = "Summarize simply"
    return ask_ai("Document: " + text[:6000] + " Question: " + q, [])
def audio_fn(aud, q):
    if aud is None: return "Upload audio first", None
    try:
        path = aud.name if hasattr(aud, "name") else aud
        f = open(path, "rb")
        tr = client.audio.transcriptions.create(model="whisper-large-v3-turbo", file=f)
        f.close()
        txt = tr.text
        if not q: q = "Summarize it"
        ans = ask_ai("Said: " + txt + " Q: " + q, [])
        tts = gTTS(text=ans[:500], lang="en")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return "You said: " + txt + " Answer: " + ans, tmp.name
    except: return "Audio error", None
def start_pay(email, plan):
    if not email or AT not in email: return "Enter your email first", ""
    if plan == "Logo GH5": amt = 500
    else: amt = 1000
    head = {"Authorization": "Bearer " + pay_key, "Content-Type": "application/json"}
    data = {"email": email, "amount": amt, "callback_url": "https://exquisite-ai.onrender.com"}
    try:
        r = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=head, timeout=30)
        j = r.json()
        url = j["data"]["authorization_url"]
        ref = j["data"]["reference"]
        return "Click to pay: " + url + " Then paste Reference below", ref
    except: return "Payment error", ""
def verify_pay(ref, plan):
    if not ref: return "Paste Reference first", False, "Not paid"
    head = {"Authorization": "Bearer " + pay_key}
    try:
        r = requests.get("https://api.paystack.co/transaction/verify/" + ref, headers=head, timeout=30)
        j = r.json()
        ok = j["data"]["status"] == "success"
        if ok:
            PAID[ref] = plan
            return "Payment confirmed!", True, "PAID - " + plan
        return "Not confirmed yet", False, "Not paid"
    except: return "Verify error", False, "Not paid"
def logo_fn(prompt, paid, st):
    if not paid: return "Pay GH5 first", None
    return real_image("Professional logo, clean: " + prompt)
def video_fn(prompt, paid):
    if not paid: return "Pay GH10 first", None
    return real_image("Cinematic thumbnail: " + prompt)
def admin_login(pwd):
    if pwd != admin_pw: return "Access denied", False
    total = len(PAID)
    lc = 0
    vc = 0
    for v in PAID.values():
        if "Logo" in v: lc = lc + 1
        if "Video" in v: vc = vc + 1
    money = lc * 5 + vc * 10
    txt = "ADMIN OK. Total: " + str(total) + " Logo: " + str(lc) + " Video: " + str(vc) + " GH: " + str(money) + " " + str(PAID)
    return txt, True
def admin_manual(ref, plan, is_admin):
    if not is_admin: return "Unlock Admin first"
    if not ref: return "Enter Reference"
    PAID[ref] = plan
    return "Approved: " + ref + " for " + plan
with gr.Blocks(title="Exquisite AI") as demo:
    gr.HTML("<script>var C=['#ffffff','#1a0033','#1e3aff','#ff69b4','#00a651','#ffd700'];var i=0;function ch(){document.body.style.backgroundColor=C[i];i=(i+1)%C.length;}setInterval(ch,60000);</script>")
    gr.Markdown("# Exquisite AI")
    gr.Markdown("Ask anything, upload, voice, photos")
    paid_state = gr.State(False)
    admin_state = gr.State(False)
    chat_id_state = gr.State("")
    with gr.Tab("All"):
        chatbot = gr.Chatbot(height=450)
        msg = gr.Textbox(label="Ask anything", placeholder="Type here...")
        ask_btn = gr.Button("Ask", variant="primary")
        chat_st = gr.Textbox(label="Save Status", value="Login to save")
    with gr.Tab("Login"):
        gr.Markdown("### Login to save chats")
        user_in = gr.Textbox(label="Username")
        pin_in = gr.Textbox(label="PIN", type="password")
        login_btn = gr.Button("Login / Load My Chats")
        hist_drop = gr.Dropdown(label="My Saved Chats", choices=[], interactive=True)
        new_btn = gr.Button("New Chat")
        save_st = gr.Textbox(label="Status", value="Login to save")
        gr.Markdown("After login go to All to chat")
    login_btn.click(get_list, [user_in, pin_in], [hist_drop, save_st])
    new_btn.click(new_chat, [user_in, pin_in], [chatbot, chat_id_state, chat_st])
    hist_drop.change(load_chat, [hist_drop, user_in, pin_in, chat_id_state], [chatbot, chat_id_state, chat_st])
    msg.submit(chat_fn, [msg, chatbot, user_in, pin_in, chat_id_state], [chatbot, msg, chat_id_state, chat_st])
    ask_btn.click(chat_fn, [msg, chatbot, user_in, pin_in, chat_id_state], [chatbot, msg, chat_id_state, chat_st])
    with gr.Tab("Realistic Photo"):
        inp = gr.Textbox(label="Describe photo")
        out = gr.Textbox(label="Result")
        img = gr.Image(label="Your Photo")
        gr.Button("Generate").click(real_image, inp, [out, img])
    with gr.Tab("Document"):
        file = gr.File(label="Upload PDF TXT")
        q = gr.Textbox(label="Question")
        doc_out = gr.Textbox(label="Answer", lines=10)
        gr.Button("Ask").click(doc_fn, [file, q], doc_out)
    with gr.Tab("Audio / Voice"):
        aud_in = gr.Audio(type="filepath", label="Upload voice")
        q2 = gr.Textbox(label="Question")
        aud_out = gr.Textbox(label="Answer", lines=8)
        aud_reply = gr.Audio(label="Voice Reply")
        gr.Button("Listen").click(audio_fn, [aud_in, q2], [aud_out, aud_reply])
    with gr.Tab("Pay - Logo GH5 / Video GH10"):
        email = gr.Textbox(label="Email for receipt")
        plan = gr.Radio(["Logo GH5", "Video GH10"], value="Logo GH5", label="Choose Plan")
        pay_out = gr.Textbox(label="Pay Link", lines=3)
        ref_in = gr.Textbox(label="Paste Reference")
        status = gr.Textbox(label="Status", value="Not paid")
        ref_holder = gr.Textbox(label="Reference", visible=False)
        gr.Button("Get Pay Link").click(start_pay, [email, plan], [pay_out, ref_holder])
        gr.Button("I Have Paid - Verify").click(verify_pay, [ref_in, plan], [pay_out, paid_state, status])
    with gr.Tab("Logo GH5 - Locked"):
        logo_in = gr.Textbox(label="Describe logo")
        logo_out = gr.Textbox(label="Result")
        logo_img = gr.Image(label="Your Logo")
        gr.Button("Generate Logo").click(logo_fn, [logo_in, paid_state, status], [logo_out, logo_img])
    with gr.Tab("Video GH10 - Locked"):
        vid_in = gr.Textbox(label="Describe video")
        vid_out = gr.Textbox(label="Result")
        vid_img = gr.Image(label="Your Thumbnail")
        gr.Button("Generate Video").click(video_fn, [vid_in, paid_state], [vid_out, vid_img])
    with gr.Tab("Admin"):
        adm_pw_in = gr.Textbox(label="Admin Password", type="password")
        adm_out = gr.Textbox(label="Admin Dashboard", lines=8)
        gr.Button("Unlock Admin").click(admin_login, adm_pw_in, [adm_out, admin_state])
        adm_ref = gr.Textbox(label="Reference to approve")
        adm_plan = gr.Radio(["Logo GH5", "Video GH10"], value="Logo GH5", label="Plan")
        adm_m_out = gr.Textbox(label="Result")
        gr.Button("Manually Approve").click(admin_manual, [adm_ref, adm_plan, admin_state], adm_m_out)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("Starting on port", port)
    demo.launch(server_name="0.0.0.0", server_port=port)
