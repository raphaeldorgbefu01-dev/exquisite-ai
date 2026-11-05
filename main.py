import os
import requests
import gradio as gr
from openai import OpenAI
from gtts import gTTS
import tempfile
import urllib.parse
import json

groq_key = os.getenv("GROQ_API_KEY") or "dummy_key"
client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
MODELS = ["llama-3.1-8b-instant", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
WHISPER_MODELS = ["whisper-large-v3-turbo", "whisper-large-v3"]
CSS = ".chatbot{max-width:100%!important} .chatbot table{display:block;overflow-x:auto!important;width:100%;border-collapse:collapse} .chatbot th,.chatbot td{padding:10px;border:1px solid #ddd;white-space:nowrap!important;min-width:110px} .chatbot th{background:#f0f0f0} .gradio-container{background:white!important} .message,.chatbot,.block,.form,input,textarea{background:white!important;color:black!important} *{transition:background-color 1s ease!important}"
PWA_HEAD = '<link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#6a11cb"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><link rel="apple-touch-icon" href="/icon-192.png"><link rel="icon" href="/icon-192.png"><script>if("serviceWorker" in navigator){window.addEventListener("load",()=>{navigator.serviceWorker.register("/sw.js").catch(()=>{})})}const COLORS=["#ffffff","#1a0033","#1e3aff","#ff69b4","#00a651","#ffd700"];let colorIndex=0;function applyColor(){const bg=COLORS[colorIndex];document.body.style.backgroundColor=bg;document.documentElement.style.backgroundColor=bg;const cards=document.querySelectorAll(".gradio-container,.message,.chatbot,.block,.form,input,textarea");cards.forEach(b=>{b.style.backgroundColor="white";b.style.color="black";});const ths=document.querySelectorAll("th");ths.forEach(t=>{t.style.backgroundColor="#f0f0f0";t.style.color="black";});colorIndex=(colorIndex+1)%COLORS.length;}setInterval(applyColor,60000);window.addEventListener("load",()=>{setTimeout(applyColor,1000);});</script>'
SYSTEM_PROMPT = "You are Exquisite AI. Answer simply, clearly. NEVER use LaTeX. Use plain text: CO2, H2O, C6H12O6, O2. For equation show: 6CO2 + 6H2O --Light energy--> C6H12O6 + 6O2. FOR TABLES: Use MAX 3 columns, headers SHORT, each cell max 3-4 short words. Use headings, bold, bullet points."

def ask_ai(prompt, history=[]):
    if groq_key == "dummy_key":
        return "Add GROQ_API_KEY in Render Environment"
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-6:]:
        if isinstance(h, dict) and "role" in h and "content" in h:
            content = h["content"]
            if isinstance(content, list):
                content = " ".join([str(c) for c in content])
            if h["role"] in ["user", "assistant"]:
                msgs.append({"role": h["role"], "content": str(content)})
    msgs.append({"role": "user", "content": prompt})
    last_err = ""
    for model in MODELS:
        try:
            res = client.chat.completions.create(model=model, messages=msgs)
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
    safe = urllib.parse.quote(prompt + ", realistic photo, high quality, 4k")
    url = "https://image.pollinations.ai/prompt/" + safe + "?width=1024&height=1024&seed=42&nologo=true"
    try:
        r = requests.get(url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.write(r.content)
        tmp.close()
        return "Realistic image for: " + prompt, tmp.name
    except Exception as e:
        return "Error loading image", None

def doc_fn(file, question):
    if file is None:
        return "Upload a document first"
    text = ""
    try:
        path = file.name if hasattr(file, 'name') else file
        if path.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            for p in reader.pages[:5]:
                text += (p.extract_text() or "") + "\n"
        elif path.endswith(".txt"):
            with open(path, 'r', errors='ignore') as f:
                text = f.read()[:8000]
        elif path.endswith(".docx"):
            import docx
            d = docx.Document(path)
            text = "\n".join([p.text for p in d.paragraphs])[:8000]
        else:
            return "Please upload PDF, TXT or DOCX"
    except Exception as e:
        return "Could not read file"
    if not question:
        question = "Summarize this document simply"
    return ask_ai("Document: " + text[:6000] + " Question: " + question, [])

def audio_fn(audio_file, question):
    if audio_file is None:
        return "Upload audio first", None
    try:
        path = audio_file.name if hasattr(audio_file, 'name') else audio_file
        transcript = ""
        for wm in WHISPER_MODELS:
            try:
                with open(path, "rb") as f:
                    trans = client.audio.transcriptions.create(model=wm, file=f)
                transcript = trans.text
                break
            except:
                continue
        if not transcript:
            return "Could not transcribe audio", None
        q = question or "What did I say? Summarize it"
        answer = ask_ai("User said: " + transcript + " Question: " + q, [])
        tts = gTTS(text=answer[:500], lang='en')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return "You said: " + transcript + " Answer: " + answer, tmp.name
    except Exception as e:
        return "Audio error", None

def logo_fn(prompt):
    pay = "<div style='padding:15px;background:#fff3cd;text-align:center'><h3>Logo - GH5</h3></div>"
    return pay, ask_ai("Give logo idea for: " + prompt, [])

def pres_fn(topic):
    pay = "<div style='padding:15px;background:#d1ecf1;text-align:center'><h3>Presentation - GH5</h3></div>"
    return pay, ask_ai("Create 5-slide outline for: " + topic, [])

def video_fn(script):
    pay = "<div style='padding:15px;background:#f8d7da;text-align:center'><h3>Video Ad - GH10</h3></div>"
    ad = ask_ai("Write 30-sec video ad script for: " + script, [])
    return pay, ad

def create_pwa_files():
    try:
        manifest = {"name": "Exquisite AI", "short_name": "Exquisite AI", "description": "Ask anything", "start_url": "/", "display": "standalone", "background_color": "#ffffff", "theme_color": "#6a11cb", "orientation": "portrait", "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]}
        with open("manifest.json", "w") as f:
            json.dump(manifest, f)
        with open("sw.js", "w") as f:
            f.write("self.addEventListener('fetch', (e) => { e.respondWith(fetch(e.request)); });")
        if not os.path.exists("icon-192.png"):
            from PIL import Image, ImageDraw
            for size, name in [(192, "icon-192.png"), (512, "icon-512.png")]:
                img = Image.new("RGB", (size, size), (106, 17, 203))
                d = ImageDraw.Draw(img)
                d.ellipse([size*0.15, size*0.15, size*0.85, size*0.85], fill=(255, 255, 255))
                d.text((size*0.38, size*0.38), "E", fill=(106, 17, 203))
                img.save(name)
    except Exception as e:
        print("PWA setup error")

create_pwa_files()

with gr.Blocks(title="Exquisite AI") as demo:
    gr.Markdown("# Exquisite AI\nAsk anything, upload documents
