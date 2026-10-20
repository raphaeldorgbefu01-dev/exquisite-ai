import json, os, uuid, time, urllib.parse, base64
from flask import Flask, jsonify, request, make_response
import requests as http_requests

app = Flask(__name__)
FREE_USES = 25
DATA_FILE = "exquisite_data.json"
PAYSTACK_PUBLIC_KEY = os.environ.get("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_SECRET_KEY = os.environ.get("PAYSTACK_SECRET_KEY", "")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "payments": []}
    try:
        f = open(DATA_FILE, "r")
        d = json.load(f)
        f.close()
        return d
    except:
        return {"users": {}, "payments": []}

def save_data(d):
    try:
        f = open(DATA_FILE, "w")
        json.dump(d, f, indent=2)
        f.close()
    except:
        pass

def get_user_id():
    uid = request.cookies.get("exquisite_uid")
    if not uid:
        uid = request.headers.get("X-User-Id")
    if not uid:
        uid = str(uuid.uuid4())
    return uid

def get_user_record(data, uid):
    users = data.setdefault("users", {})
    if uid not in users:
        users[uid] = {"free_used":0,"expiry":0,"plan":None}
    return users[uid]

def is_premium(u):
    return u.get("expiry",0) > time.time()

def remaining_free(u):
    if is_premium(u):
        return 9999
    left = FREE_USES - u.get("free_used",0)
    if left < 0:
        left = 0
    return left

def ask_gemini(prompt_text, api_key):
    if not api_key:
        return None
    models = ["gemini-1.5-flash-latest","gemini-1.5-flash","gemini-2.0-flash","gemini-1.0-pro"]
    vers = ["v1beta","v1"]
    for model in models:
        for ver in vers:
            try:
                url = "https://generativelanguage.googleapis.com/" + ver + "/models/" + model + ":generateContent?key=" + api_key
                payload = {"contents":[{"parts":[{"text": prompt_text}]}],"generationConfig":{"temperature":0.75,"maxOutputTokens":2500}}
                r = http_requests.post(url, json=payload, timeout=20)
                jr = r.json()
                if "candidates" in jr and jr["candidates"]:
                    cand = jr["candidates"][0]
                    content = cand.get("content",{})
                    parts = content.get("parts",[])
                    if parts:
                        txt = parts[0].get("text","")
                        if txt:
                            return txt
            except:
                continue
    return None

def local_answer(prompt, search_type):
    low = prompt.lower()
    if search_type == "all":
        if "best business" in low and "ghana" in low:
            return "Best Businesses Ghana 2025-26:\n1. Food Delivery GHS 300-800 per day\n2. MoMo Agency GHS 100-400 commission\n3. Thrift at Kantamanto sell on TikTok 100-250 percent profit\n4. Phone Accessories 3x price\n5. Beauty Wigs monthly demand\n6. AI Content Agency manage Instagram charge GHS 800-2000 per client\nMy pick: Combine 6 and 3 zero inventory"
        if "what is ai" in low:
            return "What is AI? AI is software that learns like human. Show computers millions of kente patterns it learns. Daily use: TikTok, MoMo fraud check, Maps, this app. 2026 500M plus use AI weekly."
        return "Answer for: " + prompt + "\n\nThis topic is important in Ghana and globally 2026. Ask more specifically like Explain simply, or Business plan, or Write code."
    if search_type == "captions":
        return "7 Captions for " + prompt[:50] + ": 1 Ghana elegance slow mo 2 Slow mo fashion 3 Tradition takes flight 4 Fabric flowing 5 60fps culture 6 Luxury details 7 From Accra with love"
    if search_type == "scripts":
        return "Script for " + prompt[:50] + ": HOOK 0-3s Stop scrolling BODY 3-25s Wide 60fps close-up 120fps CTA Follow for more"
    if search_type == "stories":
        return "Brand Story for " + prompt[:50] + ": Heritage Accra tradition meets ambition Mission Exquisite AI brings Ghana excellence"
    return "Answer for " + prompt

PLANS = {
    "day": {"label":"Day - GHS 10","price":10,"kobo":1000,"days":1},
    "weekly": {"label":"Weekly - GHS 49","price":49,"kobo":4900,"days":7},
    "monthly": {"label":"Monthly - GHS 99","price":99,"kobo":9900,"days":30}
}

PAGE_B64 = "PCFkb2N0eXBlIGh0bWw+PGh0bWw+PGhlYWQ+PG1ldGEgY2hhcnNldD0idXRmLTgiPjxtZXRhIG5hbWU9InZpZXdwb3J0IiBjb250ZW50PSJ3aWR0aD1kZXZpY2Utd2lkdGgsaW5pdGlhbC1zY2FsZT0xIj48dGl0bGU+RXhxdWlzaXRlIEFJPC90aXRsZT48c2NyaXB0IHNyYz0iaHR0cHM6Ly9qcy5wYXlzdGFjay5jby92MS9pbmxpbmUuanMiPjwvc2NyaXB0PjxzdHlsZT5ib2R5e21hcmdpbjowO2JhY2tncm91bmQ6IzBmMGYxODtjb2xvcjojZjVmMmZhO2ZvbnQtZmFtaWx5OkludGVyLHNhbnMtc2VyaWZ9LnNoZWxse3dpZHRoOm1pbigxMDUwcHgsY2FsYygxMDAlIC0gMzJweCkpO21hcmdpbjowIGF1dG87cGFkZGluZzoyNHB4IDB9LmNhcmR7YmFja2dyb3VuZDojMTkxOTIzO2JvcmRlcjoxcHggc29saWQgcmdiYSgyNTUsMjU1LDI1NSwuMTIpO2JvcmRlci1yYWRpdXM6MjBweDtwYWRkaW5nOjIwcHg7bWFyZ2luOjE4cHggMH0uYnV0dG9uLnByaW1hcnl7YmFja2dyb3VuZDojYmRhMGZmO2NvbG9yOiMxMTE7Ym9yZGVyOjA7Ym9yZGVyLXJhZGl1czoxMnB4O3BhZGRpbmc6MTJweCAyMHB4O2ZvbnQtd2VpZ2h0OjgwMDtjdXJzb3I6cG9pbnRlcn0uYnV0dG9uLnByaW1hcnkuaGlkZGVue2Rpc3BsYXk6bm9uZSFpbXBvcnRhbnR9dGV4dGFyZWF7d2lkdGg6MTAwJTtwYWRkaW5nOjE2cHg7Ym9yZGVyLXJhZGl1czoxNHB4O2JvcmRlcjoxcHggc29saWQgcmdiYSgyNTUsMjU1LDI1NSwuMTUpO2JhY2tncm91bmQ6IzExMTExYTtjb2xvcjojZmZmO2ZvbnQtc2l6ZToxNXB4O291dGxpbmU6bm9uZTtib3gtc2l6aW5nOmJvcmRlci1ib3h9dGV4dGFyZWE6Zm9jdXN7Ym9yZGVyLWNvbG9yOiNiZGEwZmZ9LnRhYntib3JkZXI6MXB4IHNvbGlkIHJnYmEoMjU1LDI1NSwyNTUsLC4xMik7YmFja2dyb3VuZDojMTgxODI1O2NvbG9yOiNhNGExYjI7cGFkZGluZzo5cHggMTZweDtib3JkZXItcmFkaXVzOjk5OXB4O2ZvbnQtc2l6ZToxM3B4O2N1cnNvcjpwb2ludGVyO21hcmdpbjozcHh9LnRhYi5hY3RpdmV7YmFja2dyb3VuZDojYmRhMGZmO2NvbG9yOiMxMTE7Zm9udC13ZWlnaHQ6NzAwfSNyZXN1bHR7bGluZS1oZWlnaHQ6MS43NTt3aGl0ZS1zcGFjZTpwcmUtd3JhcDtiYWNrZ3JvdW5kOiMxMTExMWE7Ym9yZGVyLXJhZGl1czoxNHB4O3BhZGRpbmc6MThweDttaW4taGVpZ2h0OjcwcHg7cG9zaXRpb246cmVsYXRpdmU7Ym9yZGVyOjFweCBzb2xpZCByZ2JhKDI1NSwyNTUsMjU1LC4wNil9LmNvcHktYnRue3Bvc2l0aW9uOmFic29sdXRlO3RvcDoxMHB4O3JpZ2h0OjEwcHg7YmFja2dyb3VuZDojMjMyMzJmO2JvcmRlcjoxcHggc29saWQgcmdiYSgyNTUsMjU1LDI1NSwuMTIpO2NvbG9yOiNhNGExYjI7Ym9yZGVyLXJhZGl1czo4cHg7cGFkZGluZzo2cHggMTBweDtmb250LXNpemU6MTJweDtjdXJzb3I6cG9pbnRlcn0uYmFkZ2V7ZGlzcGxheTppbmxpbmUtYmxvY2s7YmFja2dyb3VuZDpyZ2JhKDE4OSwxNjAsMjU1LC4xNSk7Ym9yZGVyOjFweCBzb2xpZCByZ2JhKDE4OSwxNjAsMjU1LC4zKTtjb2xvcjojYmRhMGZmO2JvcmRlci1yYWRpdXM6OTk5cHg7cGFkZGluZzozcHggMTBweDtmb250LXNpemU6MTFweDttYXJnaW4tYm90dG9tOjEwcHh9PC9zdHlsZT48L2hlYWQ+PGJvZHk+PGRpdiBjbGFzcz0ic2hlbGwiPjxoMSBzdHlsZT0idGV4dC1hbGlnbjpjZW50ZXI7bWFyZ2luOjhweCAwIj5XaGVyZSBJZGVhcyBUYWtlIEZsaWdodDwvaDE+PHAgc3R5bGU9InRleHQtYWxpZ246Y2VudGVyO2NvbG9yOiNhNGExYjI7Zm9udC1zaXplOjEzcHg7bWFyZ2luOjAgMCAxMHB4Ij5Bc2sgYW55dGhpbmcgbGlrZSBHZW1pbmkgLSBtYXRoLCBjb2RlLCBidXNpbmVzcywgaGVhbHRoPC9wPjxkaXYgc3R5bGU9InRleHQtYWxpZ246Y2VudGVyO21hcmdpbjoxNHB4IDAiPjxidXR0b24gY2xhc3M9InRhYiBhY3RpdmUiIGlkPSJ0YWItYWxsIiBvbmNsaWNrPSJzZXRUeXBlKCdhbGwnKSI+QWxsPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0idGFiIiBpZD0idGFiLWNhcHRpb25zIiBvbmNsaWNrPSJzZXRUeXBlKCdjYXB0aW9ucycpIj5DYXB0aW9uczwvYnV0dG9uPjxidXR0b24gY2xhc3M9InRhYiIgaWQ9InRhYi1zY3JpcHRzIiBvbmNsaWNrPSJzZXRUeXBlKCdzY3JpcHRzJykiPlNjcmlwdHM8L2J1dHRvbj48YnV0dG9uIGNsYXNzPSJ0YWIiIGlkPSJ0YWItc3RvcmllcyIgb25jbGljaz0ic2V0VHlwZSgnc3RvcmllcycpIj5TdG9yaWVzPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0idGFiIiBpZD0idGFiLWltYWdlcyIgb25jbGljaz0ic2V0VHlwZSgnaW1hZ2VzJykiPkltYWdlczwvYnV0dG9uPjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQiPjxkaXYgY2xhc3M9ImJhZGdlIiBpZD0ibW9kZUJhZGdlIj5Nb2RlOiBBbGwgLSBHZW5lcmFsIEFJPC9kaXY+PHRleHRhcmVhIGlkPSJwcm9tcHQiIHJvd3M9IjQiIHBsYWNlaG9sZGVyPSJBc2sgYW55dGhpbmc6IEJlc3QgYnVzaW5lc3MgaW4gR2hhbmE/IFdoYXQgaXMgQUk/IFNvbHZlIDJ4KzU9MTU/IiBvbmZvY3VzPSJzaG93QnV0dG9uKCkiIG9uaW5wdXQ9InNob3dCdXR0b24oKSI+PC90ZXh0YXJlYT48YnI+PGJyPjxidXR0b24gY2xhc3M9InByaW1hcnkgaGlkZGVuIiBpZD0iZmxpZ2h0QnRuIiBvbmNsaWNrPSJnZW5lcmF0ZSgpIj5MZXQgSXQgVGFrZSBGbGlnaHQ8L2J1dHRvbj48ZGl2IGlkPSJyZXN1bHQiIHN0eWxlPSJtYXJnaW4tdG9wOjE2cHgiPjxzcGFuIHN0eWxlPSJjb2xvcjojYTRhMWIyIj5Zb3VyIGFuc3dlciB3aWxsIGFwcGVhciBoZXJlLi4uPC9zcGFuPjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQiPjxoMyBzdHlsZT0ibWFyZ2luOjAgMCAxMHB4Ij5VbmxvY2sgVW5saW1pdGVkPC9oMz48ZGl2IGlkPSJwbGFucyI+PC9kaXY+PGRpdiBpZD0icXVvdGEiIHN0eWxlPSJtYXJnaW4tdG9wOjEwcHg7Y29sb3I6I2E0YTFiMjtmb250LXNpemU6MTNweCI+PC9kaXY+PC9kaXY+PC9kaXY+PHNjcmlwdD5sZXQgUFVCTElDX0tFWT0iX19QVUJMSUNfS0VZX18iO2xldCBjdXJyZW50VHlwZT0iYWxsIjtmdW5jdGlvbiBzaG93QnV0dG9uKCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImZsaWdodEJ0biIpLmNsYXNzTGlzdC5yZW1vdmUoImhpZGRlbiIpO31mdW5jdGlvbiBoaWRlQnV0dG9uKCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImZsaWdodEJ0biIpLmNsYXNzTGlzdC5hZGQoImhpZGRlbiIpO31mdW5jdGlvbiBzZXRUeXBlKHQpe2N1cnJlbnRUeXBlPXQ7ZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgiLnRhYiIpLmZvckVhY2goYj0+Yy5jbGFzc0xpc3QucmVtb3ZlKCJhY3RpdmUiKSk7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInRhYi0iK3QpLmNsYXNzTGlzdC5hZGQoImFjdGl2ZSIpO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJtb2RlQmFkZ2UiKS5pbm5lclRleHQ9Ik1vZGU6ICIrdDt2YXIgcHI9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInByb21wdCIpLnZhbHVlLnRyaW0oKTtpZihwci5sZW5ndGg+Mil7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInJlc3VsdCIpLmlubmVySFRNTD0iU3dpdGNoaW5nIHRvICIrdCsiLi4uIjtoaWRlQnV0dG9uKCk7Z2VuZXJhdGUoKTt9fWFzeW5jIGZ1bmN0aW9uIHJlZnJlc2hRdW90YSgpe3RyeXtsZXQgcj1hd2FpdCBmZXRjaCgiL2FwaS9tZSIpO2xldCBkPWF3YWl0IHIuanNvbigpO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJxdW90YSIpLmlubmVyVGV4dD1kLmlzX3ByZW1pdW0/IlByZW1pdW06ICIrdC5wbGFuKyIgVW5saW1pdGVkIjpGcmVlOiArZC5yZW1haW5pbmcrIiBsZWZ0IjtsZXQgcD1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgicGxhbnMiKTtwLmlubmVySFRNTD0iIjtPYmplY3QuZW50cmllcyhkLnBsYW5zKS5mb3JFYWNoKChbayx2XT0+e2xldCBiPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoImJ1dHRvbiIpO2IuY2xhc3NOYW1lPSJwcmltYXJ5IjtiLmlubmVyVGV4dD12LmxhYmVsO2Iuc3R5bGUubWFyZ2luPSI0cHgiO2Iub25jbGljaz0oKT0+cGF5KGspO3AuYXBwZW5kQ2hpbGQoYik7fSk7fWNhdGNoKGUpe319ZnVuY3Rpb24gY29weVJlc3VsdCgpe25hdmlnYXRvci5jbGlwYm9hcmQud3JpdGVUZXh0KGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJyZXN1bHQiKS5pbm5lclRleHQpO2FsZXJ0KCdDb3BpZWQhJyk7fWFzeW5jIGZ1bmN0aW9uIGdlbmVyYXRlKCl7bGV0IHByPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJwcm9tcHQiKS52YWx1ZS50cmltKCk7aWYoIXByKXthbGVydCgiVHlwZSBhIHF1ZXN0aW9uIik7cmV0dXJuO31sZXQgcmVzRWw9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInJlc3VsdCIpO3Jlc0VsLmlubmVySFRNTD0iRXhxdWlzaXRlIEFJIHRoaW5raW5nLi4uICgiK2N1cnJlbnRUeXBlKyIpIjtqaWRlQnV0dG9uKCk7dHJ5e2xldCByPWF3YWl0IGZldGNoKCIvYXBpL2dlbmVyYXRlIix7bWV0aG9kOiJQT1NUIixoZWFkZXJzOnsiQ29udGVudC1UeXBlIjoiYXBwbGljYXRpb24vanNvbiJ9LGJvZHk6SlNPTi5zdHJpbmdpZnkoe3Byb21wdDpwcix0eXBlOmN1cnJlbnRUeXBlfSl9KTtsZXQgZD1hd2FpdCByLmpzb24oKTtsZXQgaHRtbD0nPGJ1dHRvbiBjbGFzcz0iY29weS1idG4iIG9uY2xpY2s9ImNvcHlSZXN1bHQoKSI+Q29weTwvYnV0dG9uPicrZC5hbnN3ZXI7aWYoZC5pbWFnZV91cmwpe2h0bWwrPSciPGJyPjxpbWcgc3JjPSInK2QuaW1hZ2VfdXJsKysiIiBzdHlsZT0ibWF4LXdpZHRoOjEwMCU7Ym9yZGVyLXJhZGl1czoxNHB4Ij4nO31yZXNFbC5pbm5lckhUTUw9aHRtbDt9Y2F0Y2goZSl7cmVzRWwuaW5uZXJIVE1MPSdFcnJvcjogJytlO31zZXRUaW1lb3V0KHJlZnJlc2hRdW90YSw2MDApO31mdW5jdGlvbiBwYXkocGxhbil7aWYoIUFVQkxJQ19LRVkpW2FsZXJ0KCdBZGQgUGF5c3RhY2sga2V5Jyk7cmV0dXJuO31mZXRjaCgiL2FwaS9wYXlzdGFjay9pbml0Iix7bWV0aG9kOiJQT1NUIixoZWFkZXJzOnsiQ29udGVudC1UeXBlIjoiYXBwbGljYXRpb24vanNvbiJ9LGJvZHk6SlNPTi5zdHJpbmdpZnkoe3BsYW46cGxhbn0pfSkudGhlbihyPT5yLmpzb24oKSkudGhlbihkPT57aWYoZC5lcnJvcilhbGVydChkLmVycm9yKTt2YXIgaD1QYXlzdGFja1BvcC5zZXR1cCh7a2V5OlBVQkxJQ19LRVksZW1haWw6ZC5lbWFpbCxhbW91bnQ6ZC5rb2JvLGN1cnJlbmN5OiJHSFMiLHJlZjpkLnJlZmVyZW5jZSxjYWxsYmFjazpmdW5jdGlvbihyZXNwKXtmZXRjaCgiL2FwaS9wYXlzdGFjay92ZXJpZnkiLHttZXRob2Q6IlBPU1QiLGhlYWRlcnM6eyJDb250ZW50LVR5cGUiOiJhcHBsaWNhdGlvbi9qc29uIn0sYm9keTpKU09OLnN0cmluZ2lmeSh7cmVmZXJlbmNlOnJlc3AucmVmZXJlbmNlfSl9KS50aGVuKHI9PnIuanNvbigpKS50aGVuKHY9PnthbGVydCh2Lm1lc3NhZ2UpO3JlZnJlc2hRdW90YSgpO30pLG9uQ2xvc2U6ZnVuY3Rpb24oKXt9fSk7aC5vcGVuSWZyYW1lKCk7fSk7fWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJwcm9tcHQiKS5hZGRFdmVudExpc3RlbmVyKCJmb2N1cyIsc2hvd0J1dHRvbik7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInByb21wdCIpLmFkZEV2ZW50TGlzdGVuZXIoImlucHV0IixzaG93QnV0dG9uKTtyZWZyZXNoUXVvdGEoKTs8L3NjcmlwdD48L2JvZHk+PC9odG1sPg=="

def get_page():
    html_bytes = base64.b64decode(PAGE_B64)
    html = html_bytes.decode("utf-8")
    return html.replace("__PUBLIC_KEY__", PAYSTACK_PUBLIC_KEY)

@app.route("/")
def index():
    html = get_page()
    uid = get_user_id()
    resp = make_response(html)
    resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365)
    return resp

