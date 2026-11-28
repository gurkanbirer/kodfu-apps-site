#!/usr/bin/env python3
"""Check a generated site's links. No dependencies.

    python3 tools/linkcheck.py fareback            # every internal href/src (and #anchor) in fareback/ resolves
    python3 tools/linkcheck.py fareback --live     # also: every sitemap URL on the live host answers 200
    python3 tools/linkcheck.py fareback --live --external   # also HEAD/GET every external link (slow; many
                                                   # train company sites block scripts with 403, which is reported, not failed)

Exit status 1 if an internal link, anchor or live sitemap URL is broken. Run after tools/build.py and after a
deploy (docs/deployment.md).
"""
import html.parser
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (compatible; kodfu-apps-site linkcheck)"


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        for k in ("href", "src"):
            if a.get(k) and not (tag == "link" and a.get("rel") == "canonical"):
                self.links.append(a[k])


def parse(path):
    p = Links()
    p.feed(open(path, encoding="utf-8").read())
    return p


def target_file(base_dir, href):
    path = href.split("#")[0].split("?")[0]
    if not path:
        return None
    f = os.path.normpath(os.path.join(base_dir, path))
    if os.path.isdir(f):
        f = os.path.join(f, "index.html")
    return f


def fetch(url, method="GET"):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read() if method == "GET" else b""
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:  # noqa: BLE001 - report any network error
        return str(e)[:60], b""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    live, external = "--live" in sys.argv, "--external" in sys.argv
    if len(args) != 1:
        raise SystemExit(__doc__)
    site = os.path.join(ROOT, args[0])
    pages, bad, ext = {}, [], set()
    for d, _, files in os.walk(site):
        for n in files:
            if n.endswith(".html"):
                pages[os.path.join(d, n)] = parse(os.path.join(d, n))
    for f, p in sorted(pages.items()):
        if f.endswith("404.html"):   # served at any depth with root-absolute links
            continue
        for href in p.links:
            if re.match(r"^(https?:|mailto:|data:)", href):
                if href.startswith("http") and "play.google.com" not in href:
                    ext.add(href)
                continue
            t = target_file(os.path.dirname(f), href) if not href.startswith("#") else f
            frag = href.split("#", 1)[1] if "#" in href else ""
            if t and not os.path.exists(t):
                bad.append(f"{os.path.relpath(f, ROOT)}: {href} (no file)")
            elif frag and t and t.endswith(".html") and frag not in pages.get(t, parse(t)).ids:
                bad.append(f"{os.path.relpath(f, ROOT)}: {href} (no id '{frag}')")
    print(f"{args[0]}: {len(pages)} HTML files, {sum(len(p.links) for p in pages.values())} links, {len(bad)} broken internal")
    for b in bad:
        print("  BROKEN", b)
    if live:
        sm = open(os.path.join(site, "sitemap.xml"), encoding="utf-8").read()
        urls = re.findall(r"<loc>(.*?)</loc>", sm)
        fails = 0
        for u in urls:
            st, _ = fetch(u)
            if st != 200:
                fails += 1
                print(f"  LIVE {st} {u}")
        print(f"live: {len(urls) - fails}/{len(urls)} sitemap URLs answer 200")
        bad += ["live"] * fails
    if external:
        blocked = 0
        for u in sorted(ext):
            st, _ = fetch(u, "HEAD")
            if st in (405, 403, 400) or not isinstance(st, int):
                st2, _ = fetch(u)
                st = st2 if isinstance(st2, int) and st2 < 400 else st
            if st in (403, 429):
                blocked += 1
            elif not (isinstance(st, int) and st < 400):
                print(f"  EXTERNAL {st} {u}")
        print(f"external: {len(ext)} links checked ({blocked} refused automated requests: check those in a browser)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
