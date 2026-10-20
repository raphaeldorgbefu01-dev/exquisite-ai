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
    h = ""
    h += "<!doctype html><html><head>"
    h += "<meta charset=utf-8>"
    h += "<meta name=viewport content="
    h += "'width=device-width,initial-scale=1'>"
    h += "<title>Exquisite AI</title>"
    h += "<script src=https://js.paystack.co/v1/inline.js>"
    h += "</script>"
    h += "<style>"
    h += "body{background:#0f0f18;color:#fff;"
    h += "padding:20px;font-family:sans-serif}"
    h += ".card{background:#191923;padding:16px;"
    h += "margin:12px 0;border-radius:16px}"
    h += "textarea{width:100%;padding:12px;"
    h += "background:#111;color:#fff;"
    h += "border-radius:12px;border:1px solid #333}"
    h += "button{background:#bda0ff;color:#111;"
    h += "border:0;padding:10px 16px;"
    h += "border-radius:10px;font-weight:700;margin:3px}"
    h += "button.tab{background:#222;color:#aaa;"
    h += "border:1px solid #444;border-radius:20px}"
    h += "button.tab.active{background:#bda0ff;color:#111}"
    h += "button.hidden{display:none!important}"
    h += "img.res-img{max-width:100%;border-radius:12px;"
    h += "margin-top:12px;display:block}"
    h += ".badge{background:#222;padding:4px 10px;"
    h += "border-radius:20px;font-size:13px}"
    h += "#res{white-space:pre-wrap;background:#111;"
    h += "padding:12px;border-radius:12px;"
    h += "margin-top:10px;min-height:50px}"
    h += ".pending{display:flex;align-items:center;"
    h += "gap:10px;color:#bda0ff}"
    h += ".spinner{width:18px;height:18px;"
    h += "border:3px solid #333;"
    h += "border-top:3px solid #bda0ff;"
    h += "border-radius:50%;"
    h += "animation:spin 0.8s linear infinite}"
    h += "@keyframes spin{0%{transform:rotate(0deg)}"
    h += "100%{transform:rotate(360deg)}}"
    h += ".dots span{animation:blink 1.4s infinite both}"
    h += "@keyframes blink{0%{opacity:.2}"
    h += "20%{opacity:1}100%{opacity:.2}}"
    h += ".cursor{display:inline-block;width:8px;"
    h += "background:#bda0ff;margin-left:2px;"
    h += "animation:cb 0.8s infinite}"
    h += "@keyframes cb{0%,50%{opacity:1}"
    h += "51%,100%{opacity:0}}"
    h += "</style></head><body>"
    h += "<h2 style=text-align:center>"
    h += "Where Ideas Take Flight</h2>"
    h += "<div style=text-align:center>"
    h += "<button class=tab active id=t-all "
    h += "onclick=setT('all')>All</button>"
    h += "<button class=tab id=t-captions "
    h += "onclick=setT('captions')>Captions</button>"
    h += "<button class=tab id=t-scripts "
    h += "onclick=setT('scripts')>Scripts</button>"
    h += "<button class=tab id=t-stories "
    h += "onclick=setT('stories')>Stories</button>"
    h += "<button class=tab id=t-images "
    h += "onclick=setT('images')>Images</button>"
    h += "</div>"
    h += "<div class=card>"
    h += "<div class=badge id=quota>Loading...</div>"
    h += "<textarea id=q rows=3 "
    h += "placeholder='Type...' oninput=onInput()>A car</textarea>"
    h += "<br><br>"
    h += "<button id=flightBtn class=hidden "
    h += "onclick=go()>Let It Take Flight</button>"
    h += "<div id=res></div></div>"
    h += "<div class=card><h3>Unlock Unlimited</h3>"
    h += "<div id=plans></div></div>"
    h += "<script>"
    h += "let PUB='" + pub + "';"
