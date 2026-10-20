import json, os, uuid, time, urllib.parse, re
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
FREE_USES = 25
DATA_FILE = "exquisite_data.json"
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "payments": []}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "payments": []}

def save_data(d):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except:
        pass

def get_user_id():
    uid = request.cookies.get("exquisite_uid") or request.headers.get("X-User-Id")
    if not uid:
        uid = str(uuid.uuid4())
    return uid

def get_user_record(data, uid):
    users = data.setdefault("users", {})
    if uid not in users:
        users[uid] = {"free_used":0,"expiry":0,"plan":None}
    return users[uid]

def is_premium(u):
    return u.get("expiry",0) > time.time()

def remaining_free(u):
    return 9999 if is_premium(u) else max(0, FREE_USES - u.get("free_used",0))

def ask_gemini(prompt_text, api_key):
    if not api_key:
        return None
    models = ["gemini-1.5-flash-latest","gemini-1.5-flash","gemini-2.0-flash","gemini-1.0-pro"]
    for model in models:
        for ver in ["v1beta","v1"]:
            try:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={api_key}"
                payload = {"contents":[{"parts":[{"text": prompt_text}]}],"generationConfig":{"temperature":0.75,"maxOutputTokens":2500}}
                r = http_requests.post(url, json=payload, timeout=20)
                jr = r.json()
                if "candidates" in jr and jr["candidates"]:
                    parts = jr["candidates"][0].get("content",{}).get("parts",[])
                    if parts:
                        txt = parts[0].get("text","")
                        if txt:
                            return txt
            except:
                continue
    return None

def local_smart_answer(prompt, search_type):
    low = prompt.lower()
    t = prompt.strip().title() or "This Topic"

    if search_type == "images":
        return None

    if search_type == "all":
        if "best business" in low and "ghana" in low:
            return (
                "🇬🇭 Best Businesses in Ghana Right Now (2025-2026)\n\n"
                "With GHS 500 - 2,000:\n"
                "1. Food Delivery / Small Chops - Sobolo, fried rice, shawarma. Profit GHS 300-800/day in Accra.\n"
                "2. MoMo & Data Bundles Agency - MTN MoMo. Commission GHS 100-400 daily.\n"
                "3. Thrift (Foos) & Sneakers - Buy at Kantamanto, sell on TikTok. 100-250% profit.\n"
                "4. Phone Accessories - Chargers, pouches, power banks. 3x price.\n\n"
                "With GHS 2,000 - 10,000:\n"
                "5. Beauty & Wigs - Wigs, lashes, makeup. Monthly demand.\n"
                "6. AI Content Agency - Manage Instagram for shops using YOUR app. Charge GHS 800-2000/month per client.\n"
                "7. Mini Importation - Jewelry, bags from China.\n\n"
                "My #1 Pick For You: Combine #6 + #3. Use Exquisite AI to create captions for vendors and charge them. Zero inventory!\n"
                "Want full plan? Say 'Plan for MoMo' or 'Plan for wigs'."
            )
        if "what is ai" in low:
            return (
                "What is AI? Simple Explanation\n\n"
                "Definition: AI is computer software that learns and thinks like a human.\n\n"
                "How it works: Like teaching a child to recognize kente patterns, you show computers millions of examples.\n\n"
                "Examples in Ghana:\n"
                "- ChatGPT / Meta AI answers questions\n"
                "- TikTok knows what videos you like\n"
                "- MoMo detects fraud\n"
                "- Your Exquisite AI app creates captions & images\n\n"
                "In 2026, 500M+ people use AI weekly. AI creates photos/videos in seconds."
            )
        # Default general answer - works for ANY question
        return (
            f"Answer: {t}\n\n"
            f"You asked: {prompt}\n\n"
            "Quick Explanation:\n"
            f"{t} is valuable in Ghana and globally in 2026. It involves understanding principles and practical use.\n\n"
            "Why It Matters:\n"
            "- In Ghana many entrepreneurs search for this to grow income\n"
            "- Globally, knowing this helps you stay competitive\n"
            "- With AI tools like Exquisite AI you can learn faster\n\n"
            "Next Steps:\n"
            "1. Define your goal\n"
            "2. Learn 1-2 key skills\n"
            "3. Take small daily action\n"
            "4. Use AI to speed up\n\n"
            f"Ask more specifically: 'Explain {prompt} simply' or 'Business plan for {prompt}' or 'Write code for {prompt}'"
        )

    if search_type == "captions":
        return (
            f"7 Viral Captions for: {t}\n\n"
            "1. Ghanaian elegance in slow motion - Where culture meets class #GhanaFashion\n"
            "2. Slow mo, but make it fashion - Kente never looked this good #Kente\n"
            "3. When tradition takes flight - Ghana to the world! #AfricanFashion\n"
            "4. Fabric flowing, hearts glowing - This is Ghana redefined #AccraStyle\n"
            "5. 60fps of pure culture - Watch the details dance #RunwayMagic\n"
            "6. Luxury is in the details - Slow motion appreciation #LuxuryFashion\n"
            "7. From Accra with love - Your brand deserves shine #ExquisiteAI\n"
        )

    if search_type == "scripts":
        return (
            f"30-Second Script for: {t}\n\n"
            "HOOK (0-3s): Close-up slow mo - Stop scrolling! This is why this is taking over...\n"
            "BODY (3-25s): Wide reveal 60fps, close-up details 120fps, model twirl and eye contact\n"
            "CTA (25-30s): Follow for more! Comment your favorite part!\n"
            "Music: Afrobeats soft drums + whoosh SFX\n"
        )

    if search_type == "stories":
        return (
            f"Brand Story for: {t}\n\n"
            "Heritage: In the heart of Accra, where tradition meets ambition, a vision was born.\n"
            f"The Moment: {t} is where culture, creativity and modern tech meet.\n"
            "Emotion: True luxury is attention to detail. It's crafted, not rushed.\n"
            "Mission: Exquisite AI brings Ghanaian excellence to the world.\n"
            "Tagline: Where Ideas Take Flight\n"
        )

    return f"Answer for {prompt}"

