import json, os, uuid, time, urllib.parse, base64
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
    t = prompt.strip()[:100].title() or "Topic"
    if search_type == "all":
        if "best business" in low and "ghana" in low:
            return "Best Businesses Ghana 2025-26:\n1. Food Delivery GHS 300-800/day\n2. MoMo Agency GHS 100-400 commission\n3. Thrift at Kantamanto sell on TikTok 100-250% profit\n4. Phone Accessories 3x price\n5. Beauty Wigs monthly demand\n6. AI Content Agency manage Instagram for shops using this app charge GHS 800-2000/month per client\nMy pick: Combine 6+3 zero inventory!"
        if "what is ai" in low:
            return "What is AI? AI is software that learns like human. Example: Show computers millions of kente patterns it learns. You use daily: TikTok, MoMo fraud check, Google Maps, this app. 2026 500M+ use AI weekly."
        return f"Answer for {prompt}\n\nThis is {t}. Important in Ghana globally 2026. Ask specifically: Explain {
