import json, os, uuid, time, urllib.parse, base64
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE,"r") as f:
            return json.load(f)
    except:
        return {"users":{}}

def save_data(d):
    try:
        with open(DATA_FILE,"w") as f:
            json.dump(d,f)
    except:
        pass

def get_uid():
    u = request.cookies.get("uid")
    if not u:
        u = request.headers.get("X-User-Id")
    if not u:
        u = str(uuid.uuid4())
    return u

def get_user(data, uid):
    users = data.setdefault("users",{})
    if uid not in users:
        users[uid] = {"used":0}
    return users[uid]

def ask_gemini(q, key):
    if not key:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/"
        url += "gemini-1.5-flash-latest:generateContent?key=" + key
        payload = {"contents":[{"parts":[{"text":q}]}],"generationConfig":{"maxOutputTokens":3000}}
        r = http_requests.post(url, json=payload, timeout=20)
        j = r.json()
        if "candidates" in j and j["candidates"]:
            return j["candidates"][0]["content"]["parts"][0]["text"]
    except:
        pass
    return None

def local_answer(prompt, typ):
    low = prompt.lower()
    s = prompt[:80]
    if typ == "all":
        if "best business" in low and "ghana" in low:
            a = "Best Businesses Ghana 2025-26:\n\n"
            a += "1. Food Delivery - GHS 300-800/day Accra\n"
            a += "2. MoMo + Data - GHS 100-400 commission\n"
            a += "3. Thrift Kantamanto - Buy 20 sell 100 profit 150%\n"
            a += "4. Phone Accessories - Chargers 3x markup\n"
            a += "5. Beauty Wigs - monthly demand\n"
            a += "6. AI Agency - Manage IG for shops GHS 800-2000/mo\n"
            a += "\nPick: Combine 6 + 3 zero inventory!"
            return a
        if "what is ai" in low:
            a = "What is AI? Simple:\n"
            a += "AI is software that learns like human.\n"
            a += "Show millions examples like kente patterns.\n"
            a += "Daily: TikTok, MoMo fraud, Maps, this app.\n"
            a += "2026 500M+ use AI weekly."
            return a
        if "code" in low or "html" in low or "website" in low:
            a = "Code for: " + s + "\n\n"
            a += "<html><body><h1>" + s[:30] + "</h1>"
            a += "<p>Built with Exquisite AI Ghana</p>"
            a += "<button>Shop Now</button></body></html>\n"
            a += "Ask: Build ecommerce with cart"
            return a
        if "=" in prompt or "solve" in low or "calculate" in low:
            a = "Math for: " + s + "\n"
            a += "Steps: Move numbers, divide.\n"
            a += "Ex: 2x+5=15 -> 2x=10 -> x=5\n"
            a += "Send: Solve 3x+7=22"
            return a
        # DEFAULT ANSWERS EVERYTHING
        a = "Answer for: " + s + "\n\n"
        a += s + " is important in Ghana 2026.\n\n"
        a += "What it is: Topic used to grow income/skills.\n"
        a += "Why matters: Helps jobs, business, decisions.\n"
        a += "How to start: Goal, learn 1 skill, act daily, use AI.\n\n"
        a += "Ask deeper: Explain " + s[:30] + " simply"
        return a
    if typ == "captions":
        return "7 Captions for " + s + " - Ghana Fashion Kente AccraStyle"
    if typ == "scripts":
        return "Script for " + s + " HOOK 0-3s Stop scroll BODY 60fps CTA Follow"
    if typ == "stories":
        return "Story for " + s + " Heritage Accra Mission Exquisite AI"
    return "Answer for " + s

PLANS = {
    "day":{"label":"Day GHS 10","kobo":1000,"days":1},
    "weekly":{"label":"Weekly GHS 49","kobo":4900,"days":7},
    "monthly":{"label":"Monthly GHS 99","kobo":9900,"days":30}
}

PAGE_B64 = "PCFkb2N0eXBlIGh0bWw+PGh0bWw+PGhlYWQ+PG1ldGEgY2hhcnNldD0idXRmLTgiPjxtZXRhIG5hbWU9InZpZXdwb3J0IiBjb250ZW50PSJ3aWR0aD1kZXZpY2Utd2lkdGgsaW5pdGlhbC1zY2FsZT0xIj48dGl0bGU+RXhxdWlzaXRlIEFJPC90aXRsZT48c3R5bGU+Ym9keXtiYWNrZ3JvdW5kOiMwZjBmMTg7Y29sb3I6I2ZmZjtwYWRkaW5nOjIwcHh9LmNhcmR7YmFja2dyb3VuZDojMTkxOTIzO3BhZGRpbmc6MTZweDttYXJnaW46MTZweCAwO2JvcmRlci1yYWRpdXM6MTZweH10ZXh0YXJlYXt3aWR0aDoxMDAlO3BhZGRpbmc6MTJweDtiYWNrZ3JvdW5kOiMxMTE7Y29sb3I6I2ZmZn1idXR0b257YmFja2dyb3VuZDojYmRhMGZmO2JvcmRlcjowO3BhZGRpbmc6MTBweCAxNnB4O2JvcmRlci1yYWRpdXM6MTBweDtmb250LXdlaWdodDo3MDB9LnRhYntwYWRkaW5nOjhweCAxNHB4O2JvcmRlci1yYWRpdXM6MjBweDtiYWNrZ3JvdW5kOiMyMjI7Y29sb3I6I2FhYTtib3JkZXI6MXB4IH
