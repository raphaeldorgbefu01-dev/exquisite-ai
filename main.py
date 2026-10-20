import json, os, uuid, time, urllib.parse, re
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
    except Exception as e:
        print("Gemini err", e)
    return None

def solve_math(prompt):
    try:
        p = prompt.lower().replace("solve","").strip()
        p = p.replace(" ","")
        # 3x=15
        m = re.match(r"^(\d*\.?\d*)x=(\d*\.?\d*)$", p)
        if m:
            a = float(m.group(1) or "1")
            c = float(m.group(2))
            x = c / a
            return "Solve: " + prompt + "\n\n" + str(a) + "x = " + str(c) + "\n" + "x = " + str(c) + "/" + str(a) + "\n" + "x = " + str(x)
        # 3x+5=20 or 2x-3=7
        m = re.match(r"^(\d*\.?\d*)x([\+\-])(\d*\.?\d*)=(\d*\.?\d*)$", p)
        if m:
            a = float(m.group(1) or "1")
            op = m.group(2)
            b = float(m.group(3))
            c = float(m.group(4))
            if op == "+":
                x = (c - b) / a
                steps = str(a)+"x = "+str(c)+"-"+str(b)+"\n"+str(a)+"x = "+str(c-b)+"\n"
            else:
                x = (c + b) / a
                steps = str(a)+"x = "+str(c)+"+"+str(b)+"\n"+str(a)+"x = "+str(c+b)+"\n"
            steps += "x = " + str(x)
            return "Solve: " + prompt + "\n\n" + steps
        # percentage
        if "%" in p and "of" in p:
            m = re.search(r"(\d+)%.*?of.*?(\d+)", p)
            if m:
                per = float(m.group(1))
                val = float(m.group(2))
                res = per/100*val
                return str(per)+"% of "+str(val)+" = "+str(res)
        # simple calc
        if re.match(r"^[\d\+\-\*\/\.\(\)]+$", p):
            res = eval(p)
            return p + " = " + str(res)
    except:
        pass
    return None

