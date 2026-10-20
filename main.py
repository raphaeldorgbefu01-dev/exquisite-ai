import json, os, uuid, time, urllib.parse
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
DATA_FILE = "data.json"

def load_data():
    try:
        f = open(DATA_FILE,"r")
        d = json.load(f)
        f.close()
        return d
    except:
        return {"users":{}}

def save_data(d):
    try:
        f = open(DATA_FILE,"w")
        json.dump(d,f)
        f.close()
    except:
        pass

def get_uid():
    u = request.cookies.get("uid")
    if not u:
        u = request.headers.get("X-User-Id")
    if not u:
        u = str(uuid.uuid4())
    return u

def get_user(data, uid):
    users = data.setdefault("users",{})
    if uid not in users:
        users[uid] = {"used":0}
    return users[uid]

def ask_gemini(q, key):
    if not key:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/"
        url += "v1beta/models/gemini-1.5-flash-latest:generateContent"
        url += "?key=" + key
        payload = {"contents":[{"parts":[{"text":q}]}]}
        payload["generationConfig"] = {"maxOutputTokens":3000}
        r = http_requests.post(url, json=payload, timeout=20)
        j = r.json()
        if "candidates" in j and j["candidates"]:
            part = j["candidates"][0]["content"]["parts"][0]
            return part.get("text","")
    except:
        pass
    return None

def local_answer(prompt, typ):
    low = prompt.lower()
    s = prompt[:70]
    if typ == "all":
        if "best business" in low and "ghana" in low:
            a = "Best Business Ghana 2025-26:\n"
            a += "1. Food Delivery GHS 300-800/day\n"
            a += "2. MoMo Data GHS 100-400/day\n"
            a += "3. Thrift Kantamanto 150% profit\n"
            a += "4. Phone Accessories 3x markup\n"
            a += "5. Beauty Wigs monthly\n"
            a += "6. AI Agency GHS 800-2000 per client\n"
            a += "Pick: Combine 6+3 zero inventory!"
            return a
        if "what is ai" in low:
            return "AI is software that learns like human. Ex: TikTok, MoMo fraud, Maps, this app. 500M use AI weekly 2026."
        if "code" in low or "website" in low:
            return "Code for " + s + ":\n<html><h1>" + s[:20] + "</h1><p>Built with Exquisite AI</p></html>"
        if "=" in prompt or "solve" in low:
            return "Math for " + s + ": Ex 2x+5=15 => x=5. Send full equation."
        # GENERAL - ANSWERS ANYTHING
        a = "Answer: " + s + "\n\n"
        a += "Important in Ghana 2026.\n"
        a += "What: Topic for income/skills\n"
        a += "Why: Jobs, business, decisions\n"
        a += "How: Goal, 1 skill, act daily, use AI\n"
        a += "Ask: Explain " + s[:20] + " simply"
        return a
    if typ == "captions":
        return "Captions for " + s
    if typ == "scripts":
        return "Script for " + s
    if typ == "stories":
        return "Story for " + s
    return "Answer for " + s

def get_page():
    h = ""
    h += "<!doctype html><html><head>"
    h += "<meta charset=utf-8>"
    h += "<meta name=viewport content='width=device-width,initial-scale=1'>"
    h += "<title>Exquisite AI</title>"
    h += "<style>"
    h += "body{background:#0f0f18;color:#fff;padding:20px;font-family:sans-serif}"
    h += ".card{background:#191923;padding:16px;margin:16px 0;border-radius:16px}"
    h += "textarea{width:100%;padding:12px;background:#111;color:#fff;border-radius:12px}"
    h += "button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700}"
    h += ".tab{padding:8px 14px;border-radius:20px;background:#222;color:#aaa;border:1px solid #444;margin:2px}"
    h += ".tab.active{background:#bda0ff;color:#111}"
    h += "#res{white-space:pre-wrap;background:#111;padding:12px;border-radius:12px;margin-top:10px;min-height:60px}"
    h += "</style></head><body>"
    h += "<h2 style=text-align:center>Where Ideas Take Flight</h2>"
    h += "<div style=text-align:center>"
    h += "<button class=tab active id=t-all onclick=setT('all')>All</button>"
    h += "<button class=tab id=t-captions onclick=setT('captions')>Captions</button>"
    h += "<button class=tab id=t-scripts onclick=setT('scripts')>Scripts</button>"
    h += "<button class=tab id=t-stories onclick=setT('stories')>Stories</button>"
    h += "<button class=tab id=t-images onclick=setT('images')>Images</button>"
    h += "</div>"
    h += "<div class=card>"
    h += "<textarea id=q rows=3>Best business in Ghana</textarea><br><br>"
    h += "<button onclick=go()>Let It Take Flight</button>"
    h += "<div id=res>Your answer will appear here...</div>"
    h += "</div>"
    h += "<script>"
    h += "let cur='all';"
    h += "function setT(t){cur=t;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('t-'+t).classList.add('active')}"
    h += "async function go(){let p=document.getElementById('q').value;let r=document.getElementById('res');r.innerText='Thinking...';let d=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p,type:cur})}).then(x=>x.json());r.innerText=d.answer;if(d.image_url){let i=document.createElement('img');i.src=d.image_url;i.style='max-width:100%;margin-top:10px';r.appendChild(i)}}"
    h += "</script></body></html>"
    return h

@app.route("/")
def index():
    html = get_page()
    uid = get_uid()
    resp = make_response(html)
    resp.set_cookie("uid", uid, max_age=86400*365)
    return resp

@app.route("/api/generate", methods=["POST"])
def gen_api():
    data = load_data()
    uid = get_uid()
    user = get_user(data, uid)
    j = request.get_json() or {}
    prompt = (j.get("prompt") or "").strip()
    if not prompt:
        prompt = "Best business in Ghana"
    if len(prompt) > 2000:
        prompt = prompt[:2000]
    typ = j.get("type") or "all"
    key = os.environ.get("GEMINI_API_KEY") or ""
    if not key:
        key = os.environ.get("GOOGLE_API_KEY") or ""
    ans = ""
    img = None
    if typ == "images":
        safe = urllib.parse.quote(prompt[:400])
        seed = int(time.time()) % 999999
        img = "https://image.pollinations.ai/prompt/" + safe
        img += "?width=1024&height=1024&seed=" + str(seed)
        ans = "Image for: " + prompt[:60]
    else:
        if key:
            g = ask_gemini("Answer like Gemini: " + prompt, key)
            if g and len(g) > 10:
                ans = g
        if not ans:
            ans = local_answer(prompt, typ)
    user["used"] = user.get("used",0) + 1
    save_data(data)
    out = {"answer": ans}
    if img:
        out["image_url"] = img
    resp = make_response(jsonify(out))
    resp.set_cookie("uid", uid, max_age=86400*365)
    return resp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
