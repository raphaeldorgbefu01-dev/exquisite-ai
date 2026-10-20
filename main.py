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
    html += "<style>body{background:#0f0f18;color:#fff;padding:20px;font-family:sans-serif}.card{background:#191923;padding:16px;margin:12px 0;border-radius:16px}textarea{width:100%;padding:12px;background:#111;color:#fff;border-radius:12px}button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700}img.res-img{max-width:100%;border-radius:12px;margin-top:12px;display:block}.badge{background:#222;padding:4px 10px;border-radius:20px}</style></head><body>"
    html += "<h2 style=text-align:center>Where Ideas Take Flight</h2>"
    html += "<div class=card><div class=badge id=quota>Free: loading...</div><textarea id=q rows=3>A car</textarea><br><br><button onclick=go()>Let It Take Flight</button><div id=res></div></div>"
    html += "<div class=card><h3>Unlock Unlimited</h3><div id=plans></div></div>"
    html += "<script>let PUB='" + pub + "';let cur='images';"
    html += "async function refresh(){let r=await fetch('/api/me');let d=await r.json();document.getElementById('quota').innerText='Free: '+d.remaining+' left';let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(function(kv){let k=kv[0];let v=kv[1];let b=document.createElement('button');b.innerText=v.label;b.style='margin:4px';b.onclick=function(){pay(k)};p.appendChild(b)})}"
    html += "async function go(){let prompt=document.getElementById('q').value;let r=document.getElementById('res');r.innerText='Thinking...';let res=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt,type:cur})}).then(function(x){return x.json()});r.innerText=res.answer;if(res.image_url){let i=document.createElement('img');i.src=res.image_url;i.className='res-img';r.appendChild(i)}refresh()}"
    html += "async function pay(plan){let init=await fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan:plan})}).then(function(x){return x.json()});let h=PaystackPop.setup({key:PUB,email:init.email,amount:init.kobo,currency:'GHS',ref:init.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(function(x){return x.json()}).then(function(v){alert(v.message);refresh()})}});h.openIframe()}"
    html += "refresh();</script></body></html>"
    resp = make_response(html)
    resp.set_cookie('uid', get_uid(), max_age=86400*365)
    return resp

@app.route('/api/me')
def me():
    data = load_data()
    uid = get_uid()
    u = data.get('users',{}).get(uid,{'used':0})
    left = FREE - u.get('used',0)
    if left < 0:
        left = 0
    plans = {'day':{'label':'Day GHS 10','kobo':1000},'weekly':{'label':'Weekly GHS 49','kobo':4900},'monthly':{'label':'Monthly GHS 99','kobo':9900}}
    return jsonify({'remaining':left,'plans':plans})

@app.route('/api/generate', methods=['POST'])
def generate():
    data = load_data()
    uid = get_uid()
    users = data.setdefault('users',{})
    user = users.setdefault(uid,{'used':0})
    j = request.get_json() or {}
    prompt = j.get('prompt','A car')[:200]
    kw = urllib.parse.quote(prompt)
    safe = urllib.parse.quote(prompt)
    img = 'https://source.unsplash.com/1024x1024/?' + kw
    if POLL and len(POLL) > 5:
        img = 'https://image.pollinations.ai/prompt/' + safe + '?width=1024&height=1024&seed=' + str(int(time.time())) + '&token=' + POLL
    ans = '4K Image for: ' + prompt
    user['used'] = user.get('used',0) + 1
    save_data(data)
    out = {'answer':ans,'image_url':img}
    resp = make_response(jsonify(out))
    resp.set_cookie('uid', uid, max_age=86400*365)
    return resp

@app.route('/api/paystack/init', methods=['POST'])
def pay_init():
    j = request.get_json() or {}
    plan = j.get('plan','day')
    kobo = 1000
    if plan == 'weekly':
        kobo = 4900
    if plan == 'monthly':
        kobo = 9900
    uid = get_uid()
    headers = {'Authorization':'Bearer ' + SEC,'Content-Type':'application/json'}
    payload = {'email':uid+'@exquisite.ai','amount':kobo*100,'currency':'GHS','metadata':{'uid':uid,'plan':plan}}
    r = http_requests.post('https://api.paystack.co/transaction/initialize', json=payload, headers=headers, timeout=15)
    jr = r.json()
    return jsonify({'reference':jr['data']['reference'],'kobo':kobo*100,'email':uid+'@exquisite.ai'})

@app.route('/api/paystack/verify', methods=['POST'])
def pay_verify():
    j = request.get_json() or {}
    ref = j.get('reference')
    headers = {'Authorization':'Bearer ' + SEC}
    r = http_requests.get('https://api.paystack.co/transaction/verify/' + ref, headers=headers, timeout=15)
    jr = r.json()
    meta = jr['data'].get('metadata',{})
    uid = meta.get('uid',get_uid())
    plan = meta.get('plan','day')
    data = load_data()
    users = data.setdefault('users',{})
    user = users.setdefault(uid,{'used':0})
    days = 1
    if plan == 'weekly':
        days = 7
    if plan == 'monthly':
        days = 30
    user['expiry'] = int(time.time()) + days*24*3600
    save_data(data)
    return jsonify({'message':'Premium Activated!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))
