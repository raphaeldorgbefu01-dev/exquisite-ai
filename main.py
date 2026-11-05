import os
import requests
import gradio as gr
from openai import OpenAI
from gtts import gTTS
import tempfile
import urllib.parse

groq_key = os.getenv("GROQ_API_KEY") or "dummy_key"
client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
CSS = ".chatbot table{display:block;overflow-x:auto!important}"
SYS = "You are Exquisite AI. Answer simply. NEVER use LaTeX."
COLOR_JS = "<script>var C=['#ffffff','#1a0033','#1e3aff','#ff69b4','#00a651','#ffd700'];var i=0;function ch(){document.body.style.backgroundColor=C[i];i=(i+1)%C.length;}setInterval(ch,60000);</script>"

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

def chat_fn(message, history):
    if not message:
        return history, ""
    if history is None:
        history = []
    reply = ask_ai(message, history)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    return history, ""

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
            with open(path, "r", errors="ignore") as f:
                text = f.read()[:8000]
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
        with open(path, "rb") as f:
            trans = client.audio.transcriptions.create(model="whisper-large-v3-turbo", file=f)
        transcript = trans.text
        q = question or "Summarize it"
        ans = ask_ai("Said: " + transcript + " Q: " + q, [])
        tts = gTTS(text=ans[:500], lang="en")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return "You said: " + transcript + " Answer: " + ans, tmp.name
    except Exception:
        return "Audio error", None

with gr.Blocks(title="Exquisite AI") as demo:
    gr.HTML(COLOR_JS)
    gr.Markdown("# Exquisite AI")
    gr.Markdown("Colour changes every 1 min")
    with gr.Tab("All"):
        chatbot = gr.Chatbot(height=400)
        msg = gr.Textbox(label="Ask anything")
        msg.submit(chat_fn, [msg, chatbot], [chatbot, msg])
        gr.Button("Ask").click(chat_fn, [msg, chatbot], [chatbot, msg])
    with gr.Tab("Realistic Photo"):
        inp = gr.Textbox(label="Describe photo")
        out = gr.Textbox(label="Result")
        img = gr.Image
