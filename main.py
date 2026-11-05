import os
import requests
import gradio as gr
from openai import OpenAI
from gtts import gTTS
import tempfile
import urllib.parse
import json

groq_key = os.getenv("GROQ_API_KEY")
if not groq_key:
    groq_key = "dummy_key"
client = OpenAI(
    api_key=groq_key,
    base_url="https://api.groq.com/openai/v1"
)
MODELS = [
    "llama-3.1-8b-instant",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b"
]
WHISPER_MODELS = [
    "whisper-large-v3-turbo",
    "whisper-large-v3"
]
CSS = ".chatbot table{display:block;"
CSS += "overflow-x:auto!important}"
CSS += ".chatbot th,.chatbot td{padding:10px;"
CSS += "border:1px solid #ddd;"
CSS += "white-space:nowrap!important;"
CSS += "min-width:110px}"
CSS += ".gradio-container{background:white!important}"
CSS += ".message,.chatbot,.block,.form{"
CSS += "background:white!important;color:black!important}"
PWA_HEAD = '<link rel="manifest"'
PWA_HEAD += ' href="/manifest.json">'
PWA_HEAD += '<meta name="theme-color"'
PWA_HEAD += ' content="#6a11cb">'
PWA_HEAD += '<script>'
PWA_HEAD += 'const COLORS=["#ffffff",'
PWA_HEAD += '"#1a0033","#1e3aff",'
PWA_HEAD += '"#ff69b4","#00a651","#ffd700"];'
PWA_HEAD += 'let ci=0;'
PWA_HEAD += 'function applyColor(){'
PWA_HEAD += 'const bg=COLORS[ci];'
PWA_HEAD += 'document.body.style.backgroundColor=bg;'
PWA_HEAD += 'const cards=document.querySelectorAll('
PWA_HEAD += '".gradio-container,.message,.chatbot");'
PWA_HEAD += 'cards.forEach(b=>{'
PWA_HEAD += 'b.style.backgroundColor="white";'
PWA_HEAD += 'b.style.color="black";});'
PWA_HEAD += 'ci=(ci+1)%COLORS.length;}'
PWA_HEAD += 'setInterval(applyColor,60000);'
PWA_HEAD += '</script>'
SYS = "You are Exquisite AI. "
SYS += "Answer simply, clearly. "
SYS += "NEVER use LaTeX. "
SYS += "Use plain text: CO2, H2O. "
SYS += "FOR TABLES: MAX 3 columns, "
SYS += "headers SHORT, cells SHORT."

def ask_ai(prompt, history=[]):
    if groq_key == "dummy_key":
        return "Add GROQ_API_KEY"
    msgs = []
    msgs.append({"role": "system", "content": SYS})
    for h in history[-6:]:
        if isinstance(h, dict):
            if "role" in h:
                if h["role"] in ["user", "assistant"]:
                    c = str(h.get("content", ""))
                    msgs.append({"role": h["role"], "content": c})
    msgs.append({"role": "user", "content": prompt})
    last_err = ""
    for model in MODELS:
        try:
            res = client.chat.completions.create(
                model=model,
                messages=msgs
            )
            return res.choices[0].message.content
        except Exception as e:
            last_err = str(e)
            continue
    return "Error: " + last_err

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
    base = "https://image.pollinations.ai/prompt/"
    url = base + safe
    url += "?width=1024&height=1024&seed=42"
    try:
        r = requests.get(url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".jpg"
        )
        tmp.write(r.content)
        tmp.close()
        return "Image for: " + prompt, tmp.name
    except Exception as e:
        return "Error loading image", None

def doc_fn(file, question):
    if file is None:
        return "Upload a document first"
    text = ""
    try:
        path = file.name
        if hasattr(file, "name") is False:
            path = file
        if path.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            for p in reader.pages[:5]:
                text += (p.extract_text() or "") + " "
        elif path.endswith(".txt"):
            with open(path, "r", errors="ignore") as f:
                text = f.read()[:8000]
        elif path.endswith(".docx"):
            import docx
            d = docx.Document(path)
            text = " ".join([p.text for p in d.paragraphs])
            text = text[:8000]
        else:
            return "Upload PDF, TXT or DOCX"
    except Exception as e:
        return "Could not read file"
    if not question:
        question = "Summarize simply"
    q2 = "Document: " + text[:6000]
    q2 += " Question: " + question
    return ask_ai(q2, [])

def audio_fn(audio_file, question):
    if audio_file is None:
        return "Upload audio first", None
    try:
        path = audio_file.name
        if hasattr(audio_file, "name") is False:
            path = audio_file
        transcript = ""
        for wm in WHISPER_MODELS:
            try:
                with open(path, "rb") as f:
                    trans = client.audio.transcriptions.create(
                        model=wm, file=f
                    )
                transcript = trans.text
                break
            except:
                continue
        if not transcript:
            return "Could not transcribe", None
        q = question or "Summarize it"
        ans = ask_ai("Said: " + transcript + " Q: " + q, [])
        tts = gTTS(text=ans[:500], lang="en")
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".mp3"
        )
        tts.save(tmp.name)
        out = "You said: " + transcript
        out += " Answer: " + ans
        return out, tmp.name
    except Exception as e:
        return "Audio error", None

def logo_fn(prompt):
    pay = "<h3>Logo - GH5</h3>"
    return pay, ask_ai("Logo idea for: " + prompt, [])

def pres_fn(topic):
    pay = "<h3>Presentation - GH5</h3>"
    return pay, ask_ai("Outline for: " + topic, [])

def video_fn(script):
    pay = "<h3>Video Ad - GH10</h3>"
    ad = ask_ai("Ad script for: " + script, [])
    return pay, ad

def create_pwa_files():
    try:
        manifest = {}
        manifest["name"] = "Exquisite AI"
        manifest["short_name"] = "Exquisite AI"
        manifest["start_url"] = "/"
        manifest["display"] = "standalone"
        manifest["background_color"] = "#ffffff"
        manifest["theme_color"] = "#6a11cb"
        manifest["icons"] = []
        manifest["icons"].append(
            {"src": "/icon-192.png",
             "sizes": "192x192",
             "type": "image/png"}
        )
        with open("manifest.json", "w") as f:
            json.dump(manifest, f)
        with open("sw.js", "w") as f:
            f.write("self.addEventListener('fetch',")
            f.write("(e)=>{e.respondWith(fetch(e.request))});")
        if not os.path.exists("icon-192.png"):
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (192, 192), (106, 17, 203))
            d = ImageDraw.Draw(img)
            d.ellipse([30, 30, 162, 162], fill=(255, 255, 255))
            d.text((75, 75), "E", fill=(106, 17, 203))
            img.save("icon-192.png")
            img.save("icon-512.png")
    except Exception as e:
        print("PWA error")

create_pwa_files()

with gr.Blocks(title="Exquisite AI") as demo:
    gr.Markdown("# Exquisite AI")
    gr.Markdown("Ask anything, upload docs, voice, photos")
    gr.Markdown("Colour changes every 1 min")
    with gr.Tab("All"):
        chatbot = gr.Chatbot(height=400, elem_classes=["chatbot"])
        msg = gr.Textbox(label="Ask anything")
        msg.submit(chat_fn, [msg, chatbot], [chatbot, msg])
        gr.Button("Ask").click(chat_fn, [msg, chatbot], [chatbot, msg])
    with gr.Tab("Realistic Photo"):
        inp = gr.Textbox(label="Describe photo")
        out = gr.Textbox
