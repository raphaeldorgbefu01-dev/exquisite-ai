import json, os, uuid, time, urllib.parse
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
FREE_USES = 25
DATA_FILE = "exquisite_data.json"
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")

def load_data():
    if not os.path.exists(DATA_FILE): return {"users": {}, "payments": []}
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {"users": {}, "payments": []}
def save_data(d):
    with open(DATA_FILE, "w") as f: json.dump(d, f, indent=2)
def get_user_id():
    uid = request.cookies.get("exquisite_uid") or request.headers.get("X-User-Id")
    if not uid: uid = str(uuid.uuid4())
    return uid
def get_user_record(data, uid):
    users = data.setdefault("users", {})
    if uid not in users: users[uid] = {"free_used":0,"expiry":0,"plan":None}
    return users[uid]
def is_premium(u): return u.get("expiry",0) > time.time()
def remaining_free(u): return 9999 if is_premium(u) else max(0, FREE_USES - u.get("free_used",0))

def ask_gemini(prompt_text, api_key):
    """Try every possible model + both v1 and v1beta until one works"""
    models = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-latest",
        "gemini-flash-latest",
        "gemini-1.0-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-3-flash-preview"
    ]
    versions = ["v1","v1beta"]
    for ver in versions:
        for model in models:
            try:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={api_key}"
                payload = {"contents":[{"parts":[{"text": prompt_text}]}],"generationConfig":{"temperature":0.7,"maxOutputTokens":1500}}
                r = http_requests.post(url, json=payload, timeout=20)
                jr = r.json()
                if "candidates" in jr and jr["candidates"]:
                    text = jr["candidates"][0]["content"]["parts"][0]["text"]
                    if text.strip():
                        print(f"Success with {ver}/{model}")
                        return text
            except Exception as e:
                continue
    return None

