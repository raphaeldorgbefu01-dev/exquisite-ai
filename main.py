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
    try:
        with open(DATA_FILE, "w") as f: json.dump(d, f, indent=2)
    except: pass
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
    for model in ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.0-pro"]:
        for ver in ["v1", "v1beta"]:
            try:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={api_key}"
                payload = {"contents":[{"parts":[{"text": prompt_text}]}],"generationConfig":{"temperature":0.7,"maxOutputTokens":2000}}
                r = http_requests.post(url, json=payload, timeout=20)
                jr = r.json()
                if "candidates" in jr and jr["candidates"]:
                    return jr["candidates"][0]["content"]["parts"][0]["text"]
            except: continue
    return None

PLANS = {"day": {"label":"Day","price":10,"kobo":1000,"days":1}, "weekly": {"label":"Weekly","price":49,"kobo":4900,"days":7}, "monthly": {"label":"Monthly","price":99,"kobo":9900,"days":30}}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>
body{margin:0;background:#101018;color:#f5f2fa;font-family:Inter,sans-serif}
.shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0}
.card{background:#191923;border:1px solid rgba(255,255,255,.12);border-radius:18px;padding:22px;margin:20px 0}
button.primary{background:#bda0ff;color:#111;border:0;border-radius:12px;padding:13px 22px;font-weight:800;cursor:pointer}
button.primary.hidden{display:none!important}
textarea{width:100%;padding:14px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:#111117;color:#fff;font-size:15px;outline:none}
textarea:focus{border-color:#bda0ff}
.tab{border:1px solid rgba(255,255,255,.12);background:#181825;color:#a4a1b2;padding:9px 15px;border-radius:999px;font-size:13px;cursor:pointer;margin:2px}
.tab.active{background:#bda0ff;color:#111}
#result{line-height:1.8;white-space:pre-wrap;background:#111117;border-radius:12px;padding:16px;min-height:60px;position:relative}
.copy-btn{position:absolute;top:8px;right:8px;background:#222;border:1px solid rgba(255,255,255,.12);color:#a4a1b2;border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}
</style></head><body><div class="shell"><h1 style="text-align:center">Where Ideas Take Flight</h1><p style="text-align:center;color:#a4a1b2;font-size:14px">Ask anything — like Gemini & Meta AI. Math, coding, health, business, fashion...</p><div style="text-align:center"><button class="tab active" id="tab-all" onclick="setType('all')">🔍 All</button><button class="tab" id="tab-captions" onclick="setType('captions')">📸 Captions</button><button class="tab" id="tab-scripts" onclick="setType('scripts')">🎬 Scripts</button><button class="tab" id="tab-stories" onclick="setType('stories')">📖 Stories</button><button class="tab" id="tab-images" onclick="setType('images')">🖼️ Images</button></div><div class="card"><textarea id="prompt" rows="4" placeholder="Ask anything: What is AI? Solve 2x+5=15? Write code for website? Best business in Ghana?" onfocus="showButton()" oninput="showButton()"></textarea><br><br><button class="primary hidden" id="flightBtn" onclick="generate()">✨ Let It Take Flight</button><div id="result" style="margin-top:20px">Results will appear here...</div></div><div class="card"><h3>Unlock Unlimited</h3><div id="plans"></div><div id="quota" style="margin-top:10px;color:#a4a1b2"></div></div></div>
<script>
let PUBLIC_KEY="{{PUBLIC_KEY}}";let currentType="all";
function showButton(){document.getElementById('flightBtn').classList.remove('hidden');}
function hideButton(){document.getElementById('flightBtn').classList.add('hidden');}
function setType(t){
  currentType=t;
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+t).classList.add('active');
  let pr=document.getElementById('prompt').value.trim();
  if(pr.length>1){
    document.getElementById('result').innerHTML='🧠 Switching to '+t+'...';
    hideButton();
    generate();
  }
}
async function refreshQuota(){try{let r=await fetch('/api/me');let d=await r.json();document.getElementById('quota').innerText=d.is_premium?'Premium: '+d.plan:'Free: '+d.remaining+' left';let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(([k,v])=>{let b=document.createElement('button');b.className='primary';b.innerText=v.label+' - GHS '+v.price;b.style.margin='4px';b.onclick=()=>pay(k);p.appendChild(b);});}catch(e){}}
function copyResult(){navigator.clipboard.writeText(document.getElementById('result').innerText);alert('Copied!');}
async function generate(){
  let pr=document.getElementById('prompt').value;
  if(!pr)return;
  let resEl=document.getElementById('result');
  resEl.innerHTML='🧠 Generating '+currentType+'...';
  hideButton();
  try{
    let r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:pr,type:currentType})});
    let d=await r.json();
    let html=`<button class='copy-btn' onclick='copyResult()'>Copy</button>${d.answer}`;
    if(d.image_url){html+=`<br><br><img src="${d.image_url}" style="max-width:100%;border-radius:12px">`;}
    resEl.innerHTML=html;
  }catch(e){resEl.innerHTML='❌ '+e;}
  setTimeout(refreshQuota,500);
}
function pay(plan){if(!PUBLIC_KEY){alert('Paystack not set');return;}fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan})}).then(r=>r.json()).then(d=>{if(d.error)return alert(d.error);var h=PaystackPop.setup({key:PUBLIC_KEY,email:d.email,amount:d.kobo,currency:'GHS',ref:d.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(r=>r.json()).then(v=>{alert(v.message);refreshQuota();});},onClose:function(){}});h.openIframe();});}
document.getElementById('prompt').addEventListener('focus', showButton);
document.getElementById('prompt').addEventListener('input', showButton);
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
    try:
        data = load_data(); uid = get_user_id(); user = get_user_record(data, uid)
        if not is_premium(user) and user.get("free_used",0) >= FREE_USES:
            return jsonify({"answer":"Free limit reached - upgrade to continue unlimited questions"})

        j = request.get_json() or {}
        prompt = (j.get("prompt") or "").strip()[:3000]
        search_type = j.get("type","all")
        gemini_key = os.environ.get("GEMINI_API_KEY","") or os.environ.get("GOOGLE_API_KEY","")

        if not prompt:
            return jsonify({"answer":"Please type a question"})

        answer = ""; image_url = None

        # IMAGES TAB
        if search_type == "images":
            enhanced = prompt
            if gemini_key:
                ai = ask_gemini(f"Create one ultra detailed photorealistic image prompt, only the prompt, no quotes: {prompt}", gemini_key)
                if ai: enhanced = ai[:600]
            full = f"{enhanced}, ultra photorealistic, 8k, highly detailed, professional lighting"
            safe = urllib.parse.quote(full[:700])
            image_url = f"https://image.pollinations.ai/prompt/{safe}?width=1280&height=1280&nologo=true&model=flux&seed={int(time.time())}"
            answer = f"🖼️ **4K Image for: {prompt}**\n\n**Prompt:** {full}"

        # ALL TAB - FULL GENERAL AI LIKE GEMINI/META AI
        elif search_type == "all":
            if gemini_key:
                general_prompt = f"""You are Exquisite AI, a helpful, friendly, expert assistant like Gemini and Meta AI. Answer ANY question the user asks - math, science, coding, health, business, fashion, history, relationships, everything.

Rules:
- Answer clearly, simply, accurately
- Use simple language but be thorough
- If math/coding, show steps and code
- If Ghana-related, use Ghana context
- Be helpful like best AI assistant
- No refusal - answer all topics (except harmful)

User question: {prompt}

Answer in a helpful, well-structured way:"""
                ai = ask_gemini(general_prompt, gemini_key)
                answer = ai if ai else f"I can help with '{prompt}'. Please check your Gemini API key - getting fallback. But here's a quick answer: {prompt} is an interesting topic that I can explain in detail when API is working. For now, try again with a new Gemini key from aistudio.google.com"
            else:
                answer = f"""**Exquisite AI (General Assistant)**

You asked: "{prompt}"

I'm designed to answer ANY question like Gemini and Meta AI - math, science, coding, health, business, fashion, history, etc.

⚠️ My Gemini API key is not set or expired, so I'm in limited mode.

**To enable full answers:**
1. Go to https://aistudio.google.com/app/apikey
2. Create new API key
3. Add it to Render as GEMINI_API_KEY
4. Redeploy

Once enabled, I can:
- Solve math: "Solve 2x+5=15"
- Write code: "Create a website"
- Explain anything: "What is AI? What is photosynthesis?"
- Business ideas, health tips, etc.

Please set the API key to unlock full power!"""

        # CAPTIONS, SCRIPTS, STORIES - specialized
        else:
            if gemini_key:
                instr = {
                    "captions": f"You are a viral social media expert. Create 7 viral captions with emojis and hashtags for: {prompt}",
                    "scripts": f"You are a TikTok/Reels scriptwriter. Write a 30-60 second engaging script with HOOK, BODY, CTA, visual cues for: {prompt}",
                    "stories": f"You are a luxury brand storyteller. Write an inspirational luxury brand story with heritage, emotion, mission, tagline, CTA for: {prompt}"
                }.get(search_type, f"Answer: {prompt}")
                ai = ask_gemini(instr, gemini_key)
                answer = ai if ai else f"**{search_type.title()} for: {prompt}**\n\nSet Gemini API key for full generation. This is fallback."
            else:
                answer = f"**{search_type.title()} for: {prompt}**\n\nSet Gemini API key to generate."

        user["free_used"] = user.get("free_used",0)+1
        save_data(data)
        out = {"answer": answer}
        if image_url: out["image_url"] = image_url
        resp = make_response(jsonify(out))
        resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365)
        return resp
    except Exception as e:
        return jsonify({"answer": f"Error: {e}\n\nTry again."})

