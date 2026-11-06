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
    new_id = save_current_chat(username, pin, chat_id, history)
    status = "Saved ✅" if (username and pin) else "Not saved - Login in Login tab to make it permanent"
    return history, "", new_id, status

def real_image(prompt):
    if not prompt:
        return "Type something", None
    safe = urllib.parse.quote(prompt)
    url = "https://image.pollinations.ai/prompt/" + safe + "?width=1024&height=1024"
    try:
        r = requests.get(url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.write(r.content)
        tmp.close()
        return "Image for: " + prompt, tmp.name
    except Exception:
        return "Error loading image", None

def doc_fn(file, question):
    if file is None:
        return "Upload a document first"
    try:
        path = file.name if hasattr(file, "name") else file
        text = ""
        if path.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            for p in reader.pages[:5]:
                text = text + (p.extract_text() or "") + " "
        elif path.endswith(".txt"):
            f = open(path, "r", errors="ignore")
            text = f.read()[:8000]
            f.close()
        else:
            return "Upload PDF or TXT"
    except Exception:
        return "Could not read file"
    q = question or "Summarize simply"
    return ask_ai("Document: " + text[:6000] + " Question: " + q, [])

def audio_fn(audio_file, question):
    if audio_file is None:
        return "Upload audio first", None
    try:
        path = audio_file.name if hasattr(audio_file, "name") else audio_file
        f = open(path, "rb")
        trans = client.audio.transcriptions.create(model="whisper-large-v3-turbo", file=f)
        f.close()
        transcript = trans.text
        q = question or "Summarize it"
        ans = ask_ai("Said: " + transcript + " Q: " + q, [])
        tts = gTTS(text=ans[:500], lang="en")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return "You said: " + transcript + " Answer: " + ans, tmp.name
    except Exception:
        return "Audio error", None

def start_pay(email, plan):
    if not email or "@" not in email:
        return "Enter your email first", ""
    amount = 500 if plan == "Logo GH5" else 1000
    headers = {"Authorization": "Bearer " + pay_key, "Content-Type": "application/json"}
    data = {"email": email, "amount": amount, "callback_url": "https://exquisite-ai.onrender.com"}
    try:
        r = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers, timeout=30)
        j = r.json()
        url = j["data"]["authorization_url"]
        ref = j["data"]["reference"]
        return "1. Click to pay with MoMo: " + url + " 2. After paying, copy your Reference and paste it below to unlock.", ref
    except Exception:
        return "Payment error. Check PAYSTACK_SECRET_KEY in Render.", ""

def verify_pay(ref, plan):
    if not ref:
        return "Paste your Paystack Reference first", False, "Not paid"
    headers = {"Authorization": "Bearer " + pay_key}
    try:
        r = requests.get("https://api.paystack.co/transaction/verify/" + ref, headers=headers, timeout=30)
        j = r.json()
        ok = j["data"]["status"] == "success"
        if ok:
            PAID[ref] = plan
            return "Payment confirmed! You can now generate " + plan, True, "PAID - " + plan
        return "Payment not confirmed yet. Wait and try again.", False, "Not paid"
    except Exception:
        return "Verify error", False, "Not paid"

def logo_fn(prompt, is_paid, plan_status):
    if not is_paid:
        return "Pay GH5 first to unlock Logo. Use Pay tab.", None
    return real_image("Professional logo, clean, modern: " + prompt)

def video_fn(prompt, is_paid):
    if not is_paid:
        return "Pay GH10 first to unlock Video. Use Pay tab.", None
    return real_image("Cinematic video thumbnail, high quality: " + prompt)

def admin_login(pwd):
    if pwd == admin_pw:
        total = len(PAID)
        logo_c = 0
        video_c = 0
        for v in PAID.values():
            if "Logo" in v:
                logo_c = logo_c + 1
            if "Video" in v:
                video_c = video_c + 1
        money = logo_c * 5 + video_c * 10
        txt = "ADMIN UNLOCKED. Total Paid: " + str(total) + " Logo: " + str(logo_c) + " Video: " + str(video_c) + " Total GH: " + str(money) + " Details: " + str(PAID)
        return txt, True
    return "Access denied. Wrong Admin Password.", False

def admin_manual(ref, plan, is_admin):
    if not is_admin:
        return "Enter Admin Password first and unlock Admin."
    if not ref:
        return "Enter Reference to manually approve."
    PAID[ref] = plan
    return "Manually approved: " + ref + " for " + plan + ". Tell user to use this Reference to verify."

