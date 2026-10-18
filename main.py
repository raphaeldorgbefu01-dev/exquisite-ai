import json
import logging
import os
import uuid
import time
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__, static_folder="static")
logging.basicConfig(level=logging.INFO)

MODEL = "gemini-3.8-flash"
FREE_USES = 25
DATA_FILE = "exquisite_data.json"
UPLOAD_DIR = "uploads"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Shatta2025!")

PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE): 
        return {"users": {}, "payments": []}
    try:
        with open(DATA_FILE, "r") as f: 
            return json.load(f)
    except: 
        return {"users": {}, "payments": []}

def save_data(data):
    with open(DATA_FILE, "w") as f: 
        json.dump(data, f, indent=2)

def get_user_id():
    uid = request.cookies.get("exquisite_uid") or request.headers.get("X-User-Id") or request.form.get("uid")
    if not uid: 
        uid = str(uuid.uuid4())
    return uid

def get_user_record(data, uid):
    users = data.setdefault("users", {})
    if uid not in users: 
        users[uid] = {"free_used":0,"expiry":0,"plan":None,"created":int(time.time())}
    return users[uid]

def is_premium(user): 
    return user.get("expiry",0) > time.time()

def remaining_free(user):
    if is_premium(user): 
        return 9999
    return max(0, FREE_USES - user.get("free_used",0))

