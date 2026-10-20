import json, os, uuid, time, urllib.parse
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
PUB = os.environ.get('PAYSTACK_PUBLIC_KEY','')
SEC = os.environ.get('PAYSTACK_SECRET_KEY','')
POLL = os.environ.get('POLLINATIONS_TOKEN','')
FREE = 25

def load_data():
    try:
        return json.load(open('data.json','r'))
    except:
        return {'users':{}}

def save_data(d):
    try:
        json.dump(d, open('data.json','w'))
    except:
        pass

def get_uid():
    u = request.cookies.get('uid')
    if not u:
        u = str(uuid.uuid4())
    return u

@app.route('/')
def index():
    pub = PUB
    html = "<!doctype html><html><head><meta charset=utf-8>"
    html += "<meta name=viewport content='width=device-width,initial-scale=1'><title>Exquisite AI</title>"
    html += "<script src=https://js.paystack.co/v1/inline.js></script>"
    html += "<style>body{background:#0f0f18;color:#fff;padding:20px;font-family:sans-serif}.card{background:#191923;padding:16px;margin:12px 0;border-radius:16px}textarea{width:100%;padding:12px;background:#111;color:#fff;border-radius:12px;border:1px solid #333}button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700;margin:3px;cursor:pointer}button.tab{background:#222;color:#aaa;border:1px solid #444;border-radius:20px}button.tab.active{background:#bda0ff;color:#111}button.hidden{display:none!important}img.res-img{max-width:100%;border-radius:12px;margin-top:12px;display:block}.badge{background:#222;padding:4px 10px;border-radius:20px;font-size:13px}#res{white-space:pre-wrap;background:#111;padding:12px;border-radius:12px;margin-top:10px;min-height:50px}.pending{display:flex;align-items:center;gap:10px;color:#bda0ff}.spinner{width:18px;height:18px;border:3px solid #333;border-top:3px solid #bda0ff;border-radius:50%;animation:spin 0.8s linear infinite}@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}.dots span{animation:blink 1.4s infinite both}.dots span:nth-child(2){animation-delay:.2s}.dots span:nth-child(3){animation-delay:.4s}@keyframes blink{0%{opacity:.2}20%{opacity:1}100%{opacity:.2}}.cursor{display:inline-block;width:8px;background:#bda0ff;margin-left:2px;animation:cb 0.8s infinite}@keyframes cb{0%,50%{opacity:1}51%,100%{opacity:0}}</style></head><body>"
    html += "<h2 style=text-align:center>Where Ideas Take Flight</h2>"
    html += "<div style=text-align:center><button class=tab active id=t-all onclick=setT('all')>All</button><button class=tab id=t-captions onclick=setT('captions')>Captions</button><button class=tab id=t-scripts onclick
