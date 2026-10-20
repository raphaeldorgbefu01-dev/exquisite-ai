import json, os, uuid, time, urllib.parse
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
DATA_FILE = 'data.json'
FREE = 25
PUB = os.environ.get('PAYSTACK_PUBLIC_KEY','')
SEC = os.environ.get('PAYSTACK_SECRET_KEY','')
POLL = os.environ.get('POLLINATIONS_TOKEN','')

def load_data():
    try:
        return json.load(open(DATA_FILE,'r'))
    except:
        return {'users':{}}

def save_data(d):
    try:
        json.dump(d, open(DATA_FILE,'w'))
    except:
        pass

def get_uid():
    u = request.cookies.get('uid') or request.headers.get('X-User-Id')
    if not u:
        u = str(uuid.uuid4())
    return u

def get_user(data, uid):
    users = data.setdefault('users',{})
    if uid not in users:
        users[uid] = {'used':0,'expiry':0,'plan':None}
    return users[uid]

def is_premium(u):
    return u.get('expiry',0) > time.time()

def remain(u):
    if is_premium(u):
        return 9999
    left = FREE - u.get('used',0)
    if left < 0:
        left = 0
    return left

PLANS = {
    'day':{'label':'Day GHS 10','kobo':1000,'days':1},
    'weekly':{'label':'Weekly GHS 49','kobo':4900,'days':7},
    'monthly':{'label':'Monthly GHS 99','kobo':9900,'days':30}
}

def get_page():
    html = '''
<!doctype html><html><head>
<meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'>
<title>Exquisite AI</title>
<script src=https://js.paystack.co/v1/inline.js></script>
<style>
body{background:#0f0f18;color:#fff;padding:20px;font-family:sans-serif}
.card{background:#191923;padding:16px;margin:12px 0;border-radius:16px}
textarea{width:100%;padding:12px;background:#111;color:#fff;border-radius:12px;border:1px solid #333}
button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700}
.tab{padding:8px 14px;border-radius:20px;background:#222;color:#aaa;border:1px solid #444;margin:2px}
.tab.active{background:#bda0ff;color:#111}
#res{white-space:pre-wrap;background:#111;padding:12px;border-radius:12px;margin-top:10px;min-height:60px}
.badge{background:#222;padding:4px 10px;border-radius:20px;font-size:12px}
img.res-img{max-width:100%;border-radius:12px;margin-top:12px;display:block}
</style></head><body>
<h2 style=text-align:center>Where Ideas Take Flight</h2>
<div style=text-align:center>
<button class=tab id=t-all onclick=setT('all')>All</button>
<button class=tab id=t-images onclick=setT('images')>Images</button>
</div>
<div class=card>
<div class=badge id=quota>Free: loading...</div>
<textarea id=q rows=3>A car</textarea><br><br>
<button id=flightBtn onclick=go()>Let It Take Flight</button>
<div id=res>Your answer...</div>
</div>
<div class=card><h3>Unlock Unlimited</h3><div id=plans></div></div>
<script>
let cur='all';
let PUB='__PUB__';
function setT(t){cur=t;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('t-'+t).classList.add('active')}
async function refresh(){let r=await fetch('/api/me');let d=await r.json();document.getElementById('quota').innerText=d.is_premium?'Premium: '+d.plan:'Free: '+d.remaining+' left';let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(([k,v])=>{let b=document.createElement('button');b.innerText=v.label;b.style='margin:4px';b.onclick=()=>pay(k);p.appendChild(b)})}
async function go(){let p=document.getElementById('q').value.trim();if(!p)return;let r=document.getElementById('res');r.innerText='Thinking...';
