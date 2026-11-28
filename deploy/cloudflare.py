#!/usr/bin/env python3
"""Cloudflare for the Kodfu app sites on their own domains: sparkwiseapp.co.uk (default) and, from the
switch-over, fareback.co.uk. Same pattern as madebyada.co.uk and cambridgelicensedtaxis.co.uk on kodfu-box.
Runbook: docs/deployment.md.

Token: ~/.cf-registrar-token (account dcb9230736f5416b025beb759bd5eebb: Registrar, Zone, DNS,
settings, Dynamic Redirect, Origin CA). Every step is idempotent; on a fresh name, in order:

  python3 deploy/cloudflare.py [--domain D] dns          # proxied A apex + www -> 65.108.102.251
  python3 deploy/cloudflare.py [--domain D] origin-cert  # Origin CA cert (apex + *.apex, 15 y) -> kodfu-box
  deploy/deploy.sh nginx                                 # vhosts (need the cert on the box)
  python3 deploy/cloudflare.py [--domain D] settings     # SSL Full (Strict), Always HTTPS, min TLS 1.2, AOP
  python3 deploy/cloudflare.py [--domain D] redirect     # www -> apex 301
  python3 deploy/cloudflare.py [--domain D] status       # read-only summary
  python3 deploy/cloudflare.py [--domain D] txt 'google-site-verification=...'   # apex TXT (Search Console)

The domain is `--domain <name>` or the CF_DOMAIN environment variable; without either it is
sparkwiseapp.co.uk, so the Sparkwise commands behave exactly as before. Per domain, with <short> the first label
(sparkwiseapp, fareback): box files in /etc/nginx/<short>/ (root, 0700 dir, 0600 files), Mac copy of the
origin key and cert in ~/.config/<short>/origin/ (0700 dir, 0600 files); the private key is never printed.

sparkwiseapp.co.uk: bought 26/11/2026 through Cloudflare Registrar (zone ccac39aafcbfd2a9317712d2fe649314).
fareback.co.uk: bought by the coordinator through Cloudflare Registrar after the owner confirms the price
(owner decision 28/11/2026); nothing here buys a name.
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

def _domain_arg():
    """--domain <name> (removed from argv) or CF_DOMAIN; default sparkwiseapp.co.uk."""
    if "--domain" in sys.argv:
        i = sys.argv.index("--domain")
        if i + 1 >= len(sys.argv):
            raise SystemExit("--domain needs a name, e.g. --domain fareback.co.uk")
        name = sys.argv[i + 1]
        del sys.argv[i:i + 2]
        return name
    return os.environ.get("CF_DOMAIN", "sparkwiseapp.co.uk")


DOMAIN = _domain_arg().strip().lower().rstrip(".")
SHORT = DOMAIN.split(".")[0]          # sparkwiseapp.co.uk -> sparkwiseapp, fareback.co.uk -> fareback
ACCOUNT = "dcb9230736f5416b025beb759bd5eebb"
IP = "65.108.102.251"
TARGET = os.environ.get("TARGET", "kodfu-box")
BOX_DIR = f"/etc/nginx/{SHORT}"
LOCAL_DIR = os.path.expanduser(f"~/.config/{SHORT}/origin")
TOKEN = open(os.path.expanduser("~/.cf-registrar-token")).read().strip()


def cf(method, path, body=None):
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4" + path,
        data=None if body is None else json.dumps(body).encode(),
        method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        out = json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        out = json.loads(e.read() or b"{}")
        out["http"] = e.code
    if not out.get("success"):
        raise SystemExit(f"Cloudflare {method} {path} failed: HTTP {out.get('http')} {out.get('errors')}")
    return out["result"]


_zone = None


def zone():
    global _zone
    if _zone is None:
        z = cf("GET", f"/zones?name={DOMAIN}")
        if not z:
            raise SystemExit(f"no Cloudflare zone for {DOMAIN} yet (the coordinator buys the name first)")
        _zone = z[0]["id"]
    return _zone








def dns():
    existing = cf("GET", f"/zones/{zone()}/dns_records?per_page=100")
    for name in (DOMAIN, f"www.{DOMAIN}"):
        want = {"type": "A", "name": name, "content": IP, "proxied": True, "ttl": 1}
        cur = [r for r in existing if r["name"] == name and r["type"] in ("A", "AAAA", "CNAME")]
        if len(cur) == 1 and cur[0]["type"] == "A" and cur[0]["content"] == IP and cur[0]["proxied"]:
            print(f"A {name} → {IP} (proxied) ok")
            continue
        for r in cur:
            cf("DELETE", f"/zones/{zone()}/dns_records/{r['id']}")
        cf("POST", f"/zones/{zone()}/dns_records", want)
        print(f"A {name} → {IP} (proxied) created")


def origin_cert():
    os.makedirs(LOCAL_DIR, mode=0o700, exist_ok=True)
    key, pem = os.path.join(LOCAL_DIR, "cf-origin.key"), os.path.join(LOCAL_DIR, "cf-origin.pem")
    if not (os.path.exists(key) and os.path.exists(pem)):
        with tempfile.TemporaryDirectory() as tmp:
            csr = os.path.join(tmp, "req.csr")
            old = os.umask(0o077)
            try:
                subprocess.run(
                    ["openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", csr,
                     "-subj", f"/CN={DOMAIN}"],
                    check=True, capture_output=True,
                )
            finally:
                os.umask(old)
            res = cf("POST", "/certificates", {
                "hostnames": [DOMAIN, f"*.{DOMAIN}"],
                "requested_validity": 5475,
                "request_type": "origin-rsa",
                "csr": open(csr).read(),
            })
        with open(pem, "w") as f:
            f.write(res["certificate"])
        os.chmod(pem, 0o600)
        print(f"Origin CA certificate issued (id {res['id']}, expires {res['expires_on']})")
    else:
        print("Origin CA certificate already on the Mac; reusing it")
    # To the box: cert + key (root 0600), and Cloudflare's origin-pull CA (the same public CA
    # Original Drivers verifies against on this box).
    subprocess.run(["ssh", TARGET, f"install -d -m 700 {BOX_DIR}"], check=True)
    for local, remote in ((pem, "cf-origin.pem"), (key, "cf-origin.key")):
        with open(local, "rb") as f:
            subprocess.run(["ssh", TARGET, f"umask 077; cat > {BOX_DIR}/{remote}"], stdin=f, check=True)
    subprocess.run(
        ["ssh", TARGET,
         f"umask 077; if [ -f /etc/nginx/originaldrivers/cf-origin-pull-ca.pem ]; then cp /etc/nginx/originaldrivers/cf-origin-pull-ca.pem {BOX_DIR}/; "
         f"else curl -fsS https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem -o {BOX_DIR}/cf-origin-pull-ca.pem; fi; "
         f"openssl x509 -in {BOX_DIR}/cf-origin.pem -noout -subject -enddate; "
         f"openssl x509 -in {BOX_DIR}/cf-origin-pull-ca.pem -noout -subject; stat -c '%U %a %n' {BOX_DIR}/*"],
        check=True,
    )


def settings():
    for key, value in (("ssl", "strict"), ("always_use_https", "on"), ("min_tls_version", "1.2"), ("tls_client_auth", "on")):
        cur = cf("GET", f"/zones/{zone()}/settings/{key}")["value"]
        if cur == value:
            print(f"{key} = {value} ok")
        else:
            cf("PATCH", f"/zones/{zone()}/settings/{key}", {"value": value})
            print(f"{key}: {cur} → {value}")
    # Network Error Logging off: browsers would otherwise send error reports to Cloudflare
    # (the site promises no trackers).
    cur = cf("GET", f"/zones/{zone()}/settings/nel")["value"]
    if cur.get("enabled"):
        cf("PATCH", f"/zones/{zone()}/settings/nel", {"value": {"enabled": False}})
        print("nel: on → off")
    else:
        print("nel = off ok")


def redirect():
    phase = "http_request_dynamic_redirect"
    rule = {
        "description": "www → apex (301, path + query kept)",
        "expression": f'(http.host eq "www.{DOMAIN}")',
        "action": "redirect",
        "action_parameters": {
            "from_value": {
                "status_code": 301,
                "target_url": {"expression": f'concat("https://{DOMAIN}", http.request.uri.path)'},
                "preserve_query_string": True,
            }
        },
        "enabled": True,
    }
    try:
        cur = cf("GET", f"/zones/{zone()}/rulesets/phases/{phase}/entrypoint")
        rules = [r for r in cur.get("rules", []) if r.get("description") != rule["description"]]
    except SystemExit:
        rules = []
    cf("PUT", f"/zones/{zone()}/rulesets/phases/{phase}/entrypoint", {"rules": rules + [rule]})
    print(f"dynamic redirect: www.{DOMAIN} → https://{DOMAIN}$path (301)")


def txt(value):
    existing = cf("GET", f"/zones/{zone()}/dns_records?type=TXT&name={DOMAIN}")
    if any(r["content"].strip('"') == value for r in existing):
        print(f"TXT {DOMAIN} {value} ok")
        return
    cf("POST", f"/zones/{zone()}/dns_records", {"type": "TXT", "name": DOMAIN, "content": value, "ttl": 1})
    print(f"TXT {DOMAIN} {value} created")


def status():
    print("zone:", cf("GET", f"/zones/{zone()}")["status"], cf("GET", f"/zones/{zone()}")["name_servers"])
    for r in cf("GET", f"/zones/{zone()}/dns_records?per_page=100"):
        print(f"  {r['type']:5} {r['name']:30} {r['content'][:50]:50} proxied={r.get('proxied')}")
    for key in ("ssl", "always_use_https", "min_tls_version", "tls_client_auth"):
        print(f"  {key} = {cf('GET', f'/zones/{zone()}/settings/{key}')['value']}")


if __name__ == "__main__":
    steps = {"dns": dns, "origin-cert": origin_cert,
             "settings": settings, "redirect": redirect, "status": status}
    if len(sys.argv) == 3 and sys.argv[1] == "txt":
        txt(sys.argv[2])
    elif len(sys.argv) != 2 or sys.argv[1] not in steps:
        raise SystemExit(f"usage: {sys.argv[0]} [--domain <name>] {'|'.join(steps)}|txt <value>")
    else:
        print(f"[{DOMAIN}]")
        steps[sys.argv[1]]()