def local_answer(prompt, typ):
    low = prompt.lower()
    s = prompt[:100]
    if typ == "all":
        # REAL MATH
        if "solve" in low or "=" in prompt or "calculate" in low:
            m = solve_math(prompt)
            if m:
                return m + "\n\nWant steps? Ask: Solve 2x+5=15 with steps"
        if "best business" in low and "ghana" in low:
            a = "Best Business Ghana 2025-26:\n"
            a += "1. Food Delivery GHS 300-800/day\n"
            a += "2. MoMo Data GHS 100-400/day\n"
            a += "3. Thrift Kantamanto 150% profit\n"
            a += "4. Phone Accessories 3x\n"
            a += "5. Beauty Wigs\n"
            a += "6. AI Agency GHS 800-2000/client"
            return a
        if "what is ai" in low:
            return "AI is software that learns. Ex: TikTok, MoMo fraud detection, Maps, Exquisite AI."
        # DEFAULT - real answer
        return "Answer for: " + s + "\n\nThis is explained step by step. For " + s + ", focus on goal, skill, daily action. Ask more specifically."
    if typ == "captions":
        return "Viral Captions for " + s + ":\n1. Ghana to world\n2. Kente magic\n3. Slow mo elegance"
    if typ == "scripts":
        return "Script for " + s + ": Hook 0-3s, Body 60fps, CTA Follow"
    if typ == "stories":
        return "Brand story for " + s + " - Heritage Accra"
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
    h += "<div class=badge id=quota>Free: loading...</div>"
    h += "<div id=mode>Mode: All - General AI</div>"
    h += "<textarea id=q rows=3 placeholder='Solve 3x=15' oninput=onInput() onfocus=onInput()>Solve 3x=15</textarea><br><br>"
    h += "<button id=flightBtn onclick=go()>Let It Take Flight</button>"
    h += "<div id=res>Your answer will appear here...</div>"
    h += "</div>"
    h += "<div class=card id=payCard>"
    h += "<h3>Unlock Unlimited</h3>"
    h += "<p style=color:#888;font-size:13px>25 free uses, then upgrade</p>"
    h += "<div id=plans></div>"
    h += "</div>"
    h += "<script>"
    h += "let cur='all';let PUB='"+PUB+"';"
    h += "function setT(t){cur=t;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('t-'+t).classList.add('active');document.getElementById('mode').innerText='Mode: '+t;onInput()}"
    h += "function onInput(){let v=document.getElementById('q').value.trim();let btn=document.getElementById('flightBtn');if(v.length>1){btn.classList.remove('hidden')}else{btn.classList.add('hidden')}}"
    h += "async function refresh(){try{let r=await fetch('/api/me');let d=await r.json();let q=document.getElementById('quota');if(d.is_premium){q.innerText='Premium: '+d.plan+' Unlimited';}else{q.innerText='Free: '+d.remaining+' left of 25';}let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(([k,v])=>{let b=document.createElement('button');b.innerText=v.label;b.style='margin:4px';b.onclick=()=>pay(k);p.appendChild(b)})}catch(e){}}"
    h += "async function go(){let p=document.getElementById('q').value.trim();if(!p){alert('Type question');return}let r=document.getElementById('res');let btn=document.getElementById('flightBtn');r.innerText='Thinking...';btn.classList.add('hidden');try{let res=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p,type:cur})}).then(x=>x.json());if(res.need_pay){r.innerText=res.answer;refresh();return}r.innerText=res.answer;if(res.image_url){let i=document.createElement('img');i.src=res.image_url;i.style='max-width:100%;margin-top:10px';r.appendChild(i)}}catch(e){r.innerText='Error '+e}refresh()}"
    h += "async function pay(plan){if(!PUB){alert('Add Paystack public key');return}let init=await fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan:plan})}).then(x=>x.json());if(init.error){alert(init.error);return}let h=PaystackPop.setup({key:PUB,email:init.email,amount:init.kobo,currency:'GHS',ref:init.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(x=>x.json()).then(v=>{alert(v.message||v.error);refresh()})},onClose:function(){}});h.openIframe()}"
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
    prompt = (j.get("prompt") or "").strip()
    if not prompt:
        prompt = "Best business in Ghana"
    if len(prompt) > 2000:
        prompt = prompt[:2000]
    typ = j.get("type") or "all"
    key = os.environ.get("GEMINI_API_KEY") or ""
    if not key:
        key = os.environ.get("GOOGLE_API_KEY") or ""
    if not is_premium(user) and user.get("used",0) >= FREE:
        msg = "Free limit reached (25/25). Upgrade to unlimited."
        return jsonify({"answer": msg, "need_pay": True})
    ans = ""
    img = None
    if typ == "images":
        safe = urllib.parse.quote(prompt[:400])
        seed = int(time.time()) % 999999
        img = "https://image.pollinations.ai/prompt/" + safe
        img += "?width=1024&height=1024&seed=" + str(seed)
        ans = "4K Image for " + prompt[:60]
    else:
        if key:
            g = ask_gemini("Answer like Gemini, show steps: " + prompt, key)
            if g and len(g) > 10:
                ans = g
        if not ans:
            m = solve_math(prompt)
            if m:
                ans = m
            else:
                ans = local_answer(prompt, typ)
    user["used"] = user.get("used",0) + 1
    save_data(data)
    out = {"answer": ans}
    if img:
        out["image_url"] = img
    resp = make_response(jsonify(out))
    resp.set_cookie("uid", uid, max_age=86400*365)
    return resp

@app.route("/api/paystack/init", methods=["POST"])
def pay_init():
    if not SEC:
        return jsonify({"error":"Secret not set"}), 500
    j = request.get_json() or {}
    pk = j.get("plan") or "day"
    plan = PLANS.get(pk) or PLANS["day"]
    uid = get_uid()
    email = uid + "@exquisite.ai"
    headers = {"Authorization": "Bearer " + SEC}
    headers["Content-Type"] = "application/json"
    payload = {"email": email}
    payload["amount"] = plan["kobo"] * 100
    payload["currency"] = "GHS"
    payload["metadata"] = {"uid": uid, "plan": pk}
    r = http_requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers, timeout=15)
    jr = r.json()
    if not jr.get("status"):
        return jsonify({"error": jr.get("message")}), 400
    return jsonify({"reference": jr["data"]["reference"],"kobo": plan["kobo"]*100,"email": email})

@app.route("/api/paystack/verify", methods=["POST"])
def pay_verify():
    if not SEC:
        return jsonify({"error":"Secret not set"}), 500
    j = request.get_json() or {}
    ref = j.get("reference")
    if not ref:
        return jsonify({"error":"No ref"}), 400
    headers = {"Authorization": "Bearer " + SEC}
    r = http_requests.get("https://api.paystack.co/transaction/verify/" + ref, headers=headers, timeout=15)
    jr = r.json()
    if not jr.get("status"):
        return jsonify({"error":"Verify failed"}), 400
    if jr["data"]["status"] != "success":
        return jsonify({"error":"Payment not success"}), 400
    meta = jr["data"].get("metadata",{})
    uid = meta.get("uid") or get_uid()
    pk = meta.get("plan") or "day"
    data = load_data()
    user = get_user(data, uid)
    plan = PLANS.get(pk) or PLANS["day"]
    user["plan"] = pk
    user["expiry"] = int(time.time()) + plan["days"]*24*3600
    save_data(data)
    return jsonify({"message": "Premium Activated! " + plan["label"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