@app.route("/api/me")
def me():
    data = load_data()
    uid = get_user_id()
    user = get_user_record(data, uid)
    return jsonify({"remaining": remaining_free(user),"is_premium": is_premium(user),"plan": user.get("plan"),"plans": PLANS})

@app.route("/api/generate", methods=["POST"])
def generate_api():
    try:
        data = load_data()
        uid = get_user_id()
        user = get_user_record(data, uid)
        used = user.get("free_used",0)
        if not is_premium(user) and used >= FREE_USES:
            return jsonify({"answer":"Free limit reached (25 per day). Upgrade to unlimited."})
        j = request.get_json() or {}
        prompt_raw = j.get("prompt") or ""
        prompt = prompt_raw.strip()[:3000]
        search_type = j.get("type") or "all"
        gemini_key = os.environ.get("GEMINI_API_KEY","")
        if not gemini_key:
            gemini_key = os.environ.get("GOOGLE_API_KEY","")
        if not gemini_key:
            gemini_key = ""
        if not prompt:
            return jsonify({"answer":"Type a question first"})
        answer = ""
        image_url = None
        if search_type == "images":
            enhanced = prompt
            if gemini_key:
                ai_text = ask_gemini("One detailed photorealistic image prompt only: " + prompt, gemini_key)
                if ai_text:
                    enhanced = ai_text[:600]
            full = enhanced + ", ultra photorealistic, highly detailed, 8k, professional studio lighting"
            safe = urllib.parse.quote(full[:700])
            seed = int(time.time()) % 999999
            image_url = "https://image.pollinations.ai/prompt/" + safe + "?width=1280&height=1280&nologo=true&model=flux&seed=" + str(seed)
            answer = "4K Image: " + prompt[:80] + "\nPrompt: " + full
        elif search_type == "all":
            if gemini_key:
                gen_prompt = "You are Exquisite AI, helpful assistant like Gemini and Meta AI. Answer any question: " + prompt
                ai_answer = ask_gemini(gen_prompt, gemini_key)
                if ai_answer and len(ai_answer) > 20:
                    answer = ai_answer
            if not answer:
                answer = local_answer(prompt, "all")
        else:
            if gemini_key:
                if search_type == "captions":
                    instr = "Viral captions expert. Create 7 viral captions with emojis and hashtags for: " + prompt
                elif search_type == "scripts":
                    instr = "TikTok script writer. Write 30-60s script HOOK BODY CTA for: " + prompt
                else:
                    instr = "Luxury brand storyteller. Write inspiring brand story for: " + prompt
                ai_answer = ask_gemini(instr, gemini_key)
                if ai_answer:
                    answer = ai_answer
                else:
                    answer = local_answer(prompt, search_type)
            else:
                answer = local_answer(prompt, search_type)
        user["free_used"] = user.get("free_used",0)+1
        save_data(data)
        out = {}
        out["answer"] = answer
        if image_url:
            out["image_url"] = image_url
        resp = make_response(jsonify(out))
        resp.set_cookie("exquisite_uid", uid, max_age=60*60*24*365)
        return resp
    except Exception as e:
        return jsonify({"answer": local_answer("Best business in Ghana", "all")})

