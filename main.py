import json, os, uuid, time, urllib.parse
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

def local_answer(prompt, search_type):
    low = prompt.lower()
    t = prompt.strip()[:100].title() or "This Topic"
    if search_type == "all":
        if "best business" in low and "ghana" in low:
            return "Best Businesses in Ghana 2025-26:\n\n1. Food Delivery - GHS 300-800/day\n2. MoMo Agency - GHS 100-400 daily commission\n3. Thrift & Sneakers - Buy at Kantamanto, sell on TikTok 100-250% profit\n4. Phone Accessories - 3x price\n5. Beauty & Wigs - monthly demand\n6. AI Content Agency - Manage Instagram for shops using this app, charge GHS 800-2000/month per client\n\nMy pick: Combine #6 + #3. Zero inventory!"
        if "what is ai" in low:
            return "What is AI? AI is software that learns like a human. Example: You show computers millions of kente patterns and it learns. You use it daily - TikTok, MoMo fraud check, Google Maps, this app. In 2026, 500M+ use AI weekly."
        return f"Answer for: {prompt}\n\nThis is {t}. It is important in Ghana and globally in 2026. To learn more, ask specifically like: Explain {prompt} simply, or Business plan for {prompt}, or Write code for {prompt}."
    if search_type == "captions":
        return f"7 Captions for {t}:\n1. Ghanaian elegance in slow motion #GhanaFashion\n2. Slow mo but make it fashion #Kente\n3. When tradition takes flight #AfricanFashion\n4. Fabric flowing hearts glowing #AccraStyle\n5. 60fps of pure culture #RunwayMagic\n6. Luxury in details #LuxuryFashion\n7. From Accra with love #ExquisiteAI"
    if search_type == "scripts":
        return f"Script for {t}:\nHOOK 0-3s: Stop scrolling! Why {t} is trending\nBODY 3-25s: Wide 60fps, close-up 120fps, twirl\nCTA 25-30s: Follow for more! Comment favorite!"
    if search_type == "stories":
        return f"Brand Story for {t}:\nHeritage: In Accra tradition meets ambition\nMoment: {t} is where culture meets modern tech\nMission: Exquisite AI brings Ghana excellence to world\nTagline: Where Ideas Take Flight"
    return f"Answer for {prompt}"

PLANS = {
    "day": {"label":"Day - GHS 10","price":10,"kobo":1000,"days":1},
    "weekly": {"label":"Weekly - GHS 49","price":49,"kobo":4900,"days":7},
    "monthly": {"label":"Monthly - GHS 99","price":99,"kobo":9900,"days":30}
}

PAGE = '''
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>
body{margin:0;background:#0f0f18;color:#f5f2fa;font-family:Inter,system-ui,sans-serif}
.shell{width:min(1050px,calc(100% - 32px));margin:0 auto;padding:24px 0}
.card{background:#191923;border:1px solid rgba(255,255,255,.12);border-radius:20px;padding:20px;margin:18px 0}
button.primary{background:#bda0ff;color:#111;border:0;border-radius:12px;padding:12px 20px;font-weight:800;cursor:pointer}
button.primary.hidden{display:none!important}
textarea{width:100%;padding:16px;border-radius:14px;border:1px solid rgba(255,255,255,.15);background:#11111a;color:#fff;font-size:15px;outline:none;box-sizing:border-box}
textarea:focus{border-color:#bda0ff}
.tab{border:1px solid rgba(255,255,255,.12);background:#181825;color:#a4a1b2;padding:9px 16px;border-radius:999px;font-size:13px;cursor:pointer;margin:3px}
.tab.active{background:#bda
