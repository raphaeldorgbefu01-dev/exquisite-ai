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
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "payments": []}

def save_data(d):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except:
        pass

def get_user_id():
    uid = request.cookies.get("exquisite_uid") or request.headers.get("X-User-Id")
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
    return 9999 if is_premium(u) else max(0, FREE_USES - u.get("free_used",0))

def ask_gemini(prompt_text, api_key):
    if not api_key:
        return None
    models = ["gemini-1.5-flash-latest","gemini-1.5-flash","gemini-2.0-flash","gemini-1.0-pro"]
    for model in models:
        for ver in ["v1beta","v1"]:
            try:
                url = "https://generativelanguage.googleapis.com/" + ver + "/models/" + model + ":generateContent?key=" + api_key
                payload = {"contents":[{"parts":[{"text": prompt_text}]}],"generationConfig":{"temperature":0.75,"maxOutputTokens":2500}}
                r = http_requests.post(url, json=payload, timeout=20)
                jr = r.json()
                if "candidates" in jr and jr["candidates"]:
                    parts = jr["candidates"][0].get("content",{}).get("parts",[])
                    if parts:
                        txt = parts[0].get("text","")
                        if txt:
                            return txt
            except:
                continue
    return None

def local_answer(prompt, search_type):
    low = prompt.lower()
    t = prompt.strip()[:80].title() or "Topic"
    if search_type == "all":
        if "best business" in low and "ghana" in low:
            return "Best Businesses Ghana 2025-26:\n1. Food Delivery GHS 300-800/day\n2. MoMo Agency GHS 100-400 commission\n3. Thrift at Kantamanto sell TikTok 100-250% profit\n4. Phone Accessories 3x price\n5. Beauty Wigs monthly demand\n6. AI Content Agency manage Instagram charge GHS 800-2000 per client\nMy pick: Combine 6+3 zero inventory!"
        if "what is ai" in low:
            return "What is AI? AI is software that learns like human. Show computers millions of kente patterns it learns. Daily use: TikTok, MoMo fraud check, Maps, this app. 2026 500M+ use AI weekly."
        return "Answer for: " + prompt + "\n\nThis is " + t + ". Important in Ghana globally 2026. Ask more specifically like Explain simply, or Business plan, or Write code."
    if search_type == "captions":
        return "7 Captions for " + t + ": 1 Ghana elegance slow mo #GhanaFashion 2 Slow mo fashion #Kente 3 Tradition takes flight #AfricanFashion 4 Fabric flowing #AccraStyle 5 60fps culture #RunwayMagic 6 Luxury details #LuxuryFashion 7 From Accra with love #ExquisiteAI"
    if search_type == "scripts":
        return "Script for " + t + ": HOOK 0-3s Stop scrolling BODY 3-25s Wide 60fps close-up 120fps CTA Follow for more"
    if search_type == "stories":
        return "Brand Story for " + t + ": Heritage Accra tradition meets ambition Mission Exquisite AI brings Ghana excellence Tagline Where Ideas Take Flight"
    return "Answer for " + prompt

PLANS = {
    "day": {"label":"Day - GHS 10","price":10,"kobo":1000,"days":1},
    "weekly": {"label":"Weekly - GHS 49","price":49,"kobo":4900,"days":7},
    "monthly": {"label":"Monthly - GHS 99","price":99,"kobo":9900,"days":30}
}

