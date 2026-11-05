import os
import requests
import gradio as gr
from openai import OpenAI
from gtts import gTTS
import tempfile
import urllib.parse

groq_key = os.getenv("GROQ_API_KEY") or "dummy_key"
client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
MODEL = "llama-3.3-70b-versatile"
WHISPER_MODEL = "whisper-large-v3"

def ask_ai(prompt, history=[]):
    if groq_key == "dummy_key":
        return "⚠️ Add GROQ_API_KEY in Render → Environment"
    try:
        msgs = [{"role": "system", "content": "You are Exquisite AI, helpful like Meta AI. Answer simply, clearly, friendly."}]
        for h in history[-6:]:
            if isinstance(h, dict) and "role" in h:
                msgs.append(h)
        msgs.append({"role": "user", "content": prompt})
        res = client.chat.completions.create(model=MODEL, messages=msgs)
        return res.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

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
        return "Type something e.g. Luxury car", None
    safe = urllib.parse.quote(prompt + ", realistic photo, high quality, 4k, detailed")
    url = f"https://image.pollinations.ai/prompt/{safe}?width=1024&height=1024&seed=42&nologo=true"
    try:
        r = requests.get(url, timeout=30)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.write(r.content)
        tmp.close()
        return f"Realistic image for: {prompt}", tmp.name
    except Exception as e:
        return f"Error loading image: {e}", None

def doc_fn(file, question):
    if file is None:
        return "Upload a document first (PDF, TXT)"
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
        return f"Could not read file: {e}"
    if not question:
        question = "Summarize this document simply"
    return ask_ai(f"Document content:\n{text[:6000]}\n\nQuestion: {question}", [])

def audio_fn(audio_file, question):
    if audio_file is None:
        return "Upload an audio / voice note first", None
    try:
        path = audio_file.name if hasattr(audio_file, 'name') else audio_file
        with open(path, "rb") as f:
            trans = client.audio.transcriptions.create(model=WHISPER_MODEL, file=f)
        transcript = trans.text
        q = question or "What did I say? Summarize it"
        answer = ask_ai(f"User said in audio: {transcript}\nQuestion: {q}", [])
        tts = gTTS(text=answer[:500], lang='en')
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        return f"You said: {transcript}\n\nAnswer: {answer}", tmp.name
    except Exception as e:
        return f"Audio error: {e}", None

def logo_fn(prompt):
    pay = "<div style='padding:15px;background:#fff3cd;border-radius:10px;text-align:center'><h3>Logo - GH₵5 via Paystack MoMo</h3></div>"
    return pay, ask_ai(f"Give logo idea for: {prompt}. Colors, font, symbol.", [])

def pres_fn(topic):
    pay = "<div style='padding:15px;background:#d1ecf1;border-radius:10px;text-align:center'><h3>Presentation - GH₵5</h3></div>"
    return pay, ask_ai(f"Create 5-slide business presentation outline for: {topic}", [])

def video_fn(script):
    pay = "<div style='padding:15px;background:#f8d7da;border-radius:10px;text-align:center'><h3>Video Ad - GH₵10</h3></div>"
    ad = ask_ai(f"Write 30-sec video ad script for: {script}", [])
    return pay, ad

with gr.Blocks(title="Exquisite AI") as demo:
    gr.Markdown("# ✨ Exquisite AI\nAsk anything, upload documents, send voice, generate real photos")
    
    with gr.Tab("💬 Chat - Like Meta AI"):
        chatbot = gr.Chatbot(height=400)
        msg = gr.Textbox(label="Ask anything...", placeholder="e.g. Explain swinging and hopping to class 2")
        msg.submit(chat_fn, [msg, chatbot], [chatbot, msg])
        gr.Button("Ask").click(chat_fn, [msg, chatbot], [chatbot, msg])

    with gr.Tab("🖼️ Realistic Photo"):
        inp = gr.Textbox(label="Describe photo", placeholder="Luxury car")
        out = gr.Textbox(label="Result")
        img = gr.Image(label="Your Real Photo")
        gr.Button("Generate Real Photo").click(real_image, inp, [out, img])

    with gr.Tab("📄 Document"):
        file = gr.File(label="Upload PDF / TXT / DOCX", file_types=[".pdf", ".txt", ".docx"])
        q = gr.Textbox(label="What do you want to know about this document?")
        doc_out = gr.Textbox(label="Answer", lines=10)
        gr.Button("Ask About Document").click(doc_fn, [file, q], doc_out)

    with gr.Tab("🎤 Audio / Voice"):
        aud_in = gr.Audio(type="filepath", label="Upload voice or record")
        q2 = gr.Textbox(label="Question about audio (optional)")
        aud_out = gr.Textbox(label="Transcript + Answer", lines=8)
        aud_reply = gr.Audio(label="Voice Reply")
        gr.Button("Listen & Answer").click(audio_fn, [aud_in, q2], [aud_out, aud_reply])

    with gr.Tab("🎨 Logo - GH₵5"):
        l1 = gr.Textbox(label="Business name"); p1 = gr.HTML(); o1 = gr.Textbox(label="Logo Idea")
        gr.Button("Generate Logo - GH₵5").click(logo_fn, l1, [p1, o1])

    with gr.Tab("📊 Presentation - GH₵5"):
        l2 = gr.Textbox(label="Topic"); p2 = gr.HTML(); o2 = gr.Textbox(label="Outline", lines=10)
        gr.Button("Generate - GH₵5").click(pres_fn, l2, [p2, o2])

    with gr.Tab("🎬 Video Ad - GH₵10"):
        l3 = gr.Textbox(label="Business"); p3 = gr.HTML(); o3 = gr.Textbox(label="Script", lines=10)
        gr.Button("Generate - GH₵10").click(video_fn, l3, [p3, o3])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port)
