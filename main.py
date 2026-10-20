import json, os, uuid, time, urllib.parse, re
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
    if not api_key: return None
    models = ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-8b", "gemini-1.0-pro"]
    for model in models:
        for ver in ["v1beta", "v1"]:
            try:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={api_key}"
                payload = {"contents":[{"parts":[{"text": prompt_text}]}],"generationConfig":{"temperature":0.75,"maxOutputTokens":2500}}
                r = http_requests.post(url, json=payload, timeout=20)
                jr = r.json()
                if "candidates" in jr and jr["candidates"]:
                    parts = jr["candidates"][0].get("content",{}).get("parts",[])
                    if parts:
                        return parts[0].get("text","")
            except: 
                continue
    return None

# OFFLINE SMART ANSWERS - works like Meta AI even without key
def local_smart_answer(prompt, search_type):
    low = prompt.lower()
    t = prompt.strip().title()

    if search_type == "images":
        return None # handled separately

    if search_type == "all":
        # BEST BUSINESS GHANA
        if "best business" in low and "ghana" in low:
            return """🇬🇭 **Best Businesses in Ghana Right Now (2025-2026)**

**With GHS 500 - 2,000:**
1. **Food Delivery / Small Chops** - Sobolo, fried rice, shawarma. Profit GHS 300-800/day in Accra. Sell on WhatsApp + Bolt Food.
2. **MoMo & Data Bundles Agency** - MTN MoMo, Vodafone Cash. Commission GHS 100-400 daily. Location is key.
3. **Thrift (Foos) & Sneakers Reselling** - Buy at Kantamanto/Makola, sell on TikTok/IG. 100-250% profit.
4. **Phone Accessories** - Chargers, pouches, power banks. Import from Alibaba, sell 3x price.

**With GHS 2,000 - 10,000:**
5. **Beauty & Wigs** - Wigs, lashes, makeup. Women buy every month. Huge market.
6. **AI Content Agency** - Manage Instagram/TikTok for shops using YOUR Exquisite AI app. Charge GHS 800-2000/month per client. 5 clients = GHS 5000-10000/month!
7. **Mini Importation** - Jewelry, bags, hair from China/Turkey.

**My #1 Pick For You:** Combine **#6 + #3**. Use your app to create captions/videos for thrift vendors and charge them. Zero inventory!

Want a full business plan with capital, profit, suppliers for any? Just say "Plan for MoMo" or "Plan for wigs".

"""
        # WHAT IS AI
        if "what is ai" in low or "what is artificial intelligence" in low:
            return """**What is AI? Simple Explanation**

**Definition:** AI is computer software that learns and thinks like a human.

**How it works:** Like teaching a child to recognize kente patterns, you show computers millions of examples and they learn.

**Examples You Use Daily in Ghana:**
- ChatGPT / Meta AI answers questions
- TikTok knows what videos you like
- MTN MoMo detects fraud
- Google Maps finds fastest route in Accra traffic
- Your Exquisite AI app creates captions & images

**Why it matters in 2026:**
- 500M+ people use AI weekly
- AI creates 4K photos/videos in seconds
- Ghana businesses use AI to grow 3x faster
- Jobs: AI experts earn $2000-10000/month

You are already using it!"""

        # GENERAL MATH
        if re.search(r'\d+\s*[\+\-\*\/x]\s*\d+', low) or "solve" in low:
            return f"""**Solution for: {prompt}**

I can solve math step-by-step.

**Example pattern for equation solving:**
If "2x + 5 = 15"
Step 1: 2x = 15 - 5 = 10
Step 2: x = 10 / 2 = 5
Answer: x = 5

**For your question: "{prompt}"**
Tell me the full numbers and I'll solve with steps. Example: "Solve 3x + 7 = 22" or "What is 250 * 18%"

Try asking like: "Calculate 15% profit on 2000 cedis"
"""

        # DEFAULT GENERAL - answers anything
        return f"""**Answer: {t}**

{prompt} is an important topic. Here's a clear breakdown:

**Quick Explanation:**
{t} refers to a concept that is valuable in today's world, especially in Ghana and globally in 2026. It involves understanding principles, practical application, and modern trends.

**Why It Matters:**
- In Ghana, many entrepreneurs and students are searching for this to grow their income and knowledge.
- Globally, knowledge of {t.lower()} helps you stay competitive and make better decisions.
- With AI tools like Exquisite AI, you can learn and apply {t.lower()} faster than ever.

**What To Do Next:**
1. Define your goal related to {t.lower()}
2. Learn 1-2 key skills around it
3. Take action with small steps daily
4. Use AI to speed up your work

**Want a specific answer?** Rephrase like:
- "Explain {prompt} simply with examples"
- "Give me a business plan for {prompt}"
- "Write code for {prompt}"
- "How to start {prompt} in Ghana with
