import json
import logging
import os
import uuid
import time
import base64
from datetime import datetime
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from flask import Flask, Response, jsonify, render_template_string, request, make_response, redirect

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

MODEL = "gemini-1.5-flash"
MAX_QUESTION_LENGTH = 4_000
MODEL = "gemini-2.5-flash"
FREE_USES = 25
DATA_FILE = "exquisite_data.json"
UPLOAD_DIR = "uploads"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Shatta2025!")

os.makedirs(UPLOAD_DIR, exist_ok=True)

RESULT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answer": {"type": "STRING"},
        "image_prompt": {"type": "STRING"},
        "caption": {"type": "STRING"},
        "hashtags": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["answer", "image_prompt", "caption", "hashtags"],
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "payments": []}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "payments": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user_id():
    uid = request.cookies.get("exquisite_uid") or request.headers.get("X-User-Id") or request.form.get("uid")
    if not uid:
        uid = str(uuid.uuid4())
    return uid

def get_user_record(data, uid):
    users = data.setdefault("users", {})
    if uid not in users:
        users[uid] = {"free_used": 0, "expiry": 0, "plan": None, "created": int(time.time())}
    return users[uid]

def is_premium(user):
    return user.get("expiry", 0) > time.time()

def remaining_free(user):
    if is_premium(user):
        return 9999
    return max(0, FREE_USES - user.get("free_used", 0))

PLANS = {
    "day": {"label": "Day", "price": 10, "days": 1, "tag": "24 hours"},
    "weekly": {"label": "Weekly", "price": 49, "days": 7, "tag": "7 days - POPULAR"},
    "monthly": {"label": "Monthly", "price": 99, "days": 30, "tag": "30 days - BEST VALUE"},
}

PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Exquisite AI</title>
  <style>
    :root {color-scheme: dark; --bg: #101018; --panel: #191923; --line: rgba(255,255,255,.1); --text: #f5f2fa; --muted: #a4a1b2; --violet: #bda0ff; --mint: #a8f0d5; font-family: Inter, system-ui, sans-serif;}
    *{box-sizing:border-box} body{min-height:100vh;margin:0;color:var(--text);background:var(--bg)}
   .shell{width:min(1050px,calc(100% - 40px));margin:0 auto;padding:26px 0 72px}
    header{display:flex;justify-content:space-between;align-items:center}
   .brand{display:flex;align-items:center;gap:12px;font-weight:700}
   .brand-mark{display:grid;place-items:center;width:36px;height:36px;border-radius:12px;background:linear-gradient(140deg,var(--violet),var(--mint));color:#17121f;font-weight:900}
   .service-tag{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);font-size:12px}
   .hero{max-width:730px;margin:72px auto 34px;text-align:center}
   .eyebrow{color:var(--mint);font-size:12px;font-weight:750;letter-spacing:.18em;text-transform:uppercase}
    h1{margin:14px 0 13px;font-size:clamp(42px,7vw,72px);line-height:.99;letter-spacing:-.065em}
    h1 span{color:transparent;background:linear-gradient(105deg,#d2bbff 6%,#a9e8d5 91%);background-clip:text;-webkit-background-clip:text}
   .hero p{max-width:540px;margin:0 auto;color:var(--muted);font-size:16px;line-height:1.7}
   .composer,.output-card{border:1px solid var(--line);border-radius:20px;background:rgba(25,25,35,.88)}
   .composer{padding:18px}.composer-label{display:flex;justify-content:space-between;margin:2px 2px 12px}.counter{color:var(--muted);font-size:12px}
    textarea{width:100%;min-height:126px;border:1px solid transparent;border-radius:14px;padding:17px 18px;color:var(--text);background:#111119;font-size:15px;line-height:1.65;outline:none}
   .compose-footer{display:flex;justify-content:space-between;align-items:center;margin-top:14px;flex-wrap:wrap;gap:10px}.hint{color:var(--muted);font-size:12px}
   .primary{display:inline-flex;justify-content:center;align-items:center;min-height:44px;border:0;border-radius:12px;padding:0 18px;color:#181321;background:linear-gradient(110deg,#d1bbff,#a8f0d5);font-weight:760;cursor:pointer}
   .primary:disabled{opacity:.6}
   .results{display:grid;grid-template-columns:1.08fr .92fr;gap:16px;margin-top:18px}.output-card{padding:20px}
   .card-heading{display:flex;align-items:center;gap:10px;margin-bottom:15px}.icon{display:grid;place-items:center;width:32px;height:32px;border-radius:10px;color:var(--violet);background:rgba(189,160,255,.11)}
   .answer,.caption-text{margin:0;color:#dedbe7;font-size:14px;line-height:1.8;white-space:pre-wrap}.caption-text{font-size:16px}
   .hashtags{display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}.hashtag{padding:6px 9px;border:1px solid rgba(168,240,213,.19);border-radius:999px;color:var(--mint);background:rgba(168,240,213,.06);font-size:12px}
   .visual-card{grid-column:1 / -1}.visual-wrap{display:grid;place-items:center;min-height:250px;overflow:hidden;border:1px dashed rgba(255,255,255,.14);border-radius:15px;background:#111119}
   .visual-placeholder{max-width:380px;padding:28px;color:var(--muted);font-size:13px;text-align:center}.visual-wrap img{width:100%;max-height:640px;object-fit:contain}
   .quiet-button{display:inline-flex;align-items:center;min-height:34px;border:1px solid var(--line);border-radius:10px;padding:0 11px;color:#cecad8;background:transparent;font-size:12px;cursor:pointer;text-decoration:none}
   .toast{position:fixed;right:22px;bottom:22px;z-index:20;padding:12px 15px;border:1px solid var(--line);border-radius:12px;background:#24232e;opacity:0;transition:.2s;pointer-events:none}.toast.show{opacity:1}
    footer{margin-top:26px;color:#777486;font-size:11px;text-align:center} [hidden]{display:none!important} @media(max-width:690px){.results{grid-template-columns:1fr}.visual-card{grid-column:auto}}
    .paywall{position:fixed;inset:0;z-index:50;display:none;place-items:center;padding:20px;background:rgba(10,10,14,.85);backdrop-filter:blur(14px);overflow:auto}
    .paywall.show{display:grid}
    .paywall-card{width:min(620px,100%);border:1px solid var(--line);border-radius:22px;background:#191923;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.6);margin:auto}
    .paywall-card h2{margin:0 0 8px;font-size:28px;letter-spacing:-.04em}
    .paywall-card p{margin:0;color:var(--muted);line-height:1.6;font-size:14px}
    .plans{display:grid;gap:10px;margin:18px 0}
    .plan{border:1px solid var(--line);border-radius:14px;padding:14px 16px;display:flex;justify-content:space-between;align-items:center;background:#13131b;cursor:pointer}
    .plan.active{border-color:var(--violet);background:rgba(189,160,255,.12)}
    .plan b{font-size:16px}.plan span{font-size:12px;color:var(--muted)}
    .momo-box{border:1px dashed rgba(168,240,213,.35);border-radius:14px;padding:14px;background:rgba(168,240,213,.06);margin:14px 0}
    .momo-box strong{color:var(--mint)} .momo-line{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:8px;flex-wrap:wrap}
    .wa-btn{display:inline-flex;align-items:center;gap:8px;min-height:44px;padding:0 16px;border-radius:12px;background:#25D366;color:#0a2016;font-weight:750;text-decoration:none;border:0}
    .field{width:100%;border:1px solid var(--line);border-radius:10px;background:#111119;color:var(--text);padding:12px 14px;font-size:14px;margin-top:8px}
    .field:focus{outline:none;border-color:var(--violet)}
    .form-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:520px){.form-grid{grid-template-columns:1fr}}
    .divider{height:1px;background:var(--line);margin:16px 0}
  </style>
</head>
<body>
  <main class="shell">
    <header><div class="brand"><span class="brand-mark">✳</span> Exquisite AI</div><div class="service-tag" id="service-status">Checking AI…</div></header>
    <section class="hero"><div class="eyebrow">Your idea, in three directions</div><h1>Ask anything.<br><span>Make something.</span></h1><p>Get a thoughtful answer, a visual direction, and a TikTok caption. <span id="uses-info" style="color:var(--mint)"></span></p></section>
    <form class="composer" id="prompt-form">
      <div class="composer-label"><label for="question">What’s on your mind?</label><span class="counter" id="counter">0 / 4000</span></div>
      <textarea id="question" maxlength="4000" required placeholder="Ask a question or describe an idea…"></textarea>
      <div class="compose-footer"><span class="hint">A good question can become a whole new idea.</span><button class="primary" id="submit-button" type="submit"><span id="submit-label">Create with AI</span> ↗</button></div>
    </form>
    <section class="results" id="results" hidden>
      <article class="output-card"><div class="card-heading"><span class="icon">✦</span><h2>Your answer</h2></div><p class="answer" id="answer"></p><div style="display:flex;justify-content:flex-end;margin-top:18px"><button class="quiet-button" data-copy="answer">Copy answer</button></div></article>
      <article class="output-card"><div class="card-heading"><span class="icon">↗</span><h2>TikTok caption</h2></div><p class="caption-text" id="caption"></p><div class="hashtags" id="hashtags"></div><div style="display:flex;justify-content:flex-end;margin-top:18px"><button class="quiet-button" data-copy="caption">Copy caption</button></div></article>
      <article class="output-card visual-card"><div class="card-heading"><span class="icon">◈</span><h2>Your visual</h2></div><div class="visual-wrap" id="visual"><div class="visual-placeholder"><strong>Your image will appear here</strong>We’re turning your idea into a visual.</div></div><div id="image-actions" hidden><a class="quiet-button" id="download-image" download="exquisite-ai-image.png" href="#">Download image</a></div></article>
    </section>
    <footer>AI-generated. Review before relying. · <span id="expiry-info"></span></footer>
  </main>

  <div class="paywall" id="paywall">
    <div class="paywall-card">
      <h2>🔒 Free limit reached</h2>
      <p>You've used your <b>25 free generations</b>. Subscribe to continue.</p>
      <div class="plans" id="plans"></div>
      <div class="momo-box">
        <div><strong>MoMo Payment Details</strong></div>
        <div class="momo-line"><span>Number: <strong>0533041233</strong> — Michael Asante</span> <button type="button" class="quiet-button" onclick="navigator.clipboard.writeText('0533041233'); notify('Number copied')">Copy</button></div>
        <div style="margin-top:10px;font-size:12px;color:var(--muted)">Selected: <span id="selected-plan-text" style="color:var(--text);font-weight:700"></span></div>
        <div class="divider"></div>
        <div><strong>Step 1: Pay via MoMo</strong><br><span style="font-size:12px;color:var(--muted)">Dial *170# → Send money to 0533041233</span></div>
        <div class="divider"></div>
        <div><strong>Step 2: Confirm Payment</strong></div>
        <div style="margin-top:10px;display:grid;gap:10px">
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <a id="wa-link" class="wa-btn" target="_blank" href="#">WhatsApp Screenshot →</a>
            <span style="font-size:12px;color:var(--muted);align-self:center">Fastest - includes your ID</span>
          </div>
          <div class="divider"></div>
          <form id="payment-form" enctype="multipart/form-data">
            <div style="font-size:13px;color:var(--text);font-weight:600">Or submit here in-app:</div>
            <div class="form-grid">
              <input class="field" id="payer-phone" required placeholder="Your MoMo number (e.g. 055...)" />
              <input class="field" id="trans-id" required placeholder="Transaction ID" />
            </div>
            <input class="field" id="payer-name" placeholder="MoMo name (optional)" />
            <input class="field" type="file" id="screenshot-file" accept="image/*" />
            <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
              <button class="primary" type="submit" id="pay-submit">Submit Payment Proof</button>
              <span id="pay-status" style="font-size:12px;color:var(--muted);align-self:center"></span>
            </div>
            <div style="margin-top:8px;font-size:11px;color:var(--mint)">Confirm payment by sending a screenshot.</div>
          </form>
        </div>
      </div>
      <div style="margin-top:8px;display:flex;justify-content:space-between"><button class="quiet-button" onclick="document.getElementById('paywall').classList.remove('show')">I’ll do later</button><span style="font-size:11px;color:var(--muted)">Your ID: <span id="uid-display"></span></span></div>
    </div>
  </div>
  <div class="toast" id="toast"></div>
  <script>
    const form=document.getElementById("prompt-form"),question=document.getElementById("question"),counter=document.getElementById("counter"),submitButton=document.getElementById("submit-button"),submitLabel=document.getElementById("submit-label"),results=document.getElementById("results"),toast=document.getElementById("toast"),serviceStatus=document.getElementById("service-status");let currentCaption="",imageObjectUrl=null,toastTimer,selectedPlan="weekly";
    const PLANS_DATA = {"day":{"label":"Day","price":10,"days":1,"tag":"24 hours"},"weekly":{"label":"Weekly","price":49,"days":7,"tag":"7 days - POPULAR"},"monthly":{"label":"Monthly","price":99,"days":30,"tag":"30 days - BEST VALUE"}};
    function getUid(){let uid=localStorage.getItem("exquisite_uid");if(!uid){uid=crypto.randomUUID();localStorage.setItem("exquisite_uid",uid);}return uid;}
    const UID=getUid();
    document.cookie=`exquisite_uid=${UID}; path=/; max-age=31536000`;
    document.getElementById("uid-display").textContent=UID;
    async function checkServices(){try{const r=await fetch("/health",{headers:{"X-User-Id":UID}}),s=await r.json();serviceStatus.textContent=(s.gemini_configured?"Gemini ready":"Gemini key missing")+" · Images on";const info=document.getElementById("uses-info");if(s.is_premium){info.textContent=`• Premium until ${s.expiry_str}`;document.getElementById("expiry-info").textContent=`Premium active until ${s.expiry_str}`;}else{info.textContent=`• ${s.free_remaining} / 25 free left`;document.getElementById("expiry-info").textContent=`${s.free_remaining} free generations remaining`; if(s.free_remaining<=0) showPaywall();}}catch{serviceStatus.textContent="Status unavailable"}}
    void checkServices();
    question.addEventListener("input",()=>{counter.textContent=`${question.value.length} / 4000`});
    function notify(m){toast.textContent=m;toast.classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove("show"),2800)}
    function showImageMessage(m){const v=document.getElementById("visual");v.innerHTML=`<div class="visual-placeholder">${m}</div>`;document.getElementById("image-actions").hidden=true}
    function renderPlans(){const c=document.getElementById("plans");c.innerHTML="";for(const [k,p] of Object.entries(PLANS_DATA)){const d=document.createElement("div");d.className="plan"+(k===selectedPlan?" active":"");d.innerHTML=`<div><b>${p.label} — GHS ${p.price}</b><br><span>${p.tag}</span></div><span>→</span>`;d.onclick=()=>{selectedPlan=k;renderPlans();updateWaLink();};c.appendChild(d);}updateWaLink();}
    function updateWaLink(){const p=PLANS_DATA[selectedPlan];document.getElementById("selected-plan-text").textContent=`${p.label} - GHS ${p.price} / ${p.tag}`;const msg=encodeURIComponent(`Hi Michael, I paid GHS ${p.price} for Exquisite AI ${p.label} plan.\nMy ID: ${UID}\nPlan: ${selectedPlan}\nPhone: [my number]\nTrans ID: [ID]\n\nI have attached the screenshot.`);document.getElementById("wa-link").href=`https://wa.me/233533041233?text=${msg}`;}
    function showPaywall(){renderPlans();document.getElementById("paywall").classList.add("show");}
    async function generateImage(prompt){showImageMessage("Creating your image...");const visual=document.getElementById("visual");try{const r=await fetch("/api/image",{method:"POST",headers:{"Content-Type":"application/json","X-User-Id":UID},body:JSON.stringify({prompt})});if(!r.ok){const d=await r.json().catch(()=>({}));throw new Error(d.error||"Image failed")}const blob=await r.blob();if(imageObjectUrl)URL.revokeObjectURL(imageObjectUrl);imageObjectUrl=URL.createObjectURL(blob);const img=document.createElement("img");img.src=imageObjectUrl;visual.replaceChildren(img);document.getElementById("download-image").href=imageObjectUrl;document.getElementById("image-actions").hidden=false}catch(e){showImageMessage(e.message)}}
    form.addEventListener("submit",async(e)=>{e.preventDefault();const text=question.value.trim();if(!text)return;submitButton.disabled=true;submitLabel.textContent="Thinking";results.hidden=false;document.getElementById("answer").textContent="Working on your answer…";document.getElementById("caption").textContent="Finding the right hook…";document.getElementById("hashtags").replaceChildren();showImageMessage("Visual will appear after answer...");try{const r=await fetch("/api/generate",{method:"POST",headers:{"Content-Type":"application/json","X-User-Id":UID},body:JSON.stringify({question:text})});const data=await r.json().catch(()=>({}));if(r.status===402){showPaywall();throw new Error(data.error||"Free limit reached. Subscribe to continue.")}if(!r.ok)throw new Error(data.error||"Could not generate");document.getElementById("answer").textContent=data.answer;document.getElementById("caption").textContent=data.caption;currentCaption=[data.caption,...(data.hashtags||[])].join("\n\n");const tags=document.getElementById("hashtags");for(const tag of data.hashtags||[]){const chip=document.createElement("span");chip.className="hashtag";chip.textContent=tag.startsWith("#")?tag:`#${tag}`;tags.append(chip)}void generateImage(data.image_prompt);void checkServices();}catch(err){document.getElementById("answer").textContent=err.message;document.getElementById("caption").textContent=err.message.includes("limit")?"Subscribe to continue": "Caption unavailable";showImageMessage(err.message.includes("limit")?"Subscribe to unlock images":"Image unavailable until answer works")}finally{submitButton.disabled=false;submitLabel.textContent="Create with AI"}});
    document.querySelectorAll("[data-copy]").forEach(b=>{b.addEventListener("click",async()=>{const t=b.dataset.copy,text=t==="answer"?document.getElementById("answer").textContent:currentCaption;if(!text)return;try{await navigator.clipboard.writeText(text);notify(`${t} copied`)}catch{notify("Clipboard unavailable")}} )});
    document.getElementById("payment-form").addEventListener("submit", async(e)=>{
      e.preventDefault();
      const phone=document.getElementById("payer-phone").value.trim();
      const trans=document.getElementById("trans-id").value.trim();
      const name=document.getElementById("payer-name").value.trim();
      const file=document.getElementById("screenshot-file").files[0];
      if(!phone||!trans){notify("Enter phone and transaction ID");return;}
      const status=document.getElementById("pay-status");
      const btn=document.getElementById("pay-submit");
      btn.disabled=true; status.textContent="Submitting...";
      try{
        const fd=new FormData();
        fd.append("uid", UID);
        fd.append("plan", selectedPlan);
        fd.append("phone", phone);
        fd.append("transaction_id", trans);
        fd.append("name", name);
        if(file) fd.append("screenshot", file);
        const r=await fetch("/api/request-payment",{method:"POST",headers:{"X-User-Id":UID},body:fd});
        const d=await r.json();
        if(!r.ok) throw new Error(d.error||"Failed");
        notify("Payment proof submitted! Wait for approval.");
        status.textContent="Submitted! Admin will approve soon.";
      }catch(err){notify(err.message); status.textContent="Error: "+err.message;}
      finally{btn.disabled=false;}
    });
  </script>
</body>
</html>"""

ADMIN_PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exquisite Admin</title><style>body{background:#101018;color:#f5f2fa;font-family:system-ui;padding:20px}input,select,button{padding:10px 14px;border-radius:10px;border:1px solid #333;background:#191923;color:#fff;margin:4px}button{cursor:pointer;background:#bda0ff;color:#111}table{width:100%;border-collapse:collapse;margin-top:16px}th,td{border:1px solid #222;padding:8px;text-align:left;font-size:12px;vertical-align:top}th{background:#191923}.ok{color:#a8f0d5}.bad{color:#ff8a8a}img{max-width:140px;border-radius:8px}.card{background:#191923;border:1px solid #222;padding:12px;border-radius:12px;margin:10px 0}</style></head><body>
<h2>Exquisite AI Admin</h2>
{% if not authed %}
<form method="POST"><input type="password" name="password" placeholder="Admin password" required><button>Login</button></form>
{% else %}
<form method="POST" action="/admin/logout"><button>Logout</button></form>
<h3>Approve User by ID</h3>
<form method="POST" action="/admin/approve">
<input name="uid" placeholder="User ID" required style="width:320px">
<select name="plan"><option value="day">Day - GHS10 / 1d</option><option value="weekly" selected>Weekly - GHS49 / 7d</option><option value="monthly">Monthly - GHS99 / 30d</option></select>
<button type="submit">Approve / Extend</button>
</form>
<form method="POST" action="/admin/reject" style="margin-top:8px">
<input name="uid" placeholder="User ID to revoke/reset" style="width:320px"><button style="background:#ff8a8a;color:#111">Revoke Premium / Reset free</button>
</form>

<h3>Pending Payments</h3>
{% for p in pendings %}
<div class="card">
<b>{{p.plan}} - GHS {{p.price}}</b> | Phone: {{p.phone}} | Trans: {{p.transaction_id}} | Name: {{p.name}}<br>
UID: <code>{{p.uid}}</code> <button onclick="navigator.clipboard.writeText('{{p.uid}}')">copy</button> | At: {{p.at_str}} | Status: {{p.status}}<br>
{% if p.screenshot_path %}<a href="/{{p.screenshot_path}}" target="_blank"><img src="/{{p.screenshot_path}}"></a>{% else %}No screenshot{% endif %}
<div style="margin-top:8px">
<form method="POST" action="/admin/approve" style="display:inline"><input type="hidden" name="uid" value="{{p.uid}}"><input type="hidden" name="plan" value="{{p.plan}}"><button>Approve {{p.uid[:8]}}</button></form>
</div>
</div>
{% endfor %}

<h3>All Users</h3>
<table><tr><th>UID</th><th>Free</th><th>Plan</th><th>Expiry</th><th>Status</th><th>Created</th></tr>
{% for u in users %}
<tr><td title="{{u.uid}}">{{u.uid[:8]}}... <button onclick="navigator.clipboard.writeText('{{u.uid}}')">copy</button></td><td>{{u.free_used}}/25</td><td>{{u.plan or '-'}}</td><td>{{u.expiry_str}}</td><td class="{{'ok' if u.is_premium else 'bad'}}">{{'PREMIUM' if u.is_premium else 'FREE'}}</td><td>{{u.created_str}}</td></tr>
{% endfor %}
</table>
<pre style="background:#191923;padding:12px;border-radius:10px;max-height:400px;overflow:auto">{{logs}}</pre>
{% endif %}
</body></html>
"""

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response

@app.get("/")
def index():
    uid = get_user_id()
    resp = make_response(render_template_string(PAGE))
    if not request.cookies.get("exquisite_uid"):
        resp.set_cookie("exquisite_uid", uid, max_age=31536000, httponly=False, samesite="Lax")
    return resp

@app.get("/health")
def health():
    data = load_data()
    uid = get_user_id()
    user = get_user_record(data, uid)
    save_data(data)
    expiry = user.get("expiry", 0)
    exp_str = datetime.fromtimestamp(expiry).strftime("%Y-%m-%d %H:%M") if expiry else "-"
    return jsonify({
        "status": "ok",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "pollinations_configured": True,
        "free_remaining": remaining_free(user),
        "is_premium": is_premium(user),
        "expiry": expiry,
        "expiry_str": exp_str,
        "uid": uid
    })

@app.post("/api/generate")
def generate():
    data = load_data()
    uid = get_user_id()
    user = get_user_record(data, uid)

    payload = request.get_json(silent=True) or {}
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "Enter a question."}), 400
    question = question.strip()
    if len(question) > MAX_QUESTION_LENGTH:
        return jsonify({"error": f"Keep under {MAX_QUESTION_LENGTH:,} chars."}), 413

    if not is_premium(user) and user.get("free_used", 0) >= FREE_USES:
        save_data(data)
        return jsonify({"error": f"Free limit of {FREE_USES} reached. Subscribe: Day GHS10, Weekly GHS49, Monthly GHS99. MoMo: 0533041233 - Michael Asante.", "code": "PAYWALL"}), 402

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify({"error": "Add GEMINI_API_KEY in Secrets."}), 503

    from google import genai
    from google.genai import types
    instructions = f"You are Exquisite AI. Answer directly with useful detail. Create vivid image prompt (no text), engaging TikTok caption, 3-5 hashtags. Return JSON per schema.\n\nQuestion:\n{question}"
    try:
        client = genai.Client(api_key=api_key)
        result = client.models.generate_content(
            model=MODEL,
            contents=instructions,
            config=types.GenerateContentConfig(response_mime_type="application/json",response_schema=RESULT_SCHEMA,temperature=0.7),
        )
        parsed = json.loads(result.text or "")
        answer = parsed.get("answer"); image_prompt = parsed.get("image_prompt"); caption = parsed.get("caption"); hashtags = parsed.get("hashtags")
        if not all(isinstance(v, str) and v.strip() for v in (answer, image_prompt, caption)):
            raise ValueError("Incomplete content")
        if not isinstance(hashtags, list): hashtags = []
        hashtags = [t.strip() for t in hashtags if isinstance(t, str) and t.strip()][:5]

        if not is_premium(user):
            user["free_used"] = user.get("free_used", 0) + 1
        save_data(data)

        resp = jsonify({"answer": answer.strip(),"image_prompt": image_prompt.strip()[:MAX_IMAGE_PROMPT_LENGTH],"caption": caption.strip(),"hashtags": hashtags})
        resp.set_cookie("exquisite_uid", uid, max_age=31536000)
        return resp
    except Exception as e:
        app.logger.exception("Gemini failed")
        save_data(data)
        return jsonify({"error": f"Gemini error: {str(e)[:500]}"}), 502

@app.post("/api/image")
def generate_image():
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify({"error": "Prompt required."}), 400
    prompt = prompt.strip()[:MAX_IMAGE_PROMPT_LENGTH]
    api_key = os.environ.get("POLLINATIONS_API_KEY")
    image_url = f"https://gen.pollinations.ai/image/{quote(prompt, safe='')}?{urlencode({'model': 'flux'})}"
    headers = {"Accept": "image/*","User-Agent": "ExquisiteAI/1.0"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    upstream_request = Request(image_url, headers=headers)
    try:
        with urlopen(upstream_request, timeout=120) as upstream:
            ct = upstream.headers.get_content_type()
            if not ct.startswith("image/"):
                return jsonify({"error": "Pollinations unexpected"}), 502
            image_bytes = upstream.read(15 * 1024 * 1024 + 1)
            return Response(image_bytes, mimetype=ct, headers={"Cache-Control": "no-store"})
    except HTTPError:
        return jsonify({"error": "Pollinations could not generate image."}), 502
    except (TimeoutError, URLError) as e:
        return jsonify({"error": f"Pollinations timeout: {e}"}), 504

@app.post("/api/request-payment")
def request_payment():
    data = load_data()
    uid = request.form.get("uid") or get_user_id()
    plan_key = request.form.get("plan","weekly")
    phone = request.form.get("phone","").strip()
    trans_id = request.form.get("transaction_id","").strip()
    name = request.form.get("name","").strip()
    if plan_key not in PLANS:
        return jsonify({"error": "Invalid plan"}), 400
    if not phone or not trans_id:
        return jsonify({"error": "Phone and Transaction ID required"}), 400
    screenshot_path = ""
    if "screenshot" in request.files:
        f = request.files["screenshot"]
        if f and f.filename:
            ext = os.path.splitext(f.filename)[1].lower() or ".png"
            fname = f"{uid[:8]}_{int(time.time())}{ext}"
            fpath = os.path.join(UPLOAD_DIR, fname)
            f.save(fpath)
            screenshot_path = fpath
    entry = {
        "uid": uid, "plan": plan_key, "price": PLANS[plan_key]["price"],
        "phone": phone, "transaction_id": trans_id, "name": name,
        "screenshot_path": screenshot_path,
        "at": int(time.time()), "at_str": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "pending"
    }
    data.setdefault("payments", []).append(entry)
    save_data(data)
    return jsonify({"ok": True})

def admin_authed():
    return request.cookies.get("admin_auth") == ADMIN_PASSWORD

@app.get("/admin")
def admin_page():
    from jinja2 import Template
    if not admin_authed():
        return render_template_string(ADMIN_PAGE, authed=False)
    data = load_data()
    users = []
    for uid, u in data.get("users", {}).items():
        exp = u.get("expiry",0)
        users.append({
            "uid": uid, "free_used": u.get("free_used",0), "plan": u.get("plan"),
            "expiry": exp, "expiry_str": datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M") if exp else "-",
            "is_premium": exp > time.time(),
            "created_str": datetime.fromtimestamp(u.get("created",0)).strftime("%Y-%m-%d") if u.get("created") else "-"
        })
    users.sort(key=lambda x: x["expiry"], reverse=True)
    pendings = [p for p in data.get("payments", []) if p.get("status")=="pending"]
    pendings = sorted(pendings, key=lambda x: x.get("at",0), reverse=True)
    logs = json.dumps(data.get("payments", [])[-100:], indent=2)
    return Template(ADMIN_PAGE).render(authed=True, users=users, pendings=pendings, logs=logs)

@app.post("/admin")
def admin_login():
    pwd = request.form.get("password","")
    if pwd == ADMIN_PASSWORD:
        resp = make_response(redirect("/admin"))
        resp.set_cookie("admin_auth", ADMIN_PASSWORD, max_age=86400*7, httponly=True, samesite="Lax")
        return resp
    return render_template_string(ADMIN_PAGE, authed=False)

@app.post("/admin/logout")
def admin_logout():
    resp = make_response(redirect("/admin"))
    resp.delete_cookie("admin_auth")
    return resp

@app.post("/admin/approve")
def admin_approve():
    if not admin_authed():
        return redirect("/admin")
    uid = request.form.get("uid","").strip()
    plan_key = request.form.get("plan","weekly")
    if not uid or plan_key not in PLANS:
        return "Invalid", 400
    data = load_data()
    user = get_user_record(data, uid)
    plan = PLANS[plan_key]
    now = time.time()
    base = max(now, user.get("expiry",0))
    new_expiry = base + plan["days"]*86400
    user["expiry"] = new_expiry
    user["plan"] = plan_key
    for p in data.get("payments", []):
        if p.get("uid")==uid and p.get("status")=="pending" and p.get("plan")==plan_key:
            p["status"] = "approved"
    data["payments"].append({"uid": uid, "plan": plan_key, "price": plan["price"], "approved_at": int(now), "expiry": new_expiry, "action": "approve", "at_str": datetime.now().strftime("%Y-%m-%d %H:%M"), "status": "approved"})
    save_data(data)
    return redirect("/admin")

@app.post("/admin/reject")
def admin_reject():
    if not admin_authed():
        return redirect("/admin")
    uid = request.form.get("uid","").strip()
    data = load_data()
    if uid in data.get("users",{}):
        data["users"][uid]["expiry"] = 0
        data["users"][uid]["plan"] = None
        data["users"][uid]["free_used"] = 0
        data["payments"].append({"uid": uid, "action": "revoke", "at": int(time.time()), "at_str": datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_data(data)
    return redirect("/admin")

@app.get("/uploads/<path:filename>")
def serve_upload(filename):
    if not admin_authed():
        return "Unauthorized", 401
    fpath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(fpath):
        return "Not found", 404
    with open(fpath, "rb") as f:
        d = f.read()
    return Response(d, mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
