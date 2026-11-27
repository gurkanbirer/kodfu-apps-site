# Deployment: the Kodfu app sites

Single source of truth for how the five app websites are built and published. Fix it here if a step
is wrong. Owner decision 26/11/2026 (recorded in `~/Code/exam-apps/AGENTS.md`): Sparkwise gets its own
domain, the other four apps get `kodfu.com` subdomains, and these sites replace the GitHub Pages pages.

## What runs where

| Site | URL | DNS | TLS |
| --- | --- | --- | --- |
| Sparkwise | https://sparkwiseapp.co.uk (www → apex 301) | Cloudflare zone `ccac39aafcbfd2a9317712d2fe649314` (Registrar, bought 26/11/2026, NS `mariah`/`phil.ns.cloudflare.com`): proxied `A` apex + `www` → 65.108.102.251 | Cloudflare edge; origin: Cloudflare Origin CA cert (apex + `*.sparkwiseapp.co.uk`, RSA, to 22/11/2041) + Authenticated Origin Pulls |
| Bluebell | https://bluebell.kodfu.com | GoDaddy `A bluebell` → 65.108.102.251, TTL 600 | box `*.kodfu.com` wildcard (Let's Encrypt, certbot + GoDaddy DNS-01, renews itself) |
| HiVis | https://hivis.kodfu.com | GoDaddy `A hivis` → 65.108.102.251 | same wildcard |
| Tickover | https://tickover.kodfu.com | GoDaddy `A tickover` → 65.108.102.251 | same wildcard |
| FareBack | https://fareback.kodfu.com | GoDaddy `A fareback` → 65.108.102.251 | same wildcard |

| Piece | Where |
| --- | --- |
| Source | `src/<app>/` page fragments (+ `*.questions.json`, `mark.svg`) and `tools/build.py` (layout, CSS, nav, footer, practice pages, sitemap, robots, 404, JSON-LD). Practice questions for Sparkwise and HiVis come from the shipped bundles `~/Code/exam-apps/app/assets/content/{sparkwise,hivis}.json`; ids marked `verify: true` in `~/Code/exam-apps/content/` are dropped again by the build. |
| Output | `<app>/` folders (generated, committed). Never edit them by hand: `python3 tools/build.py` deletes and rewrites every `index.html` in them. |
| Server | `kodfu-box` (Hetzner 65.108.102.251, SSH alias, port 2244, root). Files in `/srv/kodfu-apps-site/<app>/releases/<utc>-<sha>`, `/srv/kodfu-apps-site/<app>/current` → latest; last 5 releases kept. Nothing is built on the server. |
| nginx | `/etc/nginx/sites-available/{sparkwiseapp.co.uk,bluebell.kodfu.com,hivis.kodfu.com,tickover.kodfu.com,fareback.kodfu.com}` (+ `sites-enabled` links) ← `deploy/nginx/*.conf`. Static files only, `error_page 404 /404.html`, `access_log off` (the sites promise no tracking), error logs `/var/log/nginx/kodfu-apps-<app>.error.log`. Security headers incl. a CSP with no scripts (`default-src 'none'; style-src 'self'`): the pages must stay script-free (JSON-LD data blocks are fine). Shared nginx (~30 sites): only `nginx -t && nginx -s reload`, never restart, never touch another vhost. |
| Origin cert (Sparkwise) | `/etc/nginx/sparkwiseapp/cf-origin.{pem,key}` + `cf-origin-pull-ca.pem` (root 0600, dir 0700). Mac copy `~/.config/sparkwiseapp/origin/` (0600). Made by `deploy/cloudflare.py origin-cert`. |
| Cloudflare settings | SSL Full (Strict), Always Use HTTPS, min TLS 1.2, Authenticated Origin Pulls (`tls_client_auth` on), Network Error Logging off, dynamic redirect `www` → apex 301 (path + query kept). All by `deploy/cloudflare.py`; token `~/.cf-registrar-token`, account `dcb9230736f5416b025beb759bd5eebb`. |
| GoDaddy | API key on the box (`/root/.secrets/godaddy.ini`); `deploy/godaddy-a.sh` runs there. The `*.kodfu.com` wildcard points at another server (159.69.203.206, answers 200 for any name), so **never delete these A records**; to retire a host, replace its A with a TXT (see cambridgecitytaxi in `~/Code/cambridge-city-taxi/docs/deployment.md`). |
| GitHub Pages | Still on (`gurkanbirer/kodfu-apps-site`, branch `main`, root): the live apps still link `https://gurkanbirer.github.io/kodfu-apps-site/<app>/`. It serves the same generated files; every page's `<link rel="canonical">` points at the new host, so search engines move there. Switch Pages off only after the apps, store listings and Data safety point to the new hosts (owner decision 26/11/2026). |