PLANS = {
    "day": {"label":"Day","price":10,"days":1,"kobo":1000},
    "weekly": {"label":"Weekly","price":49,"days":7,"kobo":4900},
    "monthly": {"label":"Monthly","price":99,"days":30,"kobo":9900},
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>:root{color-scheme:dark;--bg:#101018;--panel:#191923;--line:rgba(255,255,255,.12);--text:#f5f2fa;--muted:#a4a1b2;--violet:#bda0ff;--mint:#a8f0d5;font-family:Inter,sans-serif}*{box-sizing:border-box}body{margin:0;color:var(--text);background:var(--bg)}.shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0 72px}header{display:flex;justify-content:space-between;align-items:center}.brand{display:flex;align-items:center;gap:12px;font-weight:800}.brand-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:linear-gradient(140deg,var(--violet),var(--mint));color:#17121f;font-weight:900}.service-tag{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}.hero{max-width:860px;margin:82px auto 32px;text-align:center}.eyebrow{color:var(--mint);font-size:11px;font-weight:800;letter-spacing:.24em;text-transform:uppercase}h1{font-size:52px;line-height:1.02;margin:18px 0;background:linear-gradient(180deg,#fff 20%,#b8b0d0 90%);-webkit-background-clip:text;background-clip:text;color:transparent}.search-tabs{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:22px 0 0}.tab{border:1px solid var(--line);background:#181825;color:var(--muted);padding:9px 15px;border-radius:999px;font-size:13px;font-weight:600;cursor:pointer}.tab.active,.tab:hover{background:var(--violet);color:#111}.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:22px;margin:20px 0}button.primary{background:var(--violet);color:#111;border:0;border-radius:12px;padding:13px 22px;font-weight:800;cursor:pointer}button.primary.hidden{display:none!important}textarea{width:100%;padding:14px;border-radius:12px;border:1px solid var(--line);background:#111117;color:#fff;font-size:15px}#result{line-height:1.9;font-size:15px;white-space:pre-wrap;background:#111117;border-radius:12px;padding:16px;min-height:60px;position:relative}#result img{max-width:100%;border-radius:12px;margin-top:12px}.copy-btn{position:absolute;top:8px;right:8px;background:#222;border:1px solid var(--line);color:var(--muted);border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}</style></head><body><div class="shell"><header><div class="brand"><div class="brand-mark">E</div> Exquisite AI</div><div class="service-tag" id="quota">Loading...</div></header><div class="hero"><div class="eyebrow">Where Ideas Transform Into Dreams</div><h1>Where Ideas Take Flight</h1><div class="search-tabs"><button class="tab active" id="tab-all" onclick="setType('all')">🔍 All</button><button class="tab" id="tab-captions" onclick="setType('captions')">📸 Captions</button><button class="tab" id="tab-scripts" onclick="setType('scripts')">🎬 Scripts</button><button class="tab" id="tab-stories" onclick="setType('stories')">📖 Stories</button><button class="tab" id="tab-images" onclick="setType('images')">🖼️ Images</button><button class="tab" id="tab-videos" onclick="setType('videos')">🎥 Videos</button></div></div><div class="card"><textarea id="prompt" rows="4" placeholder="What is AI in simple words?" onfocus="showButton()" oninput="showButton()"></textarea><br><br><button class="primary" id="flightBtn" onclick="generate()">✨ Let It Take Flight</button><div id="result" style="margin-top:20px">Results will appear here...</div></div><div class="card"><h3 style="margin-top:0">Unlock Unlimited</h3><div id="plans" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:14px"></div></div></div>
<script>
let PUBLIC_KEY="{{PUBLIC_KEY}}";let currentType="all";
function showButton(){document.getElementById('flightBtn').classList.remove('hidden');}
function hideButton(){document.getElementById('flightBtn').classList.add('hidden');}
function setType(t){currentType=t;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('tab-'+t).classList.add('active');let pr=document.getElementById('prompt').value.trim();if(pr.length>2){hideButton();generate();}}
async function refreshQuota(){let r=await fetch('/api/me');let d=await r.json();document.getElementById('quota').innerText=d.is_premium?'✨ Premium: '+d.plan:'Free: '+d.remaining+' left';let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(([k,v])=>{let b=document.createElement('button');b.className='primary';b.innerText=v.label+' - GHS '+v.price;b.style.margin='4px';b.onclick=()=>pay(k);p.appendChild(b);});}
function copyResult(){navigator.clipboard.writeText(document.getElementById('result').innerText);alert('Copied!');}
async function generate(){let pr=document.getElementById('prompt').value;if(!pr)return;let resEl=document.getElementById('result');resEl.innerHTML='🧠 Generating simple explanation...';hideButton();try{let r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:pr,type:currentType})});let d=await r.json();if(d.image_url){resEl.innerHTML=`<button class='copy-btn' onclick='copyResult()'>Copy</button>${d.answer}<br><br><img src="${d.image_url}">`;}else{resEl.innerHTML=`<button class='copy-btn' onclick='copyResult()'>Copy</button>${d.answer}`;}}catch(e){resEl.innerHTML=`❌ ${e}`;}setTimeout(refreshQuota,500);}
function pay(plan){if(!PUBLIC_KEY){alert('Paystack not set');return;}fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan})}).then(r=>r.json()).then(d=>{if(d.error)return alert(d.error);var h=PaystackPop.setup({key:PUBLIC_KEY,email:d.email,amount:d.kobo,currency:'GHS',ref:d.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(r=>r.json()).then(v=>{alert(v.message);refreshQuota();});},onClose:function(){}});h.openIframe();});}
refreshQuota();
</script></body></html>
"""

@app.route("/")
def index():
    html = PAGE.replace("{{PUBLIC_KEY}}", PAYSTACK_PUBLIC_KEY)
    uid = get_user_id()
    resp = make_response(html)
    resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365)
    return resp

@app.route("/api/me")
def me():
    data = load_data(); uid = get_user_id(); user = get_user_record(data, uid)
    return jsonify({"remaining": remaining_free(user),"is_premium": is_premium(user),"plan": user.get("plan"),"plans": PLANS})

@app.route("/api/generate", methods=["POST"])
def generate_api():
    data = load_data(); uid = get_user_id(); user = get_user_record(data, uid)
    if not is_premium(user) and user.get("free_used",0) >= FREE_USES:
        return jsonify({"answer":"Free limit - upgrade"}), 403
    j = request.get_json() or {}
    prompt = (j.get("prompt") or "")[:2000]
    search_type = j.get("type","all")
    if not prompt: return jsonify({"answer":"Type something"}), 400

    gemini_key = os.environ.get("GEMINI_API_KEY","") or os.environ.get("GOOGLE_API_KEY","")
    answer = ""; image_url = None

    FALLBACK = f"""**Simple Definition:** AI is software that learns and thinks like a human.