@app.route("/api/paystack/init", methods=["POST"])
def paystack_init():
    try:
        if not PAYSTACK_SECRET_KEY: return jsonify({"error":"Paystack not set"}), 500
        j = request.get_json() or {}; plan = PLANS.get(j.get("plan","day"))
        if not plan: return jsonify({"error":"Invalid"}), 400
        uid = get_user_id(); email = f"{uid}@exquisite.ai"
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type":"application/json"}
        payload = {"email": email, "amount": plan["kobo"]*100, "currency":"GHS", "metadata":{"uid":uid,"plan":j.get("plan")}}
        r = http_requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers, timeout=15)
        jr = r.json()
        if not jr.get("status"): return jsonify({"error": jr.get("message")}), 400
        return jsonify({"reference": jr["data"]["reference"], "kobo": plan["kobo"]*100, "email": email})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/paystack/verify", methods=["POST"])
def paystack_verify():
    try:
        j = request.get_json() or {}; ref = j.get("reference")
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        r = http_requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers=headers, timeout=15)
        jr = r.json()
        if not jr.get("status") or jr["data"]["status"] != "success": return jsonify({"error":"Not success"}), 400
        meta = jr["data"].get("metadata",{}); uid = meta.get("uid") or get_user_id(); plan_key = meta.get("plan","day")
        data = load_data(); user = get_user_record(data, uid); user["plan"]=plan_key; user["expiry"]=int(time.time())+plan["days"]*24*3600
        data.setdefault("payments",[]).append({"uid":uid,"plan":plan_key,"ref":ref,"time":int(time.time())}); save_data(data)
        return jsonify({"message": f"Premium activated!"})
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
