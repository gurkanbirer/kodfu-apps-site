#!/usr/bin/env bash
# Explicit GoDaddy A records (kodfu.com zone) for the four app subdomains -> kodfu-box.
# Runs on kodfu-box, which holds the GoDaddy API key (/root/.secrets/godaddy.ini).
# Needed because *.kodfu.com is a wildcard to another server (159.69.203.206).
#   deploy/godaddy-a.sh          create/refresh A bluebell|hivis|tickover|fareback -> 65.108.102.251, TTL 600
#   deploy/godaddy-a.sh show     read-only
set -euo pipefail
TARGET="${TARGET:-kodfu-box}"
MODE="${1:-set}"
ssh "$TARGET" "MODE=$MODE python3 -" <<'PY'
import json, os, urllib.request
c = dict(l.strip().split("=", 1) for l in open("/root/.secrets/godaddy.ini") if "=" in l)
c = {k.strip(): v.strip() for k, v in c.items()}
h = {"Authorization": "sso-key %s:%s" % (c["dns_godaddy_key"], c["dns_godaddy_secret"]), "Content-Type": "application/json"}
IP = "65.108.102.251"
for name in ("bluebell", "hivis", "tickover", "fareback"):
    url = f"https://api.godaddy.com/v1/domains/kodfu.com/records/A/{name}"
    cur = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=h)).read())
    if os.environ["MODE"] == "show" or (len(cur) == 1 and cur[0]["data"] == IP):
        print(name, "A", cur)
        continue
    req = urllib.request.Request(url, data=json.dumps([{"data": IP, "ttl": 600}]).encode(), headers=h, method="PUT")
    print(name, "A ->", IP, "HTTP", urllib.request.urlopen(req).status, "(was", cur, ")")
PY
