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
    html += "<style>body{background:#0f0f18;color:#fff;padding:20px;font-family:sans-serif}.card{background:#191923;padding:16px;margin:12px 0;border-radius:16px}textarea{width:100%;padding:12px;background:#111;color:#fff;border-radius:12px;border:1px solid #333}button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700;margin:3px}button.tab{background:#222;color:#aaa;border:1px solid #444;border-radius:20px}button.tab.active{background:#bda0ff;color:#111}img.res-img{max-width:100%;border-radius:12px;margin-top:12px;display:block}.badge{background:#222;padding:4px 10px;border-radius:20px;font-size:13px}</style></head><body>"
    html += "<h2 style=text-align:center>Where Ideas Take Flight</h2>"
    html += "<div style=text-align:center><button class=tab active id=t-all onclick=setT('all')>All</button><button class=tab id=t-captions onclick=setT('captions')>Captions</button><button class=tab id=t-scripts onclick=setT('scripts')>Scripts</button><button class=tab id=t-stories onclick=setT('stories')>Stories</button><button class=tab id=t-images onclick=setT('images')>Images</button></div>"
    html += "<div class=card><div class=badge id=quota>Free: loading...</div><textarea id=q rows=3>A car</textarea><br><br><button onclick=go()>Let It Take Flight</button><div id=res>Your result...</div></div>"
    html += "<div class=card><h3>Unlock Unlimited</h3><div id=plans></div></div>"
    html += "<script>let PUB='" + pub + "';let cur='all';"
    html += "function setT(t){cur=t;document.querySelectorAll('.tab').forEach(function(b){b.classList.remove('active')});document.getElementById('t-'+t).classList.add('active')}"
    html += "async function refresh(){let r=await fetch('/api/me');let d=await r.json();document.getElementById('quota').innerText=d.is_premium?'Premium: '+d.plan:'Free: '+d.remaining+' left';let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(function(kv){let k=kv[0];let v=kv[1];let b=document.createElement('button');b.innerText=v.label;b.onclick=function(){pay(k)};p.appendChild(b)})}"
    html += "async function go(){let pr=document.getElementById('q').value.trim();if(!pr)return;let r=document.getElementById('res');r.innerText='Thinking...';let res=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:pr,type:cur})}).then(function(x){return x.json()});r.innerText=res.answer;if(res.image_url){let i=document.createElement('img');i.src=res.image_url;i.className='res-img';i.onerror=function(){this.src='https://picsum.photos/seed/'+Date.now()+'/1024/1024'};r.appendChild(i)}refresh()}"
    html += "async function pay(plan){let init=await fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan:plan})}).then(function(x){return x.json()});if(init.error){alert(init.error);return}let h=PaystackPop.setup({key:PUB,email:init.email,amount:init.kobo,currency:'GHS',ref:init.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(function(x){return x.json()}).then(function(v){alert(v.message||v.error);refresh()})}});h.openIframe()}"
    html += "refresh();</script></body></html>"
    resp = make_response(html)
    resp.set_cookie('uid', get_uid(), max_age=86400*365)
    return resp

@app.route('/api/me')
def me():
    data = load_data()
    uid = get_uid()
    u = data.get('users',{}).get(uid,{'used':0,'expiry':0})
    left = FREE - u.get('used',0)
    if left < 0:
        left = 0
    plans = {'day':{'label':'Day GHS 10','kobo':1000},'weekly':{'label':'Weekly GHS 49','kobo':4900},'monthly':{'label':'Monthly GHS 99','kobo':9900}}
    prem = u.get('expiry',0) > time.time()
    return jsonify({'remaining':left,'is_premium':prem,'plan':u.get('plan'),'plans':plans})

@app.route('/api/generate', methods=['POST'])
def generate():
    data = load_data()
    uid = get_uid()
    users = data.setdefault('users',{})
    user = users.setdefault(uid,{'used':0,'expiry':0})
    j = request.get_json() or {}
    prompt = j.get('prompt','A car')[:400]
    typ = j.get('type','all')
    safe = urllib.parse.quote(prompt)
    img = None
    if typ == 'images':
        # REAL AI IMAGE - works without token, unlimited
        if POLL and len(POLL) > 5:
            img = 'https://image.pollinations.ai/prompt/' + safe + '?width=1024&height=1024&seed=' + str(int(time.time())) + '&token=' + POLL + '&nologo=true&enhance=true'
        else:
            img = 'https://image.pollinations.ai/prompt/' + safe + '?width=1024&height=1024&seed=' + str(int(time.time())) + '&nologo=true'
        ans = '4K Image for: ' + prompt
    else:
        ans = 'Mode [' + typ + '] Answer: ' + prompt[:200]
    user['used'] = user.get('used',0) + 1
    save_data(data)
    out = {'answer':ans}
    if img:
        out['image_url'] = img
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
    user['plan'] = plan
    save_data(data)
    return jsonify({'message':'Premium Activated!'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))
