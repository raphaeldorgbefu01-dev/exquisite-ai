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
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Exq-8qx1Wn6x9SgU-Ghana2026!")
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

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI - Where Ideas Take Flight</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>:root{color-scheme:dark;--bg:#101018;--panel:#191923;--line:rgba(255,255,255,.1);--text:#f5f2fa;--muted:#a4a1b2;--violet:#bda0ff;--mint:#a8f0d5;font-family:Inter,system-ui,sans-serif}*{box-sizing:border-box}body{min-height:100vh;margin:0;color:var(--text);background:radial-gradient(900px 500px at 15% -10%, rgba(189,160,255,.22), transparent), radial-gradient(700px 400px at 85% 5%, rgba(168,240,213,.14), transparent), var(--bg)}.shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0 72px}header{display:flex;justify-content:space-between;align-items:center}.brand{display:flex;align-items:center;gap:12px;font-weight:800}.brand-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:linear-gradient(140deg,var(--violet),var(--mint));color:#17121f;font-weight:900}.service-tag{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}.hero{max-width:820px;margin:82px auto 32px;text-align:center}.eyebrow{color:var(--mint);font-size:11px;font-weight:800;letter-spacing:.24em;text-transform:uppercase}h1{font-size:52px;line-height:1.02;margin:18px 0;letter-spacing:-.03em;background:linear-gradient(180deg,#fff 20%,#b8b0d0 90%);-webkit-background-clip:text;background-clip:text;color:transparent}.hero p{color:var(--muted);font-size:17px;line-height:1.7;max-width:640px;margin:0 auto}.search-tabs{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:22px 0 0}.tab{border:1px solid var(--line);background:#181825;color:var(--muted);padding:8px 14px;border-radius:999px;font-size:13px;font-weight:600;cursor:pointer;transition:.2s}.tab.active,.tab:hover{background:var(--violet);color:#111;border-color:var(--violet)}.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:22px;margin:20px 0;box-shadow:0 12px 40px rgba(0,0,0,.35)}button.primary{background:var(--violet);color:#111;border:0;border-radius:12px;padding:13px 22px;font-weight:800;cursor:pointer;transition:.2s}button.primary:hover{transform:translateY(-1px);filter:brightness(1.08)}input,textarea{width:100%;padding:14px;border-radius:12px;border:1px solid var(--line);background:#111117;color:#fff;font-family:inherit;font-size:15px}textarea:focus{outline:none;border-color:var(--violet);box-shadow:0 0 0 3px rgba(189,160,255,.15)}#result{line-height:1.8;font-size:15px;white-space:pre-wrap}</style></head><body><div class="shell"><header><div class="brand"><div class="brand-mark">E</div> Exquisite AI</div><div class="service-tag" id="quota">Loading...</div></header><div class="hero"><div class="eyebrow">Where Ideas Transform Into Dreams</div><h1>Where Ideas Take Flight</h1><p>Search viral captions, scripts & stories in seconds. Transform a whisper of an idea into a dream the world can't ignore.</p><div class="search-tabs"><button class="tab active" id="tab-all" onclick="setType('all')">🔍 All</button><button class="tab" id="tab-captions" onclick="setType('captions')">📸 Viral Captions</button><button class="tab" id="tab-scripts" onclick="setType('scripts')">🎬 Scripts</button><button class="tab" id="tab-stories" onclick="setType('stories')">📖 Stories</button></div></div><div class="card"><textarea id="prompt" rows="4" placeholder="Search... e.g. 'A luxury Ghanaian brand that turns fashion into dream'"></textarea><br><br><button class="primary" onclick="generate()">✨ Let It Take Flight</button><div id="result" style="margin-top:20px"></div></div><div class="card"><h3 style="margin-top:0">Unlock Unlimited Flight</h3><p style="color:var(--muted);font-size:13px">Go premium and search unlimited ideas</p><div id="plans" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:14px"></div></div></div>
<script>
let PUBLIC_KEY="{{PUBLIC_KEY}}";
let currentType = "all";
function setType(t){
  currentType = t;
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+t).classList.add('active');
  let ph = {all: "Search... e.g. 'A luxury Ghanaian brand that turns fashion into dream'", captions: "Search viral captions... e.g. 'Ghana fashion week caption'", scripts: "Search scripts... e.g. '30s TikTok ad for luxury dress'", stories: "Search stories... e.g. 'Brand story for fashion dream'"};
  document.getElementById('prompt').placeholder = ph[t] || ph.all;
}
async function refreshQuota(){
  let r=await fetch('/api/me'); let d=await r.json();
  document.getElementById('quota').innerText=d.is_premium ? '✨ Premium: '+d.plan : 'Free: '+d.remaining+' left';
  let p=document.getElementById('plans'); p.innerHTML='';
  Object.entries(d.plans).forEach(([k,v])=>{
    let b=document.createElement('button'); b.className='primary'; b.innerText=v.label+' - GHS '+v.price+' ('+v.tag+')'; b.style.margin='4px';
    b.onclick=()=>pay(k); p.appendChild(b);
  });
}
async function generate(){
  let pr=document.getElementById('prompt').value; if(!pr) return alert('Type what you want to search');
  let resEl=document.getElementById('result');
  resEl.innerText='🔍 Searching '+currentType+'... Your idea is taking flight...';
  let r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:pr, type:currentType})});
  let d=await r.json(); resEl.innerText=d.answer||d.error||JSON.stringify(d);
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
    search_type = j.get("type","all")
    if not prompt:
        return jsonify({"error":"Empty prompt"}), 400

    gemini_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    answer = ""

    type_instruction = {
        "all": "You are Exquisite AI - Where Ideas Take Flight. Create viral content.",
        "captions": "You are a VIRAL CAPTIONS expert. Create 5-7 short, catchy, Instagram/TikTok viral captions with hashtags and emojis.",
        "scripts": "You are a VIRAL SCRIPT expert. Write a 30-60 second video script with hook, body, CTA. Make it viral, punchy, Ghanaian flavor if relevant.",
        "stories": "You are a BRAND STORY expert. Write an inspirational, dream-like brand story that feels luxurious and emotional."
    }
    instruction = type_instruction.get(search_type, type_instruction["all"])

    if not gemini_key:
        answer = "⚠️ GEMINI_API_KEY is NOT set in Render. Go to Render → Environment → Add GEMINI_API_KEY → Save → Redeploy"
    else:
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
        last_error = ""
        for model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                full_prompt = f"{instruction}\nUser search: {prompt}\n\nMake it searchable, viral, inspirational, with Where Ideas Take Flight vibe."
                payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
                r = http_requests.post(url, json=payload, timeout=30)
                jr = r.json()
                if "candidates" in jr and len(jr["candidates"]) > 0 and "content" in jr["candidates"][0]:
                    ans = jr["candidates"][0]["content"]["parts"][0]["text"]
                    if ans and ans.strip():
                        answer = ans
                        break
                last_error = str(jr)
                if "NOT_FOUND" in last_error or "not found" in last_error.lower():
                    continue
                else:
                    if "candidates" not in jr:
                        answer = f"Gemini Error ({model}): {jr}"
                        break
            except Exception as e:
                last_error = str(e)
                logging.error(f"Gemini {model} exception: {e}")
                continue
        if not answer:
            answer = f"❌ Gemini failed. Last error: {last_error}. Check API key at https://aistudio.google.com/apikey"

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
    if pwd != ADMIN_PASSWORD: return "<body style=\"background:#101018;color:#fff;font-family:sans-serif;display:grid;place-items:center;height:100vh\"><form><h2>Admin Login</h2><input type=\"password\" name=\"password\" placeholder=\"Enter admin password\" style=\"padding:12px;border-radius:8px;width:260px;background:#222;color:#fff;border:1px solid #444\"><button style=\"padding:12px;background:#bda0ff;border:0;border-radius:8px;font-weight:700;margin-left:6px\">Login</button></form></body>", 401
    d = load_data()
    users_html = "".join([f"<tr><td style='font-size:11px'>{uid[:8]}...</td><td>{u.get('free_used',0)}/{FREE_USES}</td><td>{'YES' if u.get('expiry',0) > time.time() else 'NO'}</td><td>{u.get('plan','-')}</td></tr>" for uid,u in list(d.get("users",{}).items())[-50:][::-1]])
    return f"<html><body style='background:#101018;color:#fff;padding:20px'><h1>Admin - Where Ideas Take Flight</h1><p>Users: {len(d.get('users',{}))}</p><table border=1 style='border-collapse:collapse'><tr><th>UID</th><th>Used</th><th>Premium</th><th>Plan</th></tr>{users_html}</table><br><a href='/' style='color:#bda0ff'>Home</a></body></html>"

@app.route("/admin/reset")
def admin_reset():
    if request.args.get("password") != ADMIN_PASSWORD: return "Unauthorized", 401
    uid = request.args.get("uid"); data = load_data()
    if uid in data.get("users",{}): data["users"][uid]["free_used"]=0; save_data(data)
    return redirect(f"/admin?password={ADMIN_PASSWORD}")

@app.route("/admin/give")
def admin_give():
    if request.args.get("password") != ADMIN_PASSWORD: return "Unauthorized", 401
    uid = request.args.get("uid"); days = int(request.args.get("days","7")); data = load_data()
    if uid in data.get("users",{}): data["users"][uid]["expiry"]=int(time.time())+days*24*3600; data["users"][uid]["plan"]=f"admin_{days}d"; save_data(data)
    return redirect(f"/admin?password={ADMIN_PASSWORD}")

@app.route("/admin/clear")
def admin_clear():
    if request.args.get("password") != ADMIN_PASSWORD: return "Unauthorized", 401
    save_data({"users":{}, "payments":[]})
    return redirect(f"/admin?password={ADMIN_PASSWORD}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
