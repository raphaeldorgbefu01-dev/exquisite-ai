import json, os, uuid, time, urllib.parse, re
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
DATA_FILE = "data.json"
FREE = 25
PUB = os.environ.get("PAYSTACK_PUBLIC_KEY","")
SEC = os.environ.get("PAYSTACK_SECRET_KEY","")
POLL = os.environ.get("POLLINATIONS_TOKEN","")

def load_data():
    try:
        f = open(DATA_FILE,"r")
        d = json.load(f)
        f.close()
        return d
    except:
        return {"users":{}}

def save_data(d):
    try:
        f = open(DATA_FILE,"w")
        json.dump(d,f)
        f.close()
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
        users[uid] = {"used":0,"expiry":0,"plan":None}
    return users[uid]

def is_premium(u):
    return u.get("expiry",0) > time.time()

def remain(u):
    if is_premium(u):
        return 9999
    left = FREE - u.get("used",0)
    if left < 0:
        left = 0
    return left

def ask_gemini(q, key):
    if not key:
        return None
    try:
        url = "https://generativelanguage.googleapis.com/"
        url += "v1beta/models/gemini-1.5-flash-latest:generateContent"
        url += "?key=" + key
        payload = {"contents":[{"parts":[{"text":q}]}]}
        r = http_requests.post(url, json=payload, timeout=20)
        j = r.json()
        if "candidates" in j and j["candidates"]:
            return j["candidates"][0]["content"]["parts"][0]["text"]
    except:
        pass
    return None

def solve_math(prompt):
    try:
        p = prompt.lower()
        p = p.replace("solve","").replace(" ","").strip()
        m = re.match(r"^(\d*\.?\d*)x=(\d*\.?\d*)$", p)
        if m:
            a = float(m.group(1) or "1")
            c = float(m.group(2))
            x = c / a
            out = "Solve: " + prompt + "\n\n"
            out += str(a) + "x = " + str(c) + "\n"
            out += "x = " + str(c) + "/" + str(a) + "\n"
            out += "x = " + str(x)
            return out
        m = re.match(r"^(\d*\.?\d*)=(\d*\.?\d*)x$", p)
        if m:
            c = float(m.group(1))
            a = float(m.group(2
