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
    html += "<meta name=viewport content='width=device-width,initial-scale=1'>"
    html += "<title>Exquisite AI</title>"
    html += "<script src=https://js.paystack.co/v1/inline.js></script>"
    html += "<style>body{background:#0f0f18;color:#fff;padding:20px;font-family:sans-serif}.card{background:#191923;padding:16px;margin:12px 0;border-radius:16px}textarea{width:100%;padding:12px;background:#111;color:#fff;border-radius:12px;border:1px solid #333}button{background:#bda0ff;color:#111;border:0;padding:10px 16px;border-radius:10px;font-weight:700}img.res-img{max-width:100%;border-radius:12px;margin-top:12px;display:block}.
