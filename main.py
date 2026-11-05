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

CSS = ".chatbot table{display:block;overflow-x:auto;width:100%} .chatbot th,.chatbot td{padding:8px;border:1px solid #ddd;min-width:90px;max-width:180px} .chatbot th{background:#f0f0f0}"

PWA_HEAD = '<link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#6a11cb"><meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Exquisite AI"><link rel="apple-touch-icon" href="/icon-192.png"><link rel="icon" href="/icon-192.png"><script>if("serviceWorker" in navigator){window.addEventListener("load",()=>{navigator.serviceWorker.register("/sw.js").catch(()=>{})})}</script>'

SYSTEM_PROMPT = "You are Exquisite AI, helpful like Meta AI and Gemini. Answer simply, clearly, friendly. NEVER use LaTeX like [ ] or text{} or $$. Use plain text: CO2, H2O, C6H12O6, O2. For equation show: 6CO2 + 6H2O --Light energy--> C6H12O6 + 6O2. In words: Carbon dioxide + Water + Light energy -> Glucose + Oxygen. FOR TABLES: Use MAX 3 columns, headers SHORT, each cell max 4-5 words, never long sentences in table. Use headings, bold, bullet points."

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

with gr.Blocks(title="Exquisite AI", head=PWA_HEAD) as demo:
    gr.Markdown("# Exquisite AI\nAsk anything, upload documents, send voice, generate real photos\n\nTo install as App: Chrome 3 dots -> Add to Home Screen -> Install")
    with gr.Tab("Chat - Like Meta AI"):
        chatbot = gr.Chatbot(height=400, elem_classes=["chatbot"])
        msg = gr.Textbox(label="Ask anything...", placeholder="e.g. Equation for photosynthesis")
        msg.submit(chat_fn, [msg, chatbot], [chatbot, msg])
        gr.Button("Ask").click(chat_fn, [msg, chatbot], [chatbot, msg])
    with gr.Tab("Realistic Photo"):
        inp = gr.Textbox(label="Describe photo", placeholder="Luxury car")
        out = gr.Textbox(label="Result")
        img = gr.Image(label="Your Real Photo")
        gr.Button("Generate Real Photo").click(real_image, inp, [out, img])
    with gr.Tab("Document"):
        file = gr.File(label="Upload PDF / TXT / DOCX", file_types=[".pdf", ".txt", ".docx"])
        q = gr.Textbox(label="What do you want to know?")
        doc_out = gr.Textbox(label="Answer", lines=10)
        gr.Button("Ask About Document").click(doc_fn, [file, q], doc_out)
    with gr.Tab("Audio / Voice"):
        aud_in = gr.Audio(type="filepath", label="Upload voice or record")
        q2 = gr.Textbox(label="Question about audio")
        aud_out = gr.Textbox(label="Transcript + Answer", lines=8)
        aud_reply = gr.Audio(label="Voice Reply")
        gr.Button("Listen & Answer").click(audio_fn, [aud_in, q2], [aud_out, aud_reply])
    with gr.Tab("Logo - GH5"):
        l1 = gr.Textbox(label="Business name")
        p1 = gr.HTML()
        o1 = gr.Textbox(label="Logo Idea")
        gr.Button("Generate Logo - GH5").click(logo_fn, l1, [p1, o1])
    with gr.Tab("Presentation - GH5"):
        l2 = gr.Textbox(label="Topic")
        p2 = gr.HTML()
        o2 = gr.Textbox(label="Outline", lines=10)
        gr.Button("Generate - GH5").click(pres_fn, l2, [p2, o2])
    with gr.Tab("Video Ad - GH10"):
        l3 = gr.Textbox(label="Business")
        p3 = gr.HTML()
        o3 = gr.Textbox(label="Script", lines=10)
        gr.Button("Generate - GH10").click(video_fn, l3, [p3, o3])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, allowed_paths=[".", "/tmp"], css=CSS)
