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
PWA_HEAD = '<script>'
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
