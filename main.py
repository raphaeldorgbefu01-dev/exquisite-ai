import json, logging, os, uuid, time, urllib.parse
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

FREE_USES = 25
DATA_FILE = "exquisite_data.json"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Exq-8qx1Wn6x9SgU-Ghana2026!")
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")

def load_data():
    if not os.path.exists(DATA_FILE): return {"users": {}, "payments": []}
    try:
        with open(DATA_FILE, "r") as f: return json.load(f)
    except: return {"users": {}, "payments": []}
def save_data(d):
    with open(DATA_FILE, "w") as f: json.dump(f, d, indent=2)
def get_user_id():
    uid = request.cookies.get("exquisite_uid") or request.headers.get("X-User-Id")
    if not uid: uid = str(uuid.uuid4())
    return uid
def get_user_record(data, uid):
    users = data.setdefault("users", {})
    if uid not in users: users[uid] = {"free_used":0,"expiry":0,"plan":None}
    return users[uid]
def is_premium(u): return u.get("expiry",0) > time.time()
def remaining_free(u):
    if is_premium(u): return 9999
    return max(0, FREE_USES - u.get("free_used",0))

PLANS = {
    "day": {"label":"Day","price":10,"days":1,"tag":"24 hours","kobo":1000},
    "weekly": {"label":"Weekly","price":49,"days":7,"tag":"POPULAR","kobo":4900},
    "monthly": {"label":"Monthly","price":99,"days":30,"tag":"BEST","kobo":9900},
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>:root{color-scheme:dark;--bg:#101018;--panel:#191923;--line:rgba(255,255,255,.12);--text:#f5f2fa;--muted:#a4a1b2;--violet:#bda0ff;--mint:#a8f0d5;font-family:Inter,sans-serif}*{box-sizing:border-box}body{margin:0;color:var(--text);background:radial-gradient(900px 500px at 15% -10%, rgba(189,160,255,.22), transparent), var(--bg)}.shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0 72px}header{display:flex;justify-content:space-between;align-items:center}.brand{display:flex;align-items:center;gap:12px;font-weight:800}.brand-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:linear-gradient(140deg,var(--violet),var(--mint));color:#17121f;font-weight:900}.service-tag{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}.hero{max-width:860px;margin:82px auto 32px;text-align:center}.eyebrow{color:var(--mint);font-size:11px;font-weight:800;letter-spacing:.24em;text-transform:uppercase}h1{font-size:52px;line-height:1.02;margin:18px 0;letter-spacing:-.03em;background:linear-gradient(180deg,#fff 20%,#b8b0d0 90%);-webkit-background-clip:text;background-clip:text;color:transparent}.hero p{color:var(--muted);font-size:17px;line-height:1.7;max-width:680px;margin:0 auto}.search-tabs{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:22px 0 0}.tab{border:1px solid var(--line);background:#181825;color:var(--muted);padding:9px 15px;border-radius:999px;font-size:13px;font-weight:600;cursor:pointer}.tab.active,.tab:hover{background:var(--violet);color:#111;border-color:var(--violet)}.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:22px;margin:20px 0}button.primary{background:var(--violet);color:#111;border:0;border-radius:12px;padding:13px 22px;font-weight:800;cursor:pointer;transition:all .2s}button.primary.hidden{opacity:0;transform:translateY(10px);pointer-events:none;height:0;padding:0;margin:0;overflow:hidden}textarea{width:100%;padding:14px;border-radius:12px;border:1px solid var(--line);background:#111117;color:#fff;font-size:15px}#result{line-height:1.9;font-size:15px;white-space:pre-wrap;background:#111117;border-radius:12px;padding:16px;min-height:60px;position:relative}#result img{max-width:100%;border-radius:12px;margin-top:12px}.copy-btn{position:absolute;top:8px;right:8px;background:#222;border:1px solid var(--line);color:var(--muted);border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}</style></head><body><div class="shell"><header><div class="brand"><div class="brand-mark">E</div> Exquisite AI</div><div class="service-tag" id="quota">Loading...</div></header><div class="hero"><div class="eyebrow">Where Ideas Transform Into Dreams</div><h1>Where Ideas Take Flight</h1><p>Search viral captions, scripts, stories, images & videos in seconds.</p><div class="search-tabs"><button class="tab active" id="tab-all" onclick="setType('all')">🔍 All</button><button class="tab" id="tab-captions" onclick="setType('captions')">📸 Captions</button><button class="tab" id="tab-scripts" onclick="setType('scripts')">🎬 Scripts</button><button class="tab" id="tab-stories" onclick="setType('stories')">📖 Stories</button><button class="tab" id="tab-images" onclick="setType('images')">🖼️ Images</button><button class="tab" id="tab-videos" onclick="setType('videos')">🎥 Videos</button></div></div><div class="card"><textarea id="prompt" rows="4" placeholder="Ask anything... e.g. 'What is AI in simple words?'" onfocus="showButton()" oninput="showButton()"></textarea><br><br><button class="primary" id="flightBtn" onclick="generate()">✨ Let It Take Flight</button><div id="result" style="margin-top:20px">Results will appear here...</div></div><div class="card"><h3 style="margin-top:0">Unlock Unlimited</h3><div id="plans" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:14px"></div></div></div>
<script>
let PUBLIC_KEY="{{PUBLIC_KEY}}";
let currentType="all";
function showButton(){let b=document.getElementById('flightBtn');b.classList.remove('hidden');b.style.display='inline-block';}
function hideButton(){let b=document.getElementById('flightBtn');b.classList.add('hidden');setTimeout(()=>{if(b.classList.contains('hidden'))b.style.display='none';},200);}
function setType(t){currentType=t;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('tab-'+t).classList.add('active');let ph={all:"Ask anything... e.g. 'What is blockchain in simple words?'",captions:"Viral captions for...",scripts:"TikTok script for...",stories:"Brand story for...",images:"Luxury Ghanaian model in kente, 4k",videos:"Cinematic runway, slow motion"};document.getElementById('prompt').placeholder=ph[t]||ph.all;let pr=document.getElementById('prompt').value.trim();if(pr.length>2){hideButton();generate();}}
async function refreshQuota(){let r=await fetch('/api/me');let d=await r.json();document.getElementById('quota').innerText=d.is_premium?'✨ Premium: '+d.plan:'Free: '+d.remaining+' left';let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(([k,v])=>{let b=document.createElement('button');b.className='primary';b.innerText=v.label+' - GHS '+v.price;b.style.margin='4px';b.onclick=()=>pay(k);p.appendChild(b);});}
function copyResult(){let t=document.getElementById('result').innerText;navigator.clipboard.writeText(t);alert('Copied!');}
async function generate(){
 let pr=document.getElementById('prompt').value; if(!pr){alert('Type something');return;}
 let resEl=document.getElementById('result');
 resEl.innerHTML='🧠 Explaining simply with modern facts... (if stuck >10s, check Gemini key)';
 hideButton();
 try{
  let controller = new AbortController(); let timeout = setTimeout(()=>controller.abort(), 25000);
  let r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:pr,type:currentType}),signal:controller.signal});
  clearTimeout(timeout);
  let d=await r.json();
  if(d.image_url){
    resEl.innerHTML=`<button class='copy-btn' onclick='copyResult()'>Copy</button>${d.answer}<br><br><img src="${d.image_url}" loading="lazy"><br><a href="${d.image_url}" target="_blank" style="color:#bda0ff">Open full</a>`;
  }else{
    resEl.innerHTML=`<button class='copy-btn' onclick='copyResult()'>Copy</button>${(d.answer||d.error||'Error').replace(/\\n/g,'<br>')}`;
  }
 }catch(e){
  resEl.innerHTML=`❌ Request timed out or failed: ${e}.<br><br>Your Render free server might be sleeping or Gemini key invalid. Please refresh page and try again. If persists, check Render logs.`;
 }
 setTimeout(refreshQuota, 500);
}
function pay(plan){if(!PUBLIC_KEY){alert('Paystack keys not set');return;}fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan})}).then(r=>r.json()).then(d=>{if(d.error)return alert(d.error);var h=PaystackPop.setup({key:PUBLIC_KEY,email:d.email,amount:d.kobo,currency:'GHS',ref:d.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(r=>r.json()).then(v=>{alert(v.message);refreshQuota();});},onClose:function(){}});h.openIframe();});}
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
        return jsonify({"answer":"Free limit reached - please upgrade to continue."}), 403
    j = request.get_json() or {}
    prompt = (j.get("prompt") or "")[:2000]
    search_type = j.get("type","all")
    if not prompt: return jsonify({"answer":"Please type something"}), 400

    gemini_key = os.environ.get("GEMINI_API_KEY","") or os.environ.get("GOOGLE_API_KEY","")
    answer = ""; image_url = None

    # SIMPLE fallback if Gemini fails - so it NEVER hangs 40 minutes
    FALLBACK_ALL = f"""**Simple Definition:**
AI (Artificial Intelligence) is computer software that learns and thinks like a human.

**Easy Explanation:**
Imagine teaching a child to recognize kente cloth. You show many examples until they learn. AI works the same - we show computers millions of examples (photos, text) and they learn to answer, write, or create images. Example in Ghana: AI can help a fashion designer in Accra create new kente patterns automatically.

**Most Known Modern Facts (2024-2026):**
• ChatGPT has over 200M weekly users in 2026
• AI can now generate 4K ultra-realistic fashion photos in seconds
• Ghana is using AI for market price prediction and mobile money fraud detection
• Modern AI models like Gemini 1.5 can understand text, images, and video together
• AI video generation (Sora, Runway) now creates 20-second cinematic clips

**Why it matters today:**
It saves time, makes businesses faster, and lets small brands in Ghana compete with big global brands.

*Question was: {prompt}*"""

    try:
        if search_type in ["images","videos"]:
            enhanced = prompt
            if gemini_key:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                    payload = {"contents":[{"parts":[{"text": f"Enhance this into detailed photorealistic prompt, only prompt: {prompt}"}]}]}
                    r = http_requests.post(url, json=payload, timeout=12)
                    jr = r.json()
                    if "candidates" in jr:
                        enhanced = jr["candidates"][0]["content"]["parts"][0]["text"].strip()
                except: pass
            
            if search_type == "images":
                safe = urllib.parse.quote(f"{enhanced}, ultra photorealistic, 8k, realistic skin texture, Canon EOS R5, 85mm lens, studio lighting"[:700])
                image_url = f"https://image.pollinations.ai/prompt/{safe}?width=1280&height=1280&nologo=true&model=flux-pro&enhance=true&seed={int(time.time())}"
                answer = f"✨ Dream Image in 4K:\n{enhanced}"
            else:
                safe = urllib.parse.quote((enhanced[:300] + ", cinematic video still, 16:9")[:700])
                image_url = f"https://image.pollinations.ai/prompt/{safe}?width=1280&height=720&nologo=true&model=flux-pro&enhance=true&seed={int(time.time())}"
                answer = f"🎥 Video Concept:\n{enhanced}\n\nUse this prompt in Runway/Pika to make real video."
        else:
            if not gemini_key:
                answer = FALLBACK_ALL + "\n\n⚠️ NOTE: Set GEMINI_API_KEY in Render to get live answers."
            else:
                # DIRECT call - no models list check that was causing hang
                instruction = {
                    "all": "Explain in SIMPLE, EASY words a 15-year-old understands. Give: 1) Simple Definition (1 sentence), 2) Easy Explanation with Ghana example, 3) 3-5 Modern Facts 2024-2026 bullet points, 4) Why it matters. Simple English, short sentences. Query:",
                    "captions": "Create 7 viral captions with hashtags+emojis for:",
                    "scripts": "Write 30-60 sec TikTok script with hook, body, CTA for:",
                    "stories": "Write luxurious brand story for:",
                }.get(search_type, "Answer simply:")

                last_err = ""
                for model in ["gemini-1.5-flash","gemini-1.5-flash-001","gemini-2.0-flash"]:
                    try:
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
                        payload = {"contents":[{"parts":[{"text": f"{instruction} {prompt}"}]}],"generationConfig":{"temperature":0.7,"maxOutputTokens":1200}}
                        r = http_requests.post(url, json=payload, timeout=18)
                        jr = r.json()
                        if "candidates" in jr and jr["candidates"]:
                            answer = jr["candidates"][0]["content"]["parts"][0]["text"]
                            if answer.strip(): break
                        last_err = str(jr)[:500]
                    except Exception as e:
                        last_err = str(e)
                        continue
                
                if not answer:
                    # If Gemini fails, use fallback so user is not stuck 40 mins
                    if search_type == "all" and "what is ai" in prompt.lower():
                        answer = FALLBACK_ALL
                    else:
                        answer = f"AI is thinking but Gemini returned error: {last_err[:300]}. \n\nFallback answer: {FALLBACK_ALL if search_type=='all' else 'Try again in 10s. If persists, check your GEMINI_API_KEY in Render Dashboard > Environment.'}"

    except Exception as e:
        answer = f"Error: {e}\n\nFallback: {FALLBACK_ALL}"

    user["free_used"] = user.get("free_used",0)+1; save_data(data)
    out = {"answer": answer}
    if image_url: out["image_url"] = image_url
    resp = make_response(jsonify(out)); resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365); return resp

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
        meta = jr["data"].get("metadata",{}); uid = meta.get("uid") or get_user_id(); plan_key = meta.get("plan","day"); plan = PLANS.get(plan_key, PLANS["day"])
        data = load_data(); user = get_user_record(data, uid); user["plan"]=plan_key; user["expiry"]=int(time.time())+plan["days"]*24*3600
        data.setdefault("payments",[]).append({"uid":uid,"plan":plan_key,"ref":ref,"time":int(time.time())}); save_data(data)
        return jsonify({"message": f"Premium activated! {plan['label']}"})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000)); app.run(host="0.0.0.0", port=port)
