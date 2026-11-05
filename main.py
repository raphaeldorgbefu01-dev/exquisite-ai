import os
import requests
import gradio as gr
from openai import OpenAI
from gtts import gTTS
import tempfile
import urllib.parse

groq_key = os.getenv("GROQ_API_KEY") or "dummy_key"
client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")

MODELS = ["llama-3.1-8b-instant", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
WHISPER_MODELS = ["whisper-large-v3-turbo", "whisper-large-v3"]

CSS = """
.chatbot table { display: block; overflow-x: auto; white-space: nowrap; width: 100%; border-collapse: collapse; }
.chatbot th, .chatbot td { padding: 8px 10px; text-align: left; border: 1px solid #ddd; white-space: normal !important; min-width: 90px; max-width: 180px; word-wrap: break-word; }
.chatbot th { background: #f0f0f0; font-weight: bold; }
.chatbot td { vertical-align: top; }
"""

# --- PWA HEAD - MAKES IT INSTALLABLE ---
PWA_HEAD = """
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#6a11cb">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Exquisite AI">
<link rel="apple-touch-icon" href="/icon-192.png">
<link rel="icon" type="image/png" href="/icon-192.png">
<script>
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(()=>{});
  });
}
</script>
"""

SYSTEM_PROMPT = """You are Exquisite AI, helpful like Meta AI and Gemini. Answer simply, clearly, friendly.
IMPORTANT FORMATTING RULES:
1. NEVER use LaTeX like \\[ \\] or \\text{} or $$.
2. Use plain readable text: CO2, H2O, C6H12O6, O2
3. When user asks for an equation, ALWAYS show it like this:
6CO2 + 6H2O --Light energy--> C6H12O6 + 6O2
In words: Carbon dioxide + Water + Light energy -> Glucose + Oxygen
- Reactants: 6 molecules of carbon dioxide (CO2) and 6 molecules of water (H2O).
- Products: 1 molecule of glucose (C6H12O6) and 6 molecules of oxygen (O2).
4. FOR TABLES: Use MAXIMUM 3 columns. Headers SHORT. Each cell SHORT - max 4-5 words. Never put long sentences in a table. If long, use bullet list.
5. For ALL answers: Use short headings, bold, bullet points, simple words.
"""

def ask_ai(prompt, history=[]):
    if groq_key == "dummy_key":
        return "Add GROQ_API_KEY in Render Environment"
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    for h in history[-6:]:
        if isinstance(h, dict) and "role" in h and "content" in h:
            content = h["content"]
            if isinstance(content, list):
                content = " ".join([str(c.get("text", "") if isinstance(c, dict) else c) for c in content])
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
    return f"Error: {last_err}"

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
        return f"Could
