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
    html += "<style>"
    html += "body{background:#0f0f18;color:#fff;padding:20px;font-family:sans-serif}.card{background:#191923;padding:16px;margin:12px 0;border-radius:16px}"
    html += "textarea{width:100%;padding:12px;background:#111;color:#fff;border-radius:12px;border:1px solid #333}"
    html += "button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700;margin:3px;cursor:pointer}"
    html += "button.tab{background:#222;color:#aaa;border:1px solid #444;border-radius:20px}button.tab.active{background:#bda0ff;color:#111}button.hidden{display:none!important}"
    html += "img.res-img{max-width:100%;border-radius:12px;margin-top:12px;display:block}"
    html += ".badge{background:#222;padding:4px 10px;border-radius:20px;font-size:13px}#res{white-space:pre-wrap;background:#111;padding:12px;border-radius:12px;margin-top:10px;min-height:50px}"
    html += ".pending{display:flex;align-items:center;gap:10px;color:#bda0ff}.spinner{width:18px;height:18px;border:3px solid #333;border-top:3px solid #bda0ff;border-radius:50%;animation:spin 0.8s linear infinite}"
    html += "@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}"
    html += ".dots span{animation:blink 1.4s infinite both}.dots span:nth-child(2){animation-delay:.2s}.dots span:nth-child(3){animation-delay:.4s}@keyframes blink{0%{opacity:.2}20%{opacity:1}100%{opacity:.2}}"
    html += ".cursor{display:inline-block;width:8px;background:#bda0ff;margin-left:2px;animation:cursorBlink 0.8s infinite}@keyframes cursorBlink{0%,50%{opacity:1}51%,100%{opacity:0}}"
    html += "</style></head><body>"
    html += "<h2 style=text-align:center>Where Ideas Take Flight</h2>"
    html += "<div style=text-align:center><button class=tab active id=t-all onclick=setT('all')>All</button><button class=tab id=t-captions onclick=setT('captions')>Captions</button><button class=tab id=t-scripts onclick=setT('scripts')>Scripts</button><button class=tab id=t-stories onclick=setT('stories')>Stories</button><button class=tab id=t-images onclick=setT('images')>Images</button></div>"
    html += "<div class=card><div class=badge id=quota>Free: loading...</div><textarea id=q rows=3 placeholder='Type something...' oninput=onInput()>A car</textarea><br><br><button id=flightBtn class=hidden onclick=go()>Let It Take Flight</button><div id=res></div></div>"
    html += "<div class=card><h3>Unlock Unlimited</h3><div id=plans></div></div>"
    html += "<script>let PUB='" + pub + "';let cur='all';let isSearching=false;"
    html += "function setT(t){cur=t;document.querySelectorAll('.tab').forEach(function(b){b.classList.remove('active')});document.getElementById('t-'+t).classList.add('active');onInput()}"
    html += "function onInput(){let txt=document.getElementById('q').value.trim();let btn=document.getElementById('flightBtn');if(isSearching){btn.classList.add('hidden');return}if(txt.length>0){btn.classList.remove('hidden')}else{btn.classList.add('hidden')}}"
    html += "function showPending(){let r=document.getElementById('res');r.innerHTML=\"<div class='pending'><div class='spinner'></div><div>Generating<span class='dots'><span>.</span><span>.</span><span>.</span></span></div></div>\"}"
    html += "function typeWriter(text,imgUrl){let r=document.getElementById('res');r.innerHTML=\"<span id='typed'></span><span id='cursor' class='cursor'>&nbsp;</span>\";let typed=document.getElementById('typed');let cursor=document.getElementById('cursor');let i=0;let interval=setInterval(function(){if