with gr.Blocks(title="Exquisite AI", js=JS) as demo:
    gr.Markdown("# Exquisite AI")
    gr.Markdown("Ask anything, upload documents, send voice, generate real photos.........")
    paid_state = gr.State(False)
    admin_state = gr.State(False)
    chat_id_state = gr.State("")
    # --- NEW: LOGIN TAB SEPARATED ---
    with gr.Tab("Login"):
        gr.Markdown("### Login to save your chats permanently")
        gr.Markdown("Use same Username + PIN on any phone to get your old chats back.")
        user_in = gr.Textbox(label="Username", placeholder="e.g. kwame123")
        pin_in = gr.Textbox(label="PIN (remember it)", type="password", placeholder="e.g. 1234")
        login_btn = gr.Button("Login / Load My Chats")
        history_dropdown = gr.Dropdown(label="My Saved Chats - Click to Open", choices=[], interactive=True)
        new_btn = gr.Button("＋ New Chat")
        save_status = gr.Textbox(label="Status", value="Login to make chats permanent")
        gr.Markdown("After login, go to **All** tab to chat. Your chats will auto-save.")
    with gr.Tab("All"):
        # ONLY CHAT HERE - CLEAN
        chatbot = gr.Chatbot(height=450)
        msg = gr.Textbox(label="Ask anything", placeholder="Type here...")
        with gr.Row():
            ask_btn = gr.Button("Ask", variant="primary")
        chat_save_status = gr.Textbox(label="Save Status", value="Login in Login tab to make chats permanent")
        # Wire buttons AFTER both tabs are created
        login_btn.click(get_chat_list, [user_in, pin_in], [history_dropdown, save_status])
        new_btn.click(new_chat, [user_in, pin_in], [chatbot, chat_id_state, chat_save_status])
        history_dropdown.change(load_selected_chat, [history_dropdown, user_in, pin_in, chat_id_state], [chatbot, chat_id_state, chat_save_status])
        msg.submit(chat_fn, [msg, chatbot, user_in, pin_in, chat_id_state], [chatbot, msg, chat_id_state, chat_save_status])
        ask_btn.click(chat_fn, [msg, chatbot, user_in, pin_in, chat_id_state], [chatbot, msg, chat_id_state, chat_save_status])
    with gr.Tab("Realistic Photo"):
        inp = gr.Textbox(label="Describe photo")
        out = gr.Textbox(label="Result")
        img = gr.Image(label="Your Real Photo")
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
        email = gr.Textbox(label="Your Email for Paystack receipt")
        plan = gr.Radio(["Logo GH5", "Video GH10"], value="Logo GH5", label="Choose Plan")
        pay_out = gr.Textbox(label="Pay Link", lines=3)
        ref_in = gr.Textbox(label="Paste Paystack Reference after paying")
        status = gr.Textbox(label="Status", value="Not paid")
        ref_holder = gr.Textbox(label="Reference (auto)", visible=False)
        gr.Button("Get Pay Link").click(start_pay, [email, plan], [pay_out, ref_holder])
        gr.Button("I Have Paid - Verify").click(verify_pay, [ref_in, plan], [pay_out, paid_state, status])
    with gr.Tab("Logo GH5 - Locked"):
        logo_in = gr.Textbox(label="Describe your logo")
        logo_out = gr.Textbox(label="Result")
        logo_img = gr.Image(label="Your Logo")
        gr.Button("Generate Logo").click(logo_fn, [logo_in, paid_state, status], [logo_out, logo_img])
    with gr.Tab("Video GH10 - Locked"):
        vid_in = gr.Textbox(label="Describe your video")
        vid_out = gr.Textbox(label="Result")
        vid_img = gr.Image(label="Your Video Thumbnail")
        gr.Button("Generate Video").click(video_fn, [vid_in, paid_state], [vid_out, vid_img])
    with gr.Tab("Admin"):
        adm_pw_in = gr.Textbox(label="Admin Password", type="password")
        adm_out = gr.Textbox(label="Admin Dashboard", lines=8)
        gr.Button("Unlock Admin").click(admin_login, adm_pw_in, [adm_out, admin_state])
        adm_ref = gr.Textbox(label="Reference to manually approve")
        adm_plan = gr.Radio(["Logo GH5", "Video GH10"], value="Logo GH5", label="Plan")
        adm_manual_out = gr.Textbox(label="Manual Approve Result")
        gr.Button("Manually Approve Payment").click(admin_manual, [adm_ref, adm_plan, admin_state], adm_manual_out)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, allowed_paths=[".", "/tmp"], css=CSS)
