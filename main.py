import json
import logging
import os
import uuid
import time
from datetime import datetime
from urllib.parse import quote
from urllib.request import Request, urlopen
from flask import Flask, Response, jsonify, render_template_string, request, make_response, redirect, send_from_directory
import requests as http_requests

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
logging.basicConfig(level=logging.INFO)

MODEL = "gemini-3.8-flash"
FREE_USES = 25
DATA_FILE = "exquisite_data.json"
UPLOAD_DIR = "uploads"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Shatta2025!")

# === SAFE - NO HARDCODED SECRETS - USE ENV VARIABLES ===
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")
# For local testing you can set env, but never commit real keys!

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

RESULT_SCHEMA = {"type":"OBJECT","properties":{"answer":{"type":"STRING"},"image_prompt":{"type":"STRING"},"caption":{"type":"STRING"},"hashtags":{"type":"ARRAY","items":{"type":"STRING"}}},"required":["answer","image_prompt","caption","hashtags"]}

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
    "monthly": {"label":"Monthly","price":99,"days":30,"tag":"30 days - BEST VALUE","kobo":9900},
}

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite AI</title><script src="https://js.paystack.co/v1/inline.js"></script>
<style>:root{color-scheme:dark;--bg:#101018;--panel:#191923;--line:rgba(255,255,255,.1);--text:#f5f2fa;--muted:#a4a1b2;--violet:#bda0ff;--mint:#a8f0d5;font-family:Inter,system-ui,sans-serif}*{box-sizing:border-box}body{min-height:100vh;margin:0;color:var(--text);background:var(--bg)}.shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0 72px}header{display:flex;justify-content:space-between;align-items:center}.brand{display:flex;align-items:center;gap:12px;font-weight:700}.brand-mark{display:grid;place-items:center;width:36px;height:36px;border-radius:12px;background:linear-gradient(140deg,var(--violet),var(--mint));color:#17121f;font-weight:900}.service-tag{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}.hero{max-width:730px;margin:72px auto 34px;text-align:center}.eyebrow{color:var(--mint);font-size:12px;font-weight:750;letter-spacing:.18em;text-transform:uppercase}
