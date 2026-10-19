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
    "monthly": {"label":"Monthly","price":99,"days":30,"tag":"30 days - BEST","kobo":9900},
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>:root{color-scheme:dark;--bg:#101018;--panel:#191923;--line:rgba(255,255,255,.1);--text:#f5f2fa;--muted:#a4a1b2;--violet:#bda0ff;--mint:#a8f0d5;font-family:Inter,system-ui,sans-serif}*{box-sizing:border-box}body{margin:0;color:var(--text);background:radial-gradient(900px 500px at 15% -10%, rgba(189,160,255,.22), transparent), var(--bg)}.shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0 72px}header{display:flex;justify-content:space-between;align-items:center}.brand{display:flex;align-items:center;gap:12px;font-weight:800}.brand-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:linear-gradient(140deg,var(--violet),var(--mint));color:#17121f;font-weight:900}.service-tag{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}.hero{max-width:860px;margin:82px auto 32px;text-align:center}.eyebrow{color:var(--mint);font-size:11px;font-weight:800;letter-spacing:.24em;text-transform:uppercase}h1{font-size:52px;line-height:1.02;margin:18px 0;letter-spacing:-.03em;background:linear-gradient(180deg,#fff 20%,#b8b0d0 90%);-webkit-background-clip:text;background-clip:text;color:transparent}.hero p{color:var(--muted);font-size:17px;line-height:1.7;max-width:680px;margin:0 auto}.search-tabs{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:22px 0 0}.tab{border:1px solid var(--line);background:#181825;color:var(--muted);padding:9px 15px;border-radius:999px;font-size:13px;font-weight:600;cursor:pointer}.tab.active,.tab:hover{background:var(--violet);color:#111;border-color:var(--violet)}.card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:22px;margin:20px 0}button.primary{background:var(--violet);color:#111;border:0;border-radius:12px;padding:13px 22px;font-weight:800;cursor:pointer}textarea{width:100%;padding:14px;border-radius:12px;border:1px solid var(--line);background:#111117;color:#fff;font-family:inherit;font-size:15px}#result{line-height:1.8;font-size:15px;white-space:pre-wrap}#result img{max-width:100%;border-radius:12px;margin-top:12px;border:1px solid var(--line)}</style></head><body><div class="shell"><header><div class="brand"><div class="brand-mark">E</div> Exquisite AI</div><div class="service-tag" id="quota">Loading...</div></header><div class="hero"><div class="eyebrow">Where Ideas Transform Into Dreams</div><h1>Where Ideas Take Flight</h1><p>Search viral captions, scripts, stories, images & videos in seconds.</p><div class="search-tabs"><button class="tab active" id="tab-all" onclick="setType('all')">🔍 All</button><button class="tab" id="tab-captions" onclick="setType('captions')">📸 Captions</button><button class="tab" id="tab-scripts" onclick="setType('scripts')">🎬 Scripts</button><button class="tab" id="tab-stories" onclick="setType('stories')">📖 Stories</button><button class="tab" id="tab-images" onclick="setType('images')">🖼️ Images</button><button class="tab" id="tab-videos" onclick="setType('videos')">🎥 Videos</button></div></div><div class="card"><textarea id="prompt" rows="4" placeholder="Ask anything... e.g. 'What is quantum luxury in fashion?'"></textarea><br><br><button class="primary" onclick="generate()">✨ Let It Take Flight</button><div id="result" style="margin-top:20px"></div></div><div class="card"><h3 style="margin-top:0">Unlock Unlimited</h3><div id="plans" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:14px"></div></div></div>
<script>
let PUBLIC_KEY="{{PUBLIC_KEY}}";
let currentType="all";
function setType(t){ 
  currentType=t; 
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active')); 
  document.getElementById('tab-'+t).classList.add('active'); 
  let ph={
    all:"Ask anything... e.g. 'Explain modern luxury fashion like I'm 5 + definition + 3 facts'",
    captions:"Search viral captions... e.g. 'Ghana fashion week caption'",
    scripts:"Search scripts... e.g. '30s TikTok ad for luxury dress'",
    stories:"Search stories... e.g. 'Brand story for fashion dream'",
    images:"Describe image... e.g. 'Luxury Ghanaian model in kente, 4k ultra realistic'",
    videos:"Describe video... e.g. 'Cinematic runway show, Ghanaian models, slow motion, 8s'"
  }; 
  document.getElementById('prompt').placeholder=ph[t]||ph.all;
  // AUTO GENERATE ON MODE SWITCH if user already typed
  let pr = document.getElementById('prompt').value.trim();
  if(pr.length > 2){
    generate();
  }
}
async function refreshQuota(){ let r=await fetch('/api/me'); let d=await r.json(); document.getElementById('quota').innerText=d.is_premium ? '✨ Premium: '+d.plan : 'Free: '+d.remaining+' left'; let p=document.getElementById('plans'); p.innerHTML=''; Object.entries(d.plans).forEach(([k,v])=>{ let b=document.createElement('button'); b.className='primary'; b.innerText=v.label+' - GHS '+v.price+' ('+v.tag+')'; b.style.margin='4px'; b.onclick=()=>pay(k); p.appendChild(b); });}
async function generate(){ 
  let pr=document.getElementById('prompt').value; 
  if(!pr) return alert('Type what you want'); 
  let resEl=document.getElementById('result'); 
  let loadingText = {
    all: '🧠 Generating sophisticated explanation + facts...',
    captions: '📸 Creating viral captions...',
    scripts: '🎬 Writing viral script...',
    stories: '📖 Crafting story...',
    images: '🖼️ Creating 4K ultra realistic image... 10s',
    videos: '🎥 Creating video concept + storyboard... 10s'
  };
  resEl.innerHTML=loadingText[currentType]||'Generating...';
  let r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:pr,type:currentType})}); 
  let d=await r.json(); 
  if(d.image_url){ 
    resEl.innerHTML=(d.answer ? d.answer+'<br><br>' : '')+`<img src="${d.image_url}" loading="lazy"><br><a href="${d.image_url}" target="_blank" style="color:#bda0ff">Open full ${currentType==='videos'?'Video Thumbnail':'4K'}</a>`; 
  } else { 
    resEl.innerText=d.answer||d.error||JSON.stringify(d);
  } 
  setTimeout(refreshQuota, 500);
}
function pay(plan){ if(!PUBLIC_KEY){alert('Paystack not set');return;} fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan})}).then(r=>r.json()).then(d=>{ if(d.error) return alert(d.error); var handler=PaystackPop.setup({key:PUBLIC_KEY,email:d.email||'user@exquisite.ai',amount:d.kobo,currency:'GHS',ref:d.reference,callback:function(resp){ fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(r=>r.json()).then(v=>{ alert(v.message||'Verified!'); refreshQuota(); }); },onClose:function(){ alert('Closed'); }}); handler.openIframe(); });}
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
def generate():
    data = load_data(); uid = get_user_id(); user = get_user_record(data, uid)
    if not is_premium(user) and user.get("free_used",0) >= FREE_USES:
        return jsonify({"error":"Free limit reached - upgrade"}), 403
    j = request.get_json() or {}
    prompt = (j.get("prompt") or "")[:2000]
    search_type = j.get("type","all")
    if not prompt: return jsonify({"error":"Empty"}), 400

    gemini_key = os.environ.get("GEMINI_API_KEY","") or os.environ.get("GOOGLE_API_KEY","")
    answer = ""; image_url = None

    type_instruction = {
        "all": "You are Exquisite AI - the world's most sophisticated knowledge assistant. For the query, provide: 1) A clear modern definition, 2) Sophisticated explanation (what it is, how it works, why it matters), 3) 3-5 most known/modern facts, 4) History or origin if relevant, 5) Modern examples/trends (2024-2026), 6) Simple summary. Make it elegant, premium, Ghana-friendly, and up-to-date. Query:",
        "captions": "You are VIRAL CAPTIONS expert. Create 5-7 short viral captions with hashtags and emojis for:",
        "scripts": "You are VIRAL SCRIPT expert. Write 30-60 sec TikTok script with hook, body, CTA for:",
        "stories": "You are BRAND STORY expert. Write inspirational luxurious brand story for:",
        "images": "You are IMAGE PROMPT expert. Enhance this into detailed beautiful high-quality prompt:",
        "videos": "You are VIDEO DIRECTOR expert. Create detailed video concept for: Provide 1) Video title, 2) 8-second storyboard (3 scenes with camera moves), 3) Voiceover script, 4) Music/SFX suggestion, 5) Text overlays, 6) Enhanced AI video prompt for generation. Make cinematic. Query:"
    }
    instruction = type_instruction.get(search_type, type_instruction["all"])

    if search_type in ["images","videos"]:
        try:
            enhanced = prompt
            if gemini_key:
                try:
                    for ver in ["v1","v1beta"]:
                        try:
                            url = f"https://generativelanguage.googleapis.com/{ver}/models/gemini-1.5-flash:generateContent?key={gemini_key}"
                            payload = {"contents":[{"parts":[{"text": f"{instruction} {prompt}. Return ONLY enhanced prompt for images, or full video concept for videos."}]}]}
                            r = http_requests.post(url, json=payload, timeout=25)
                            jr = r.json()
                            if "candidates" in jr: enhanced = jr["candidates"][0]["content"]["parts"][0]["text"].strip(); break
                        except: continue
                except: pass
            
            if search_type == "images":
                safe = urllib.parse.quote(f"{enhanced}, ultra photorealistic, 8k, sharp focus, realistic skin texture, fashion editorial, Canon EOS R5, 85mm lens, dramatic studio lighting, kente fabric detail"[:700])
                image_url = f"https://image.pollinations.ai/prompt/{safe}?width=1280&height=1280&nologo=true&model=flux-pro&enhance=true&seed={int(time.time())}"
                answer = f"✨ Dream Image Created in 4K Ultra Realistic!\\n{enhanced}"
            else: # videos
                # Generate thumbnail for video concept
                thumb_prompt = enhanced[:300] + ", cinematic video still, motion blur, 16:9, ultra realistic"
                safe = urllib.parse.quote(thumb_prompt[:700])
                image_url = f"https://image.pollinations.ai/prompt/{safe}?width=1280&height=720&nologo=true&model=flux-pro&enhance=true&seed={int(time.time())}"
                answer = f"🎥 VIDEO CONCEPT CREATED!\\n\\n{enhanced}\\n\\n---\\nPreview thumbnail generated above. Use the enhanced prompt in RunwayML / Pika / CapCut AI to generate actual video."
        except Exception as e:
            answer = f"Generation failed: {e}"
    else:
        if not gemini_key:
            answer = "⚠️ GEMINI_API_KEY not set in Render"
        else:
            last_err = ""
            models_try = ["gemini-1.5-flash","gemini-1.5-flash-001","gemini-2.0-flash","gemini-1.5-flash-latest"]
            try:
                for ver in ["v1","v1beta"]:
                    lr = http_requests.get(f"https://generativelanguage.googleapis.com/{ver}/models?key={gemini_key}", timeout=15)
                    lj = lr.json()
                    if "models" in lj:
                        found = []
                        for m in lj["models"]:
                            if "generateContent" in m.get("supportedGenerationMethods",[]):
                                name = m.get("name","").replace("models/","")
                                if "flash" in name: found.append(name)
                        if found: models_try = found + models_try; break
            except Exception as e: last_err = str(e)
            for model in models_try:
                for ver in ["v1beta","v1"]:
                    try:
                        url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={gemini_key}"
                        payload = {"contents":[{"parts":[{"text": f"{instruction} {prompt}"}]}]}
                        r = http_requests.post(url, json=payload, timeout=35)
                        jr = r.json()
                        if "candidates" in jr and jr["candidates"]:
                            answer = jr["candidates"][0]["content"]["parts"][0]["text"]
                            if answer.strip(): break
                        last_err = str(jr)[:1000]
                    except Exception as e:
                        last_err = str(e); continue
                if answer.strip(): break
            if not answer: answer = f"❌ Gemini error: {last_err[:800]}"

    user["free_used"] = user.get("free_used",0)+1; save_data(data)
    out = {"answer": answer}
    if image_url: out["image_url"] = image_url
    resp = make_response(jsonify(out)); resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365); return resp

@app.route("/api/paystack/init", methods=["POST"])
def paystack_init():
    if not PAYSTACK_SECRET_KEY: return jsonify({"error":"Paystack secret not set"}), 500
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

@app.route("/admin")
def admin():
    pwd = request.args.get("password") or request.args.get("p")
    if pwd != ADMIN_PASSWORD: return "Unauthorized", 401
    d = load_data(); return f"<html><body style='background:#101018;color:#fff;padding:20px'><h1>Admin OK - Users {len(d.get('users',{}))}</h1><a href='/' style='color:#bda0ff'>Home</a></body></html>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000)); app.run(host="0.0.0.0", port=port)