## Publish a change

```bash
python3 tools/build.py            # regenerate the <app>/ folders from src/
git add -A && git commit -m "..." # a release ships the committed HEAD, never the working tree
deploy/deploy.sh                  # all five (or: deploy/deploy.sh sparkwise hivis)
deploy/deploy.sh check            # 200 + ssl_verify=0 for /, /privacy/, /terms/, sitemap, robots; www 301
git push                          # GitHub Pages copy (and backup)
deploy/deploy.sh rollback <app>   # back to that app's previous release
```

Links inside a site are written `~/path/` in fragments; the build makes them relative, so the same
files work at `https://<host>/` and at `https://gurkanbirer.github.io/kodfu-apps-site/<app>/`.
Placeholders: `<!--cta-->` (store card), `<!--sources-->` (official sources), `<!--questions-->`
(renders `<page>.questions.json`). FAQ items `<h3 class="faq-q">…</h3><div class="faq-a">…</div>`
become FAQPage JSON-LD. Home pages carry SoftwareApplication + WebSite JSON-LD, other pages a
BreadcrumbList.

## From nothing (order matters)

```bash
python3 deploy/cloudflare.py dns           # Sparkwise: proxied A apex + www
python3 deploy/cloudflare.py origin-cert   # Origin CA cert -> kodfu-box
deploy/godaddy-a.sh                        # A bluebell|hivis|tickover|fareback -> 65.108.102.251
deploy/deploy.sh                           # releases (dirs must exist before the vhosts serve)
deploy/deploy.sh nginx                     # five vhosts, one nginx -t + reload
python3 deploy/cloudflare.py settings      # Full (Strict), Always HTTPS, TLS 1.2, AOP
python3 deploy/cloudflare.py redirect      # www -> apex 301
deploy/deploy.sh check
```

## Content rules (owner conventions)

- Privacy policies and terms stay legally identical in substance; only factual errors are fixed, and
  the page's "Last updated" date moves when its text changes.
- Exam sites: never imply official status, no logos, never copy BS 7671 / handbook / official
  question-bank text, never promise a pass; only shipped (verified) questions are published; every
  page carries the brand disclaimer (Sparkwise: "Not affiliated with or endorsed by the IET, BSI,
  City & Guilds, ECS or JIB"). Tickover must not promise plate lookup or MOT history (plate lookup is
  unavailable, `~/Code/tickover/docs/api-access.md`). FareBack's `/#delete` section is linked from
  Google Play's data-deletion field: keep the id.
- No cookies, analytics or trackers; support email gurkancaner@kodfu.com everywhere.

## Search Console

Sparkwise: Domain property `sparkwiseapp.co.uk`, verified by a DNS TXT record on the apex
(`python3 deploy/cloudflare.py txt 'google-site-verification=…'`). The kodfu.com subdomains: URL-prefix
properties (or the `kodfu.com` Domain property, verified by a GoDaddy TXT). The token comes from the
Search Console UI (owner's Google account). Submit each `https://<host>/sitemap.xml`.

## History

- 04/11/2026: support, privacy and terms pages on GitHub Pages (`gurkanbirer.github.io/kodfu-apps-site`).
- 26/11/2026: Pages switched off, then back on the same day as a temporary host.
- 27/11/2026: the five sites go live on kodfu-box (this runbook); Pages kept, with canonical links to the new hosts.

## Google Search Console (27/11/2026)

Account `info.kodfu@gmail.com`. Domain property `sc-domain:sparkwiseapp.co.uk`, verified by a DNS TXT record in the
Cloudflare zone (`deploy/cloudflare.py txt …`; keep the record). URL-prefix properties `https://bluebell.kodfu.com/`,
`https://hivis.kodfu.com/`, `https://fareback.kodfu.com/`, `https://tickover.kodfu.com/`, verified by the HTML file
`googleea66026b8981bf38.html`: it lives at the repo root and `tools/build.py` copies it to every host's root. Do not delete
it, or those properties lose verification. Every host's `sitemap.xml` is submitted.
