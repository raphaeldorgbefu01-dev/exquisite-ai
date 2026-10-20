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
        users[uid] = {"used":0,"expiry":0}
    return users[uid]

def ask_gemini(q, key):
    if not key:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=" + key
        payload = {"contents":[{"parts":[{"text":q}]}],"generationConfig":{"temperature":0.8,"maxOutputTokens":3000}}
        r = http_requests.post(url, json=payload, timeout=20)
        j = r.json()
        if "candidates" in j and j["candidates"]:
            txt = j["candidates"][0].get("content",{}).get("parts",[])[0].get("text","")
            if txt:
                return txt
    except:
        pass
    return None

def local_answer(prompt, typ):
    low = prompt.lower()
    short = prompt[:120]
    # ALL TAB - REAL AI WITHOUT KEY
    if typ == "all":
        if "best business" in low and "ghana" in low:
            return "Best Businesses in Ghana 2025-26 (Low Capital):\n\n1. Food Delivery - Sobolo, fried rice, shawarma. Capital GHS 500-1500. Profit GHS 300-800/day in Accra/Kumasi. Sell on WhatsApp, Bolt Food.\n2. MoMo + Data Bundles - MTN MoMo vendor. Capital GHS 200