PLANS = {
    "day": {"label":"Day","price":10,"days":1,"tag":"24 hours","kobo":1000},
    "weekly": {"label":"Weekly","price":49,"days":7,"tag":"7 days - POPULAR","kobo":4900},
    "monthly": {"label":"Monthly","price":99,"days":30,"tag":"30 days - BEST VALUE","kobo":9900},
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>:root{color-scheme:dark;--bg:#101018;--panel:#191923;--line:rgba(255,255,255,.1);--text:#f5f2fa;--muted:#a4a1b2;--violet:#bda0ff;--mint:#a8f0d5;font-family:Inter,system-ui,sans-serif}*{box-sizing:border-box}body{min-height:100vh;margin:0;color:var(--text);background:var(--bg)}.shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0 72px}header{display:flex;justify-content:space-between;align-items:center}.brand{display:flex;align-items:center;gap:12px;font-weight:700}.brand-mark{display:grid;place-items:center;width:36px;height:36px;border-radius:12px;background:linear-gradient(140deg,var(--violet),var(--mint));color:#17121f;font-weight:900}.service-tag{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}.hero{max-width:730px;margin:72px auto 34px;text-align:center}.eyebrow{color:var(--mint);font-size:12px;font-weight:750;letter-spacing:.18em;text-transform:uppercase}h1{font-size:42px;margin:12px 0}.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin:16px 0}button{background:var(--violet);color:#111;border:0;border-radius:10px;padding:12px 18px;font-weight:700;cursor:pointer}input,textarea{width:100%;padding:12px;border-radius:10px;border:1px solid var(--line);background:#111;color:#fff}</style></head><body><div class="shell"><header><div class="brand"><div class="brand-mark">E</div> Exquisite AI</div><div class="service-tag" id="quota">Loading...</div></header><div class="hero"><div class="eyebrow">Premium AI Content Studio</div><h1>Create viral content in seconds</h1><p style="color:var(--muted)">25 free uses. Upgrade with Paystack.</p></div><div class="card"><textarea id="prompt" rows="4" placeholder="Ask anything..."></textarea><br><br><button onclick="generate()">Generate ✨</button><div id="result" style="margin-top:16px;white-space:pre-wrap"></div></div><div class="card"><h3>Upgrade</h3><div id="plans"></div></div></div>
<script>
let PUBLIC_KEY="{{PUBLIC_KEY}}";
async function refreshQuota(){
  let r=await fetch('/api/me'); let d=await r.json();
  document.getElementById('quota').innerText=d.is_premium ? 'Premium: '+d.plan : 'Free left: '+d.remaining;
  let p=document.getElementById('plans'); p.innerHTML='';
  Object.entries(d.plans).forEach(([k,v])=>{
    let b=document.createElement('button'); b.innerText=v.label+' - GHS '+v.price+' ('+v.tag+')'; b.style.margin='6px';
    b.onclick=()=>pay(k); p.appendChild(b);
  });
}
async function generate(){
  let pr=document.getElementById('prompt').value; if(!pr) return alert('Type something');
  document.getElementById('result').innerText='Generating...';
  let r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:pr})});
  let d=await r.json(); document.getElementById('result').innerText=d.answer||JSON.stringify(d);
  refreshQuota();
}
function pay(plan){
  if(!PUBLIC_KEY){ alert('Paystack not configured - set PAYSTACK_PUBLIC_KEY in Render env'); return; }
  fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan})}).then(r=>r.json()).then(d=>{
    if(d.error) return alert(d.error);
    var handler=PaystackPop.setup({key:PUBLIC_KEY,email:d.email||'user@exquisite.ai',amount:d.kobo,currency:'GHS',ref:d.reference,callback:function(resp){ fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(r=>r.json()).then(v=>{ alert(v.message||'Verified!'); refreshQuota(); }); },onClose:function(){ alert('Payment closed'); }});
    handler.openIframe();
  });
}
refreshQuota();
</script></body></html>
"""

@app.route("/")
def index():
    data = load_data()
    uid = get_user_id()
    user = get_user_record(data, uid)
    save_data(data)
    html = PAGE.replace("{{PUBLIC_KEY}}", PAYSTACK_PUBLIC_KEY)
    resp = make_response(html)
    resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365)
    return resp

@app.route("/api/me")
def me():
    data = load_data()
    uid = get_user_id()
    user = get_user_record(data, uid)
    return jsonify({"uid": uid,"remaining": remaining_free(user),"is_premium": is_premium(user),"plan": user.get("plan"),"expiry": user.get("expiry"),"plans": PLANS})

@app.route("/api/generate", methods=["POST"])
def generate():
    data = load_data()
    uid = get_user_id()
    user = get_user_record(data, uid)
    if not is_premium(user) and user.get("free_used",0) >= FREE_USES:
        return jsonify({"error":"Free limit reached"}), 403
    j = request.get_json() or {}
    prompt = j.get("prompt","")[:2000]
    user["free_used"] = user.get("free_used",0)+1
    save_data(data)
    return jsonify({"answer": f"[DEMO] You asked: {prompt}\n\nConnect Gemini API here."})

@app.route("/api/paystack/init", methods=["POST"])
def paystack_init():
    if not PAYSTACK_SECRET_KEY:
        return jsonify({"error":"Paystack secret not set"}), 500
    j = request.get_json() or {}
    plan_key = j.get("plan","day")
    plan = PLANS.get(plan_key)
    if not plan: return jsonify({"error":"Invalid plan"}), 400
    uid = get_user_id()
    email = f"{uid}@exquisite.ai"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type":"application/json"}
    payload = {"email": email, "amount": plan["kobo"]*100, "currency":"GHS", "metadata":{"uid":uid,"plan":plan_key}}
    try:
        r = http_requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers, timeout=15)
        jr = r.json()
        if not jr.get("status"): return jsonify({"error": jr.get("message")}), 400
        return jsonify({"reference": jr["data"]["reference"], "kobo": plan["kobo"]*100, "email": email})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/paystack/verify", methods=["POST"])
def paystack_verify():
    j = request.get_json() or {}
    ref = j.get("reference")
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    try:
        r = http_requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers=headers, timeout=15)
        jr = r.json()
        if not jr.get("status") or jr["data"]["status"] != "success": return jsonify({"error":"Not successful"}), 400
        meta = jr["data"].get("metadata",{})
        uid = meta.get("uid") or get_user_id()
        plan_key = meta.get("plan","day")
        plan = PLANS.get(plan_key, PLANS["day"])
        data = load_data()
        user = get_user_record(data, uid)
        user["plan"] = plan_key
        user["expiry"] = int(time.time()) + plan["days"]*24*3600
        data.setdefault("payments",[]).append({"uid":uid,"plan":plan_key,"ref":ref,"time":int(time.time())})
        save_data(data)
        return jsonify({"message": f"Premium activated! {plan['label']}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