@app.route("/api/paystack/init", methods=["POST"])
def paystack_init():
    try:
        if not PAYSTACK_SECRET_KEY:
            return jsonify({"error":"Paystack secret not set"}), 500
        j = request.get_json() or {}
        plan_key = j.get("plan") or "day"
        plan = PLANS.get(plan_key)
        if not plan:
            return jsonify({"error":"Invalid plan"}), 400
        uid = get_user_id()
        email = uid + "@exquisite.ai"
        headers = {"Authorization": "Bearer " + PAYSTACK_SECRET_KEY, "Content-Type":"application/json"}
        payload = {"email": email, "amount": plan["kobo"]*100, "currency":"GHS", "metadata":{"uid":uid,"plan":plan_key}}
        r = http_requests.post("https://api.paystack.co/transaction/initialize", json=payload, headers=headers, timeout=15)
        jr = r.json()
        if not jr.get("status"):
            return jsonify({"error": jr.get("message")}), 400
        return jsonify({"reference": jr["data"]["reference"], "kobo": plan["kobo"]*100, "email": email})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

@app.route("/api/paystack/verify", methods=["POST"])
def paystack_verify():
    try:
        j = request.get_json() or {}
        ref = j.get("reference")
        if not ref:
            return jsonify({"error":"No ref"}), 400
        headers = {"Authorization": "Bearer " + PAYSTACK_SECRET_KEY}
        r = http_requests.get("https://api.paystack.co/transaction/verify/" + ref, headers=headers, timeout=15)
        jr = r.json()
        if not jr.get("status") or jr["data"]["status"] != "success":
            return jsonify({"error":"Payment not successful"}), 400
        meta = jr["data"].get("metadata",{})
        uid = meta.get("uid")
        if not uid:
            uid = get_user_id()
        plan_key = meta.get("plan") or "day"
        data = load_data()
        user = get_user_record(data, uid)
        plan = PLANS.get(plan_key)
        if not plan:
            plan = PLANS["day"]
        user["plan"]=plan_key
        user["expiry"]=int(time.time())+plan["days"]*24*3600
        payments = data.setdefault("payments",[])
        payments.append({"uid":uid,"plan":plan_key,"ref":ref,"time":int(time.time())})
        save_data(data)
        msg = "Premium Activated! " + plan["label"]
        return jsonify({"message": msg})
    except Exception as ex:
        return jsonify({"error": str(ex)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
