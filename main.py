import json, os, uuid, time, urllib.parse, urllib.request, base64
from flask import Flask, jsonify, request, make_response

app = Flask(__name__)
PUB = os.environ.get("PAYSTACK_PUBLIC_KEY","")
SEC = os.environ.get("PAYSTACK_SECRET_KEY","")
POLL = os.environ.get("POLLINATIONS_TOKEN","")
FREE = 25

def load_data():
    try:
        return json.load(open("data.json","r"))
    except:
        return {"users":{}}

def save_data(d):
    try:
        json.dump(d, open("data.json","w"))
    except:
        pass

def get_uid():
    u = request.cookies.get("uid")
    if not u:
        u = str(uuid.uuid4())
    return u

B64_HTML = (
    "PCFkb2N0eXBlIGh0bWw+PGh0bWw+PGhlYWQ+PG1ldGEgY2hhcnNldD11dGYt"
    "OD4KPG1ldGEgbmFtZT12aWV3cG9ydCBjb250ZW50PSJ3aWR0aD1kZXZpY2U"
    "td2lkdGgsaW5pdGlhbC1zY2FsZT0xIj4KPHRpdGxlPkV4cXVpc2l0ZSBBST"
    "wvdGl0bGU+CjxzY3JpcHQgc3JjPSJodHRwczovL2pzLnBheXN0YWNrLmNv"
    "L3YxL2lubGluZS5qcyI+PC9zY3JpcHQ+C
