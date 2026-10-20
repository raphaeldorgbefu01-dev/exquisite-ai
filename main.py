import json, os, uuid, time, urllib.parse, re
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
DATA_FILE = "data.json"
FREE = 25
PUB = os.environ.get("PAYSTACK_PUBLIC_KEY","")
SEC = os.environ.get("PAYSTACK_SECRET_KEY","")
POLL = os.environ.get("POLLINATIONS_TOKEN","")

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

def solve_math(prompt):
    try:
        p = prompt.lower()
        p = p.replace("solve","")
        p = p.replace(" ","")
        p = p.strip()
        # 3x=15
        pat1 = r"^(\d*\.?\d*)x=(\d*\.?\d*)$"
        m = re.match(pat1, p)
        if m:
            a_str = m.group(1)
            if a_str == "":
                a_str = "1"
            a = float(a_str)
            c = float(m.group(2))
            x = c / a
            out = "Solve: " + prompt + "\n"
            out += "x = " + str(x)
            return out
        # 5=5x
        pat2 = r"^(\d*\.?\d*)=(\d*\.?\d*)x$"
        m = re.match(pat2, p)
        if m:
            c = float(m.group(1))
            a_str = m.group(2)
            if a_str == "":
                a_str = "1"
            a = float(a_str)
            x = c / a
            out = "Solve: " + prompt + "\n"
            out += "x = " + str(x)
            return out
        # x=5
        pat3 = r"^x=(\d*\.?\d*)$"
        m = re.match(pat3, p)
        if m:
            return "Solve: " + prompt + "\n x = " + m.group(1)
        # 5=x
        pat4 = r"^(\d*\.?\d*)=x$"
        m = re.match(pat4, p)
        if m:
            return "Solve: " + prompt + "\n x = " + m.group(1)
        # calc
        pat5 = r"^[\d\+\-\*\/\.\(\)]+$"
        if re.match(pat5, p):
            res = eval(p)
            return p + " = " + str(res)
    except:
        pass
    return None

def local_answer(prompt, typ):
    low = prompt.lower()
    s = prompt[:80]
    if typ == "all":
        mm = solve_math(prompt)
        if mm:
            return mm
        if "best business" in low and "ghana" in low:
            a = "Best Business Ghana:\n"
            a += "1. Food 300-800/day\n"
            a += "2. MoMo 100-400/day\n"
            a += "3. Thrift 150%\n"
            a += "4. Phone 3x\n"
            a += "5. Beauty Wigs\n"
            a += "6. AI Agency 800-2000/client"
            return a
        return "Answer: " + s + "\nFor Ghana 2026."
    return "Ready for " + s

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
    h += ".badge{background:#222;padding:4px 10px;border-radius:20px;font-size:12px;color:#aaa}"
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
    h += "<div class=badge id=quota>Free: loading...</div>"
    h += "<textarea id=q rows=3 oninput=onInput() onfocus=onInput()>5=5x</textarea><br><br>"
    h += "<button id=flightBtn onclick=go()>Let It Take Flight</button>"
    h += "<div id=res>Your answer here...</div>"
    h += "</div>"
    h += "<div class=card><h3>Unlock Unlimited</h3><div id=plans></div></div>"
    h += "<script>"
    h += "let cur='all';let PUB='"+PUB+"';"
    h += "function setT(t){cur=t;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('t-'+t).classList.add('active');onInput()}"
    h += "function onInput(){let v=document.getElementById('q').value.trim();let btn=document.getElementById('flightBtn');if(v.length>0){btn.classList.remove('hidden')}else{btn.classList.add('hidden')}}"
    h += "async function refresh(){let r=await fetch('/api/me');let d=await r.json();let q=document.getElementById('quota');if(d.is_premium){q.innerText='Premium: '+d.plan;}else{q.innerText='Free: '+d.remaining+' left';}let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(([k,v])=>{let b=document.createElement('button');b.innerText=v.label;b.style='margin:4px';b.onclick=()=>pay(k);p.appendChild(b)})}"
    h += "async function go(){let p=document.getElementById('q').value.trim();if(!p)return;let r=document.getElementById('res');let btn=document.getElementById('flightBtn');r.innerText='Thinking...';btn.classList.add('hidden');let res=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p,type:cur})}).then(x=>x.json());r.innerText=res.answer;if(res.image_url){let i=document.createElement('img');i.src=res.image_url;i.style='max-width:100%';r.appendChild(i)}refresh()}"
    h += "async function pay(plan){let init=await fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan:plan})}).then(x=>x.json());let h=PaystackPop.setup({key:PUB,email:init.email,amount:init.kobo,currency:'GHS',ref:init.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(x=>x.json()).then(v=>{alert(v.message);refresh()})}});h.openIframe()}"
    h += "refresh();onInput();"
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
    data = load_data()
    uid = get_uid()
    user = get_user(data, uid)
    j = request.get_json() or {}
    prompt = (j.get("