PAGE_B64 = "PCFkb2N0eXBlIGh0bWw+PGh0bWw+PGhlYWQ+PG1ldGEgY2hhcnNldD0idXRmLTgiPjxtZXRhIG5hbWU9InZpZXdwb3J0IiBjb250ZW50PSJ3aWR0aD1kZXZpY2Utd2lkdGgsaW5pdGlhbC1zY2FsZT0xIj48dGl0bGU+RXhxdWlzaXRlIEFJPC90aXRsZT48c2NyaXB0IHNyYz0iaHR0cHM6Ly9qcy5wYXlzdGFjay5jby92MS9pbmxpbmUuanMiPjwvc2NyaXB0PjxzdHlsZT5ib2R5e21hcmdpbjowO2JhY2tncm91bmQ6IzBmMGYxODtjb2xvcjojZjVmMmZhO2ZvbnQtZmFtaWx5OkludGVyLHNhbnMtc2VyaWZ9LnNoZWxse3dpZHRoOm1pbigxMDUwcHgsY2FsYygxMDAlIC0gMzJweCkpO21hcmdpbjowIGF1dG87cGFkZGluZzoyNHB4IDB9LmNhcmR7YmFja2dyb3VuZDojMTkxOTIzO2JvcmRlcjoxcHggc29saWQgcmdiYSgyNTUsMjU1LDI1NSwuMTIpO2JvcmRlci1yYWRpdXM6MjBweDtwYWRkaW5nOjIwcHg7bWFyZ2luOjE4cHggMH0uYnV0dG9uLnByaW1hcnl7YmFja2dyb3VuZDojYmRhMGZmO2NvbG9yOiMxMTE7Ym9yZGVyOjA7Ym9yZGVyLXJhZGl1czoxMnB4O3BhZGRpbmc6MTJweCAyMHB4O2ZvbnQtd2VpZ2h0OjgwMDtjdXJzb3I6cG9pbnRlcn0uYnV0dG9uLnByaW1hcnkuaGlkZGVue2Rpc3BsYXk6bm9uZSFpbXBvcnRhbnR9dGV4dGFyZWF7d2lkdGg6MTAwJTtwYWRkaW5nOjE2cHg7Ym9yZGVyLXJhZGl1czoxNHB4O2JvcmRlcjoxcHggc29saWQgcmdiYSgyNTUsMjU1LDI1NSwuMTUpO2JhY2tncm91bmQ6IzExMTExYTtjb2xvcjojZmZmO2ZvbnQtc2l6ZToxNXB4O291dGxpbmU6bm9uZTtib3gtc2l6aW5nOmJvcmRlci1ib3h9dGV4dGFyZWE6Zm9jdXN7Ym9yZGVyLWNvbG9yOiNiZGEwZmZ9LnRhYntib3JkZXI6MXB4IHNvbGlkIHJnYmEoMjU1LDI1NSwyNTUsLC4xMik7YmFja2dyb3VuZDojMTgxODI1O2NvbG9yOiNhNGExYjI7cGFkZGluZzo5cHggMTZweDtib3JkZXItcmFkaXVzOjk5OXB4O2ZvbnQtc2l6ZToxM3B4O2N1cnNvcjpwb2ludGVyO21hcmdpbjozcHh9LnRhYi5hY3RpdmV7YmFja2dyb3VuZDojYmRhMGZmO2NvbG9yOiMxMTE7Zm9udC13ZWlnaHQ6NzAwfSNyZXN1bHR7bGluZS1oZWlnaHQ6MS43NTt3aGl0ZS1zcGFjZTpwcmUtd3JhcDtiYWNrZ3JvdW5kOiMxMTExMWE7Ym9yZGVyLXJhZGl1czoxNHB4O3BhZGRpbmc6MThweDttaW4taGVpZ2h0OjcwcHg7cG9zaXRpb246cmVsYXRpdmU7Ym9yZGVyOjFweCBzb2xpZCByZ2JhKDI1NSwyNTUsMjU1LC4wNil9LmNvcHktYnRue3Bvc2l0aW9uOmFic29sdXRlO3RvcDoxMHB4O3JpZ2h0OjEwcHg7YmFja2dyb3VuZDojMjMyMzJmO2JvcmRlcjoxcHggc29saWQgcmdiYSgyNTUsMjU1LDI1NSwuMTIpO2NvbG9yOiNhNGExYjI7Ym9yZGVyLXJhZGl1czo4cHg7cGFkZGluZzo2cHggMTBweDtmb250LXNpemU6MTJweDtjdXJzb3I6cG9pbnRlcn0uYmFkZ2V7ZGlzcGxheTppbmxpbmUtYmxvY2s7YmFja2dyb3VuZDpyZ2JhKDE4OSwxNjAsMjU1LC4xNSk7Ym9yZGVyOjFweCBzb2xpZCByZ2JhKDE4OSwxNjAsMjU1LC4zKTtjb2xvcjojYmRhMGZmO2JvcmRlci1yYWRpdXM6OTk5cHg7cGFkZGluZzozcHggMTBweDtmb250LXNpemU6MTFweDttYXJnaW4tYm90dG9tOjEwcHh9PC9zdHlsZT48L2hlYWQ+PGJvZHk+PGRpdiBjbGFzcz0ic2hlbGwiPjxoMSBzdHlsZT0idGV4dC1hbGlnbjpjZW50ZXI7bWFyZ2luOjhweCAwIj5XaGVyZSBJZGVhcyBUYWtlIEZsaWdodDwvaDE+PHAgc3R5bGU9InRleHQtYWxpZ246Y2VudGVyO2NvbG9yOiNhNGExYjI7Zm9udC1zaXplOjEzcHg7bWFyZ2luOjAgMCAxMHB4Ij5Bc2sgYW55dGhpbmcgbGlrZSBHZW1pbmkgLSBtYXRoLCBjb2RlLCBidXNpbmVzcywgaGVhbHRoPC9wPjxkaXYgc3R5bGU9InRleHQtYWxpZ246Y2VudGVyO21hcmdpbjoxNHB4IDAiPjxidXR0b24gY2xhc3M9InRhYiBhY3RpdmUiIGlkPSJ0YWItYWxsIiBvbmNsaWNrPSJzZXRUeXBlKCdhbGwnKSI+QWxsPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0idGFiIiBpZD0idGFiLWNhcHRpb25zIiBvbmNsaWNrPSJzZXRUeXBlKCdjYXB0aW9ucycpIj5DYXB0aW9uczwvYnV0dG9uPjxidXR0b24gY2xhc3M9InRhYiIgaWQ9InRhYi1zY3JpcHRzIiBvbmNsaWNrPSJzZXRUeXBlKCdzY3JpcHRzJykiPlNjcmlwdHM8L2J1dHRvbj48YnV0dG9uIGNsYXNzPSJ0YWIiIGlkPSJ0YWItc3RvcmllcyIgb25jbGljaz0ic2V0VHlwZSgnc3RvcmllcycpIj5TdG9yaWVzPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0idGFiIiBpZD0idGFiLWltYWdlcyIgb25jbGljaz0ic2V0VHlwZSgnaW1hZ2VzJykiPkltYWdlczwvYnV0dG9uPjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQiPjxkaXYgY2xhc3M9ImJhZGdlIiBpZD0ibW9kZUJhZGdlIj5Nb2RlOiBBbGwgLSBHZW5lcmFsIEFJPC9kaXY+PHRleHRhcmVhIGlkPSJwcm9tcHQiIHJvd3M9IjQiIHBsYWNlaG9sZGVyPSJBc2sgYW55dGhpbmc6IEJlc3QgYnVzaW5lc3MgaW4gR2hhbmE/IFdoYXQgaXMgQUk/IFNvbHZlIDJ4KzU9MTU/IiBvbmZvY3VzPSJzaG93QnV0dG9uKCkiIG9uaW5wdXQ9InNob3dCdXR0b24oKSI+PC90ZXh0YXJlYT48YnI+PGJyPjxidXR0b24gY2xhc3M9InByaW1hcnkgaGlkZGVuIiBpZD0iZmxpZ2h0QnRuIiBvbmNsaWNrPSJnZW5lcmF0ZSgpIj5MZXQgSXQgVGFrZSBGbGlnaHQ8L2J1dHRvbj48ZGl2IGlkPSJyZXN1bHQiIHN0eWxlPSJtYXJnaW4tdG9wOjE2cHgiPjxzcGFuIHN0eWxlPSJjb2xvcjojYTRhMWIyIj5Zb3VyIGFuc3dlciB3aWxsIGFwcGVhciBoZXJlLi4uPC9zcGFuPjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQiPjxoMyBzdHlsZT0ibWFyZ2luOjAgMCAxMHB4Ij5VbmxvY2sgVW5saW1pdGVkPC9oMz48ZGl2IGlkPSJwbGFucyI+PC9kaXY+PGRpdiBpZD0icXVvdGEiIHN0eWxlPSJtYXJnaW4tdG9wOjEwcHg7Y29sb3I6I2E0YTFiMjtmb250LXNpemU6MTNweCI+PC9kaXY+PC9kaXY+PC9kaXY+PHNjcmlwdD5sZXQgUFVCTElDX0tFWT0iX19QVUJMSUNfS0VZX18iO2xldCBjdXJyZW50VHlwZT0iYWxsIjtmdW5jdGlvbiBzaG93QnV0dG9uKCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImZsaWdodEJ0biIpLmNsYXNzTGlzdC5yZW1vdmUoImhpZGRlbiIpO31mdW5jdGlvbiBoaWRlQnV0dG9uKCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImZsaWdodEJ0biIpLmNsYXNzTGlzdC5hZGQoImhpZGRlbiIpO31mdW5jdGlvbiBzZXRUeXBlKHQpe2N1cnJlbnRUeXBlPXQ7ZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgiLnRhYiIpLmZvckVhY2goYj0+Yy5jbGFzc0xpc3QucmVtb3ZlKCJhY3RpdmUiKSk7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInRhYi0iK3QpLmNsYXNzTGlzdC5hZGQoImFjdGl2ZSIpO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJtb2RlQmFkZ2UiKS5pbm5lclRleHQ9Ik1vZGU6ICIrdDt2YXIgcHI9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInByb21wdCIpLnZhbHVlLnRyaW0oKTtpZihwci5sZW5ndGg+Mil7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInJlc3VsdCIpLmlubmVySFRNTD0iU3dpdGNoaW5nIHRvICIrdCsiLi4uIjtoaWRlQnV0dG9uKCk7Z2VuZXJhdGUoKTt9fWFzeW5jIGZ1bmN0aW9uIHJlZnJlc2hRdW90YSgpe3RyeXtsZXQgcj1hd2FpdCBmZXRjaCgiL2FwaS9tZSIpO2xldCBkPWF3YWl