PLANS = {
    "day": {"label":"Day - GHS 10","price":10,"kobo":1000,"days":1},
    "weekly": {"label":"Weekly - GHS 49","price":49,"kobo":4900,"days":7},
    "monthly": {"label":"Monthly - GHS 99","price":99,"kobo":9900,"days":30}
}

PAGE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>
body{margin:0;background:#0f0f18;color:#f5f2fa;font-family:Inter,system-ui,sans-serif}
.shell{width:min(1050px,calc(100% - 32px));margin:0 auto;padding:24px 0}
.card{background:#191923;border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:20px;margin:18px 0}
button.primary{background:#bda0ff;color:#111;border:0;border-radius:12px;padding:12px 20px;font-weight:800;cursor:pointer}
button.primary.hidden{display:none!important}
textarea{width:100%;padding:16px;border-radius:14px;border:1px solid rgba(255,255,255,.15);background:#11111a;color:#fff;font-size:15px;outline:none;box-sizing:border-box}
textarea:focus{border-color:#bda0ff}
.tab{border:1px solid rgba(255,255,255,.12);background:#181825;color:#a4a1b2;padding:9px 16px;border-radius:999px;font-size:13px;cursor:pointer;margin:3px}
.tab.active{background:#bda0ff;color:#111;font-weight:700}
#result{line-height:1.75;white-space:pre-wrap;background:#11111a;border-radius:14px;padding:18px;min-height:70px;position:relative;border:1px solid rgba(255,255,255,.06)}
.copy-btn{position:absolute;top:10px;right:10px;background:#23232f;border:1px solid rgba(255,255,255,.12);color:#a4a1b2;border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}
.badge{display:inline-block;background:rgba(189,160,255,.15);border:1px solid rgba(189,160,255,.3);color:#bda0ff;border-radius:999px;padding:3px 10px;font-size:11px;margin-bottom:10px}
</style></head><body><div class="shell"><h1 style="text-align:center;margin:8px 0">Where Ideas Take Flight</h1><p style="text-align:center;color:#a4a1b2;font-size:13px;margin:0 0 10px">Ask anything like Gemini & Meta AI — math, code, business, health, fashion</p><div style="text-align:center;margin:14px 0"><button class="tab active" id="tab-all" onclick="setType('all')">All</button><button class="tab" id="tab-captions" onclick="setType('captions')">Captions</button><button class="tab" id="tab-scripts" onclick="setType('scripts')">Scripts</button><button class="tab" id="tab-stories" onclick="setType('stories')">Stories</button><button class="tab" id="tab-images" onclick="setType('images')">Images</button></div><div class="card"><div class="badge" id="modeBadge">Mode: All - General AI</div><textarea id="prompt" rows="4" placeholder="Ask anything: Best business in Ghana? What is AI? Solve 2x+5=15?" onfocus="showButton()" oninput="showButton()"></textarea><br><br><button class="primary hidden" id="flightBtn" onclick="generate()">Let It Take Flight</button><div id="result" style="margin-top:16px"><span style="color:#a4a1b2">Your answer will appear here...</span></div></div><div class="card"><h3 style="margin:0 0 10px">Unlock Unlimited</h3><div id="plans"></div><div id="quota" style="margin-top:10px;color:#a4a1b2;font-size:13px"></div></div></div>
<script>
let PUBLIC_KEY="{{PUBLIC_KEY}}";let currentType="all";
function showButton(){document.getElementById('flightBtn').classList.remove('hidden');}
function hideButton(){document.getElementById('flightBtn').classList.add('hidden');}
function setType(t){
  currentType=t;
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+t).classList.add('active');
  document.getElementById('modeBadge').innerText='Mode: '+t;
  let pr=document.getElementById('prompt').value.trim();
  if(pr.length>2){
    document.getElementById('result').innerHTML='Switching
