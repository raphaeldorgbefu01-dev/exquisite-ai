import json, os, uuid, time, urllib.parse, re
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
        f = open(DATA_FILE,'r')
        d = json.load(f)
        f.close()
        return d
    except:
        return {'users':{}}

def save_data(d):
    try:
        f = open(DATA_FILE,'w')
        json.dump(d,f)
        f.close()
    except:
        pass

def get_uid():
    u = request.cookies.get('uid')
    if not u:
        u = request.headers.get('X-User-Id')
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

def ask_gemini(q, key):
    if not key:
        return None
    try:
        url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key=' + key
        payload = {'contents':[{'parts':[{'text':q}]}]}
        r = http_requests.post(url, json=payload, timeout=20)
        j = r.json()
        if 'candidates' in j and j['candidates']:
            return j['candidates'][0]['content']['parts'][0]['text']
    except:
        pass
    return None

def solve_math(prompt):
    try:
        p = prompt.lower().replace('solve','').replace(' ','').strip()
        m = re.match(r'^(\d*\.?\d*)x=(\d*\.?\d*)$', p)
        if m:
            a_str = m.group(1)
            if a_str == '':
                a_str = '1'
            a = float(a_str)
            c = float(m.group(2))
            x = c / a
            return 'Solve: ' + prompt + '\n x = ' + str(x)
        m = re.match(r'^(\d*\.?\d*)=(\d*\.?\d*)x$', p)
        if m:
            c = float(m.group(1))
            a_str = m.group(2)
            if a_str == '':
                a_str = '1'
            a = float(a_str)
            x = c / a
            return 'Solve: ' + prompt + '\n x = ' + str(x)
        if re.match(r'^[\d\+\-\*\/\.\(\)]+$', p):
            res = eval(p)
            return p + ' = ' + str(res)
    except:
        pass
    return None

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
button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700;cursor:pointer}
button.hidden{display:none!important}
.tab{padding:8px 14px;border-radius:20px;background:#222;color:#aaa;border:1px solid #444;margin:2px}
.tab.active{background:#bda0ff;color:#111}
#res{white-space:pre-wrap;background:#111;padding:12px;border-radius:12px;margin-top:10px;min-height:60px}
.badge{background:#222;padding:4px 10px;border-radius:20px;font-size:12px;color:#aaa}
img.res-img{max-width:100%;border-radius:12px;margin-top:12px;display:block}
</style></head><body>
<h2 style=text-align:center>Where Ideas Take Flight</h2>
<div style=text-align:center>
<button class=tab active id=t-all onclick=setT('all')>All</button>
<button class=tab id=t-captions onclick=setT('captions')>Captions</button>
<button class=tab id=t-scripts onclick=setT('scripts')>Scripts</button>
<button class=tab id=t-stories onclick=setT('stories')>Stories</button>
<button class=tab id=t-images onclick=setT('images')>Images</button>
</div>
<div class=card>
<div class=badge id=quota>Free: loading...</div>
<textarea id=q rows=3 oninput=onInput()>AI kente fashion Ghana</textarea><br><br>
<button id=flightBtn onclick=go()>Let It Take Flight</button>
<div id=res>Your answer will appear here...</div>
</div>
<div class=card><h3>Unlock Unlimited</h3><div id=plans></div></div>
<script>
let cur='all';
let PUB='__PUB__';
function setT(t){cur=t;document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));document.getElementById('t-'+t).classList.add('active')}
function onInput(){let v=document.getElementById('q').value.trim();let btn=document.getElementById('flightBtn');if(v.length>0){btn.classList.remove('hidden')}else{btn.classList.add('hidden')}}
async function refresh(){let r=await fetch('/api/me');let d=await r.json();let q=document.getElementById('quota');if(d.is_premium){q.innerText='Premium: '+d.plan;}else{q.innerText='Free: '+d.remaining+' left';}let p=document.getElementById('plans');p.innerHTML='';Object.entries(d.plans).forEach(([k,v])=>{let b=document.createElement('button');b.innerText=v.label;b.style='margin:4px';b.onclick=()=>pay(k);p.appendChild(b)})}
async function go(){let p=document.getElementById('q').value.trim();if(!p)return;let r=document.getElementById('res');let btn=document.getElementById('flightBtn');r.innerText='Thinking...';btn.classList.add('hidden');let res=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p,type:cur})}).then(x=>x.json());r.innerText=res.answer;if(res.image_url){let i=document.createElement('img');i.src=res.image_url;i.className='res-img';r.appendChild(i)}refresh()}
async function pay(plan){let init=await fetch('/api/paystack/init',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan:plan})}).then(x=>x.json());if(init.error){alert(init.error);return}let h=PaystackPop.setup({key:PUB,email:init.email,amount:init.kobo,currency:'GHS',ref:init.reference,callback:function(resp){fetch('/api/paystack/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reference:resp.reference})}).then(x=>x.json()).then(v=>{alert(v.message||v.error);refresh()})}});h.openIframe()}
refresh();onInput();
</script></body></html>
'''
    return html.replace('__PUB__', PUB)

@app.route('/')
def index():
    html = get_page()
    uid = get_uid()
    resp = make_response(html)
    resp.set_cookie('uid', uid, max_age=86400*365)
    return resp

@app.route('/<path:path>')
def catch_all(path):
    if path.startswith('api/'):
        return jsonify({'error':'Not found'}), 404
    return index()

@app.route('/api/me')
def me():
    data = load_data()
    uid = get_uid()
    user = get_user(data, uid)
    return jsonify({'remaining': remain(user),'is_premium': is_premium(user),'plan': user.get('plan'),'plans': PLANS})

@app.route('/api/generate', methods=['POST'])
def gen_api():
    data = load_data()
    uid = get_uid()
    user = get_user(data, uid)
    j = request.get_json() or {}
    prompt = (j.get('prompt') or '').strip()
    if not prompt:
        prompt = 'Best business in Ghana'
    if len(prompt) > 2000:
        prompt = prompt[:2000]
    typ = j.get('type') or 'all'
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or ''
    if not is_premium(user) and user.get('used',0) >= FREE:
        return jsonify({'answer': 'Free 25 reached. Upgrade.', 'need_pay': True})
    ans = ''
    img = None
    if typ == 'images':
        seed = int(time.time()) % 999999
        safe = urllib.parse.quote(prompt[:400])
        img = 'https://picsum.photos/seed/' + str(seed) + '/1024/1024'
        if POLL:
            img = 'https://image.pollinations.ai/prompt/' + safe + '?seed=' + str(seed) + '&token=' + POLL + '&nologo=true'
        ans = '4K Image for: ' + prompt[:60]
    else:
        if key:
            g = ask_gemini('Answer: ' + prompt, key)
            if g and len(g) > 5:
                ans = g
        if not ans:
            mm = solve_math(prompt)
            if mm:
                ans = mm
            else:
                ans = 'Answer for: ' + prompt[:100]
    user['used'] = user.get('used',0) + 1
    save_data(data)
    out = {'answer': ans}
    if img:
        out['image_url'] = img
    resp = make_response(jsonify(out))
    resp.set_cookie('uid', uid, max_age=86400*365)
    return resp

@app.route('/api/paystack/init', methods=['POST'])
def pay_init():
    if not SEC:
        return jsonify({'error':'Secret not set'}), 500
    j = request.get_json() or {}
    pk = j.get('plan') or 'day'
    plan = PLANS.get(pk) or PLANS['day']
    uid = get_uid()
    email = uid + '@exquisite.ai'
    headers = {'Authorization': 'Bearer ' + SEC, 'Content-Type': 'application/json'}
    payload = {'email': email, 'amount': plan['kobo']*100, 'currency': 'GHS', 'metadata': {'uid': uid, 'plan': pk}}
    r = http_requests.post('https://api.paystack.co/transaction/initialize', json=payload, headers=headers, timeout=15)
    jr = r.json()
    if not jr.get('status'):
        return jsonify({'error': jr.get('message')}), 400
    return jsonify({'reference': jr['data']['reference'],'kobo': plan['kobo']*100,'email': email})

@app.route('/api/paystack/verify', methods=['POST'])
def pay_verify():
    if not SEC:
        return jsonify({'error':'Secret not set'}), 500
    j = request.get_json() or {}
    ref = j.get('reference')
    if not ref:
        return jsonify({'error':'No ref'}), 400
    headers = {'Authorization': 'Bearer ' + SEC}
    r = http_requests.get('https://api.paystack.co/transaction/verify/' + ref, headers=headers, timeout=15)
    jr = r.json()
    if not jr.get('status'):
        return jsonify({'error':'Verify failed'}), 400
    if jr['data']['status'] != 'success':
        return jsonify({'error':'Not success'}), 400
    meta = jr['data'].get('metadata',{})
    uid = meta.get('uid') or get_uid()
    pk = meta.get('plan') or 'day'
    data = load_data()
    user = get_user(data, uid)
    plan = PLANS.get(pk) or PLANS['day']
    user['plan'] = pk
    user['expiry'] = int(time.time()) + plan['days']*24*3600
    save_data(data)
    return jsonify({'message': 'Premium Activated! ' + plan['label']})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)))