**Easy Explanation:** Like teaching a child kente patterns by showing many examples, we show computers millions of examples (text, photos) and they learn to answer, write, or create. Ghana example: AI helps a designer in Accra create new kente designs fast.

**Modern Facts (2024-2026):**
- 200M+ people use ChatGPT weekly in 2026
- AI can generate 4K ultra-realistic fashion photos in seconds
- Ghana uses AI for market price prediction and MoMo fraud detection
- Modern AI (Gemini) understands text, images and video together
- AI video tools like Sora create 20-second cinematic clips

**Why it matters:** Saves time and lets small Ghanaian brands compete globally."""

    try:
        if search_type == "images":
            safe = urllib.parse.quote(f"{prompt}, ultra photorealistic, 8k, studio lighting"[:700])
            image_url = f"https://image.pollinations.ai/prompt/{safe}?width=1280&height=1280&nologo=true&model=flux&seed={int(time.time())}"
            answer = f"✨ 4K Image: {prompt}"
        elif search_type == "videos":
            answer = f"🎥 Video Concept for: {prompt}\n\nStoryboard + Voiceover will be here. Use All tab for definitions."
        else:
            if not gemini_key:
                answer = FALLBACK
            else:
                instr = {
                    "all": "Explain in SIMPLE, EASY words a 15-year-old can understand. Format with: Simple Definition (1 sentence), Easy Explanation with Ghana kente example, Modern Facts 2024-2026 (4 bullets), Why it matters. Query:",
                    "captions": "Create 7 viral captions with emojis+hashtags for:",
                    "scripts": "Write 30-60 sec TikTok script with hook, body, CTA for:",
                    "stories": "Write inspirational luxury brand story for:"
                }.get(search_type, "Answer simply and clearly:")

                full_prompt = f"{instr} {prompt}"
                ai_answer = ask_gemini(full_prompt, gemini_key)
                if ai_answer:
                    answer = ai_answer
                else:
                    # Clean fallback - NO error dump
                    if search_type == "all":
                        answer = FALLBACK
                    else:
                        answer = f"{FALLBACK}\n\n(Your query was: {prompt})"

    except Exception as e:
        answer = FALLBACK

    user["free_used"] = user.get("free_used",0)+1
    save_data(data)
    out = {"answer": answer}
    if image_url: out["image_url"] = image_url
    resp = make_response(jsonify(out))
    resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365)
    return resp

@app.route("/api/paystack/init", methods=["POST"])
def paystack_init():
    if not PAYSTACK_SECRET_KEY: return jsonify({"error":"Paystack not set"}), 500
    j = request.get_json() or {}; plan = PLANS.get(j.get("plan","day"))
    if not plan: return jsonify({"error":"Invalid"}), 400
    uid = get_user_id(); email = f"{uid}@exquisite.ai"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type":"application/json"}
    payload = {"email": email, "amount": plan["kobo"]*100, "currency":"GHS", "metadata":{"uid":uid,"plan":j.get("plan")}}
    try:
        r = http_requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers, timeout=15)
        jr = r.json()
        if not jr.get("status"): return jsonify({"error": jr.get("message")}), 400
        return jsonify({"reference": jr["data"]["reference"], "kobo": plan["kobo"]*100, "email": email})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/paystack/verify", methods=["POST"])
def paystack_verify():
    j = request.get_json() or {}; ref = j.get("reference")
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    try:
        r = http_requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers=headers, timeout=15)
        jr = r.json()
        if not jr.get("status") or jr["data"]["status"] != "success": return jsonify({"error":"Not success"}), 400
        meta = jr["data"].get("metadata",{}); uid = meta.get("uid") or get_user_id(); plan_key = meta.get("plan","day")
        data = load_data(); user = get_user_record(data, uid); user["plan"]=plan_key; user["expiry"]=int(time.time())+plan["days"]*24*3600
        data.setdefault("payments",[]).append({"uid":uid,"plan":plan_key,"ref":ref,"time":int(time.time())}); save_data(data)
        return jsonify({"message": f"Premium activated! {plan['label']}"})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000)); app.run(host="0.0.0.0", port=port)
