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

def get_page
