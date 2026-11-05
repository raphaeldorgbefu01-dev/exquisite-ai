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

CSS = ".chatbot{max-width:100%!important} .chatbot table{display:block;overflow-x:auto!important;width:100%;border-collapse:collapse} .chatbot th,.chatbot td{padding:10px;border:1px solid #ddd;white-space:nowrap!important;min-width:110px} .chatbot th{background:#f0f0f0} .gradio-container{background:white!important} .message, .chatbot, .block, .form, input, textarea{background:white!important;color:black!important} *{transition:background-color 1s ease!important}"

# --- COLOUR CYCLE EVERY 1 MINUTE - TEXT ALWAYS READABLE ---
PWA_HEAD = """
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#6a11cb">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="apple-touch-icon" href="/icon-192.png">
<link rel="icon" href="/icon-192.png">
<script>
if("serviceWorker" in navigator){window.addEventListener("load",()=>{navigator.serviceWorker.register("/sw.js").catch(()=>{})})}
// COLOUR CYCLE - 1 MINUTE = 60000 ms - ONLY BACKGROUND CHANGES
const COLORS = ["#ffffff","#1a0033","#1e3aff","#ff69b4","#00a651","#ffd700"];
let colorIndex = 0;
function applyColor(){
  const bg = COLORS[colorIndex];
  document.body.style.backgroundColor = bg;
  document.documentElement.style.backgroundColor = bg;
  const cards = document.querySelectorAll(".gradio-container, .message, .chatbot, .block, .form, input, textarea");
  cards.forEach(b => { b.style.backgroundColor = "white"; b.style.color = "black"; });
  const ths = document.querySelectorAll("th");
  ths.forEach(t => { t.style.backgroundColor = "#f0f0f0"; t.style.color = "black"; });
  colorIndex = (colorIndex + 1) % COLORS.length;
}
setInterval(applyColor, 60000);
window.addEventListener("load", () => { setTimeout(applyColor, 1000); });
</script>
"""

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
    url = "https://image.pollinations.ai/prompt/" + safe +
