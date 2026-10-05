import json, os, sys, urllib.request, urllib.error

PROXY = "http://127.0.0.1:8787/v1/chat/completions"
KEY = os.environ.get("AGENTROUTER_API_KEY")
if not KEY:
    sys.exit("AGENTROUTER_API_KEY not set in environment")

req_file = sys.argv[1] if len(sys.argv) > 1 else None
count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
if not req_file:
    sys.exit("usage: AGENTROUTER_API_KEY=... python replay.py <req.json> [count]")

body = json.dumps(json.load(open(req_file))).encode()
h = {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + KEY,
    "Accept": "*/*",
    "Accept-Encoding": "identity",
}
for i in range(count):
    try:
        r = urllib.request.urlopen(urllib.request.Request(PROXY, body, h), timeout=180)
        print(f"attempt {i+1}: HTTP {r.status}")
        r.read(); r.close()
    except urllib.error.HTTPError as e:
        print(f"attempt {i+1}: HTTP {e.code} {e.read()[:300].decode('utf-8', 'replace')}")