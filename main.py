import json, os, uuid, time, urllib.parse
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
DATA_FILE = "data.json"
FREE = 25
PUB = os.environ.get("PAYSTACK_PUBLIC_KEY","")
SEC = os.environ.get("PAYSTACK_SECRET_KEY","")

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
        users[uid] = {"used":0,"expiry":0,"plan":None}
    return users[uid]

def is_premium(u):
    return u.get("expiry",0) > time.time()

def remain(u):
    if is_premium(u):
        return 9999
    left = FREE - u.get("used",0)
    if left < 0:
        left = 0
    return left

def ask_gemini(q, key):
    if not key:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/"
        url += "v1beta/models/gemini-1.5-flash-latest:generateContent"
        url += "?key=" + key
        payload = {"contents":[{"parts":[{"text":q}]}]}
        r = http_requests.post(url, json=payload, timeout=20)
        j = r.json()
        if "candidates" in j and j["candidates"]:
            return j["candidates"][0]["content"]["parts"][0]["text"]
    except:
        pass
    return None

def local_answer(prompt, typ):
    low = prompt.lower()
    s = prompt[:70]
    if typ == "all":
        if "best business" in low and "ghana" in low:
            a = "Best Business Ghana:\n"
            a += "1. Food GHS 300-800/day\n"
            a += "2. MoMo GHS 100-400/day\n"
            a += "3. Thrift 150% profit\n"
            a += "4. Phone Accessories 3x\n"
            a += "5. Beauty Wigs\n"
            a += "6. AI Agency GHS 800-2000/client"
            return a
        if "what is ai" in low:
            return "AI learns like human. Ex: TikTok, MoMo, Maps."
        # GENERAL
        a = "Answer: " + s + "\n"
        a += "Important Ghana 2026.\n"
        a += "How: Goal, skill, act daily, use AI."
        return a
    return "For " + s + " - viral content ready."

PLANS = {
    "day":{"label":"Day GHS 10","kobo":1000,"days":1},
    "weekly":{"label":"Weekly GHS 49","kobo":4900,"days":7},
    "monthly":{"label":"Monthly GHS 99","kobo":9900,"days":30}
}

def get_page():
    h = ""
    h += "<!doctype html><html><head>"
    h += "<meta charset=utf-8>"
    h += "<meta name=viewport content='width=device-width,initial-scale=1'>"
    h += "<title>Exquisite AI</title>"
    h += "<script src=https://js.paystack.co/v1/inline.js></script>"
    h += "<style>"
    h += "body{background:#0f0f18;color:#fff;padding:20px;font-family:sans-serif}"
    h += ".card{background:#191923;padding:16px;margin:12px 0;border-radius:16px}"
    h += "textarea{width:100%;padding:12px;background:#111;color:#fff;border-radius:12px;border:1px solid #333}"
    h += "button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700;cursor:pointer}"
    h += "button.hidden{display:none!important}"
    h += ".tab{padding:8px 14px;border-radius:20px;background:#222;color:#aaa;border:1px solid #444;margin:2px}"
    h += ".tab.active{background:#bda0ff;color:#111}"
    h += "#res{white-space:pre-wrap;background:#111;padding:12px;border-radius:12px;margin-top:10px;min-height:60px}"
    h += ".badge{display:inline-block;background:#222;padding:4px 10px;border-radius:20px;font-size:12px;color:#aaa;margin-bottom:8px}"
    h += "</style></head><body>"
    h += "<h2 style=text-align:center>Where Ideas Take Flight</h2>"
    h += "<p style=text-align:center;color:#888;font-size:13px>Ask anything like Gemini</p>"
    h += "<div style=text-align:center>"
    h += "<button class=tab active id=t-all onclick=setT('all')>All</button>"
    h += "<button class=tab id=t-captions onclick=setT('captions')>Captions</button>"
    h += "<button class=tab id=t-scripts onclick=setT('scripts')>Scripts</button>"
    h += "<button class=tab id=t-stories onclick=setT('stories')>Stories</button>"
    h += "<button class=tab id=t-images onclick=setT('images')>Images</button>"
    h += "</div>"
    h += "<div class=card>"
    h += "<div class=badge id=quota>Loading...</div>"
    h += "<div id=mode>Mode: All - General AI</div>"
    h += "<textarea id=q rows=3 placeholder='Best business in Ghana?' oninput=onInput() onfocus=onInput()></textarea><br><br>"
    h += "<button id=flightBtn class=hidden onclick=go()>Let It Take Flight</button>"
    h += "<div id=res>Your answer will appear here...</div>"
    h += "</div>"
    h += "<div class=card id=payCard>"
    h += "<h3>Unlock Unlimited</h3>"
    h += "<p style=color:#888;font-size:13px>25 free uses, then upgrade</p>"
    h += "<div id=plans></div>"
    h += "</div>"
    h += "<script>"
    h += "let cur='all';let PUB='"+PUB+"';"
    h += "function setT(t){cur=t;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('t-'+t).classList.add('active');document.getElementById('mode').innerText='Mode: '+t;let v=document.getElementById('q').value.trim();if(v.length>2){document.getElementById('flightBtn').classList.remove('hidden')}}"
    h += "function onInput(){let v=document.getElementById('q').value.trim();let btn=document.getElementById('flightBtn');if(v.length>1){btn.classList.remove('hidden')}else{btn.classList.add('hidden')}}"
    h += "async function refresh(){try{let r=await fetch('/api/me');let d=await r.json();let q=document.getElementById('quota');if(d.is_premium){q.innerText='Premium: '+d.plan+' Unlimited';}else{q.innerText='Free: '+d.remaining+' left of 25';}let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(([k,v])=>{let b=document.createElement('button');b.innerText=v.label;b.style='margin:4px';b.onclick=()=>pay(k);p.appendChild(b)})}catch(e){}}"
    h += "async function go(){let p=document.getElementById('q').value.trim();if(!p){alert('Type question');return}let r=document.getElementById('res');let btn=document.getElementById('flightBtn');r.innerText='Exquisite AI thinking... ('+cur+')';btn.classList.add('hidden');try{let res=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p,type:cur})}).then(x=>x.json());if(res.need_pay){r.innerText=res.answer;document.getElementById('payCard').style.display='block';refresh();return}r.innerText=res.answer;if(res.image_url){let i=document.createElement('img');i.src=res.image_url;i.style='max-width:100%;margin-top:10px;border-radius:12px';r.appendChild(i)}}catch(e){r.innerText='Error: '+e}refresh()}"
    h += "async function pay(plan){if(!PUB){alert('Add Paystack public key in Render');return}let init=await fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan:plan})}).then(x=>x.json());if(init.error){alert(init.error);return}let h=PaystackPop.setup({key:PUB,email:init.email,amount:init.kobo,currency:'GHS',ref:init.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(x=>x.json()).then(v=>{alert(v.message||v.error);refresh()})},onClose:function(){}});h.openIframe()}"
    h += "refresh();"
    h += "</script></body></html>"
    return h

@app.route("/")
def index():
    html = get_page()
    uid = get_uid()
    resp = make_response(html)
    resp.set_cookie("uid", uid, max_age=86400*365)
    return resp

@app.route("/api/me")
def me():
    data = load_data()
    uid = get_uid()
    user = get_user(data, uid)
    return jsonify({"remaining": remain(user),"is_premium": is_premium(user),"plan": user.get("plan"),"plans": PLANS})

@app.route("/api/generate", methods=["POST"])
def gen_api():
   
