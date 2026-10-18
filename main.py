import json
import logging
import os
import uuid
import time
from flask import Flask, jsonify, request, make_response, redirect
import requests as http_requests

app = Flask(__name__, static_folder="static")
logging.basicConfig(level=logging.INFO)

FREE_USES = 25
DATA_FILE = "exquisite_data.json"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "CHANGE_ME_SET_IN_RENDER")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE): return {"users": {}, "payments": []}
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {"users": {}, "payments": []}
def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)
def get_user_id():
    uid = request.cookies.get("exquisite_uid") or request.headers.get("X-User-Id") or request.form.get("uid")
    if not uid: uid = str(uuid.uuid4())
    return uid
def get_user_record(data, uid):
    users = data.setdefault("users", {})
    if uid not in users: users[uid] = {"free_used":0,"expiry":0,"plan":None,"created":int(time.time())}
    return users[uid]
def is_premium(user): return user.get("expiry",0) > time.time()
def remaining_free(user):
    if is_premium(user): return 9999
    return max(0, FREE_USES - user.get("free_used",0))

PLANS = {
    "day": {"label":"Day","price":10,"days":1,"tag":"24 hours","kobo":1000},
    "weekly": {"label":"Weekly","price":49,"days":7,"tag":"7 days - POPULAR","kobo":4900},
    "monthly": {"label":"Monthly","price":99,"days":30,"tag":"30 days - BEST VALUE","kobo":9900},
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>:root{color-scheme:dark;--bg:#101018;--panel:#191923;--line:rgba(255,255,255,.1);--text:#f5f2fa;--muted:#a4a1b2;--violet:#bda0ff;--mint:#a8f0d5;font-family:Inter,system-ui,sans-serif}*{box-sizing:border-box}body{min-height:100vh;margin:0;color:var(--text);background:var(--bg)}.shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0 72px}header{display:flex;justify-content:space-between;align-items:center}.brand{display:flex;align-items:center;gap:12px;font-weight:700}.brand-mark{display:grid;place-items:center;width:36px;height:36px;border-radius:12px;background:linear-gradient(140deg,var(--violet),var(--mint));color:#17121f;font-weight:900}.service-tag{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}.hero{max-width:730px;margin:72px auto 34px;text-align:center}.eyebrow{color:var(--mint);font-size:12px;font-weight:750;letter-spacing:.18em;text-transform:uppercase}h1{font-size:42px;margin:12px 0}.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin:16px 0}button{background:var(--violet);color:#111;border:0;border-radius:10px;padding:12px 18px;font-weight:700;cursor:pointer}input,textarea{width:100%;padding:12px;border-radius:10px;border:1px solid var(--line);background:#111;color:#fff}</style></head><body><div class="shell"><header><div class="brand"><div class="brand-mark">E</div> Exquisite AI</div><div class="service-tag" id="quota">Loading...</div></header><div class="hero"><div class="eyebrow">Premium AI Content Studio</div><h1>Create viral content in seconds</h1><p style="color:var(--muted)">25 free uses. Upgrade with Paystack.</p></div><div class="card"><textarea id="prompt" rows="4" placeholder="Ask anything..."></textarea><br><br><button onclick="generate()">Generate</button><div id="result" style="margin-top:16px;white-space:pre-wrap"></div></div><div class="card"><h3>Upgrade</h3><div id="plans"></div></div></div>
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
  if(!PUBLIC_KEY){ alert('Paystack not configured'); return; }
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
        return jsonify({"error":"Free limit reached - please upgrade to continue"}), 403
    
    j = request.get_json() or {}
    prompt = j.get("prompt","")[:2000]
    if not prompt:
        return jsonify({"error":"Empty prompt"}), 400
    
    # GEMINI AI
    gemini_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    answer = ""
    if gemini_key:
        try:
            # Using Gemini 1.5 Flash - fast and cheap
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            r = http_requests.post(url, json=payload, timeout=30)
            jr = r.json()
            # Parse Gemini response
            if "candidates" in jr and len(jr["candidates"]) > 0:
                answer = jr["candidates"][0]["content"]["parts"][0]["text"]
            else:
                answer = f"Gemini Error: {jr}"
        except Exception as e:
            answer = f"AI Error: {str(e)}"
            logging.error(f"Gemini error: {e}")
    else:
        answer = f"[Set GEMINI_API_KEY in Render] You asked: {prompt}"

    user["free_used"] = user.get("free_used",0)+1
    save_data(data)
    resp = make_response(jsonify({"answer": answer}))
    resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365)
    return resp

@app.route("/api/paystack/init", methods=["POST"])
def paystack_init():
    if not PAYSTACK_SECRET_KEY: return jsonify({"error":"Paystack secret not set"}), 500
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
    except Exception as e: return jsonify({"error": str(e)}), 500

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
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/admin")
def admin():
    pwd = request.args.get("password") or request.args.get("p")
    if pwd != ADMIN_PASSWORD:
        return "<body style=\"background:#101018;color:#fff;font-family:sans-serif;display:grid;place-items:center;height:100vh\"><form><h2>Admin Login</h2><input type=\"password\" name=\"password\" placeholder=\"Enter admin password\" style=\"padding:12px;border-radius:8px;width:260px;background:#222;color:#fff;border:1px solid #444\"><button style=\"padding:12px;background:#bda0ff;border:0;border-radius:8px;font-weight:700;margin-left:6px\">Login</button></form></body>", 401
    d = load_data()
    users_html = ""
    for uid, u in list(d.get("users",{}).items())[-100:][::-1]:
        is_p = "YES" if u.get("expiry",0) > time.time() else "NO"
        users_html += f"<tr><td style='font-size:11px'>{uid[:8]}...</td><td>{u.get('free_used',0)}/{FREE_USES}</td><td>{is_p}</td><td>{u.get('plan','-')}</td><td>{time.strftime('%Y-%m-%d %H:%M', time.localtime(u.get('created',0)))}</td><td><a href='/admin/reset?uid={uid}&password={pwd}'>Reset</a> | <a href='/admin/give?uid={uid}&days=7&password={pwd}'>+7d</a> | <a href='/admin/give?uid={uid}&days=30&password={pwd}'>+30d</a></td></tr>"
    pays_html = ""
    for p in list(d.get("payments",[]))[-100:][::-1]:
        pays_html += f"<tr><td>{p.get('uid','')[:8]}</td><td>{p.get('plan')}</td><td>{p.get('ref')}</td><td>{time.strftime('%Y-%m-%d %H:%M', time.localtime(p.get('time',0)))}</td></tr>"
    return f"<html><head><title>Admin - Exquisite</title><style>body{{background:#101018;color:#f5f2fa;font-family:Inter,sans-serif;padding:20px}}table{{width:100%;border-collapse:collapse;margin:12px 0}}th,td{{border:1px solid rgba(255,255,255,.1);padding:8px;text-align:left}}th{{background:#191923}}a{{color:#bda0ff}}.card{{background:#191923;border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:16px;margin:16px 0}}</style></head><body><h1>Exquisite Admin</h1><p>Total users: {len(d.get('users',{}))} | Total payments: {len(d.get('payments',[]))}</p><div class='card'><h3>Users (last 100)</h3><table><tr><th>UID</th><th>Used</th><th>Premium</th><th>Plan</th><th>Created</th><th>Actions</th></tr>{users_html}</table></div><div class='card'><h3>Payments (last 100)</h3><table><tr><th>UID</th><th>Plan</th><th>Ref</th><th>Time</th></tr>{pays_html}</table></div><div class='card'><a href='/admin/clear?password={pwd}' onclick=\"return confirm('Delete ALL data?')\">Clear all data</a> | <a href='/'>Home</a></div></body></html>"

@app.route("/admin/reset")
def admin_reset():
    if request.args.get("password") != ADMIN_PASSWORD: return "Unauthorized", 401
    uid = request.args.get("uid")
    data = load_data()
    if uid in data.get("users",{}):
        data["users"][uid]["free_used"]=0
        save_data(data)
    return redirect(f"/admin?password={ADMIN_PASSWORD}")

@app.route("/admin/give")
def admin_give():
    if request.args.get("password") != ADMIN_PASSWORD: return "Unauthorized", 401
    uid = request.args.get("uid")
    days = int(request.args.get("days","7"))
    data = load_data()
    if uid in data.get("users",{}):
        data["users"][uid]["expiry"]=int(time.time())+days*24*3600
        data["users"][uid]["plan"]=f"admin_{days}d"
        save_data(data)
    return redirect(f"/admin?password={ADMIN_PASSWORD}")

@app.route("/admin/clear")
def admin_clear():
    if request.args.get("password") != ADMIN_PASSWORD: return "Unauthorized", 401
    save_data({"users":{}, "payments":[]})
    return redirect(f"/admin?password={ADMIN_PASSWORD}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
