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
The conversion placeholders (`~play:<position>`, `<!--appcta-->`, `<!--after-questions:…-->`,
`<!--shots:…-->`, `<!--hero-->`, `{{count:…}}`) are listed at the top of `tools/build.py`.

## Conversion system and Play install referrer (27/11/2026)

Owner decision 27/11/2026 (`~/Code/exam-apps/AGENTS.md`): the only goal is Google Play installs and Pro
purchases. Every page has the app's colours and mark in the header, a one-line pitch and a Play button
above the fold (on phones a sticky bottom bar, CSS only, hidden from 760px up), CTAs inside and after
the content, and app screenshots (`src/<app>/screens/*.webp`, 480×853, made from
`~/Code/exam-apps/store/<app>/screenshots/android/`). Question counts in CTAs come from the shipped
bundles at build time (`{{count:…}}` tokens), never typed by hand. No App Store links while the iOS
release is on hold; pages say "Android now; iPhone version not yet available."

Every Play link is made by `play_link()` in `tools/build.py`. Never type a store URL in a fragment:
write `href="~play:<position>"` (a plain store URL is rewritten with position `inline`).

```
https://play.google.com/store/apps/details?id=<pkg>&referrer=utm_source%3D<host>%26utm_medium%3Dsite%26utm_campaign%3D<page>%26utm_content%3D<position>
```

| Field | Value |
| --- | --- |
| `utm_source` | the site's host: `sparkwiseapp.co.uk`, `bluebell.kodfu.com`, `hivis.kodfu.com`, `fareback.kodfu.com`, `tickover.kodfu.com` (the GitHub Pages copy reports the same source) |
| `utm_medium` | `site` |
| `utm_campaign` | the page: `home`, `18th-edition-exam`, `practice-18th-edition-shock-protection`, `guide`, `404` … (URL path, `/` → `-`) |
| `utm_content` | the button: `hero` (top of page / home hero), `sticky` (mobile bar), `inline-<topic>` (box inside a guide or index), `after-questions` (practice pages), `footer` (closing card), `free-pro` and `home-screens` (home page), `faq-answer` |

Where to read it: Play Console → the app → **Grow users → Store performance → Store listing
acquisition** (older menus: Statistics / User acquisition → Acquisition reports), traffic source
**Third-party referrals**, broken down by **UTM source** and **UTM campaign**: store listing visitors,
installers and conversion rate per site and page. Play Console shows source and campaign but not
`utm_content`, so `UTM_POSITION_IN_CAMPAIGN = True` in `tools/build.py` (since 27/11/2026) makes the
campaign `<page>--<position>` (e.g. `home--hero`); add up the rows with the same `<page>` prefix for
a page total. Play does not report Pro
purchases per source; compare installers per page with total Pro sales. The sites still have no
analytics, cookies or trackers.

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
  page carries the brand disclaimer (Sparkwise, since 28/11/2026: "Not affiliated with or endorsed
  by the IET, BSI, City & Guilds, EAL, NET, the ECS, the JIB, NICEIC, NAPIT, MCS, HSE or OZEV", the
  bodies the 1.2.0 paywall names). Tickover must not promise plate lookup or MOT history (plate lookup is
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

## Sparkwise exam pages (1.2.0, 28/11/2026)

Sparkwise 1.2.0 sells each new exam on its own inside the one app (owner decision 27/11/2026 in
`~/Code/exam-apps/AGENTS.md`; product ids and prices in `~/Code/exam-apps/config/sparkwise.json` `PRODUCTS`):
PAT 2377 £7.99, EV 2921-34 £7.99, 2391-52 + 2391-50 + 2391-51 £9.99, ECS ESU £7.99, AM2 knowledge £9.99,
EWA entry test £7.99, solar PV 2922 + battery 2923 £7.99; Pro £12.99 still covers 18th Edition + ECS HS&E;
All exams £24.99. `PACKS` in `tools/build.py` holds each pack's page, price, sources and screenshots, and a
fragment with `pack: <key>` gets that pack's sticky bar, app boxes, closing card and sources. Counts are
unique question ids (`{{count:a|b}}`), never sums of shared topic files. The pages wait for 1.2.0 on Play:
see the deploy gate in `docs/seo-strategy.md`.

Educated guesses (28/11/2026, site session; the owner can override):
- URLs name the exam and its code: `/pat-testing-exam-2377/`, `/ev-charging-exam-2921/`,
  `/inspection-testing-exam-2391/` (one page for all three 2391 exams, as they are one unlock),
  `/ecs-electrical-safety-unit/`, `/am2-knowledge-test/`, `/ewa-entry-test/`,
  `/solar-pv-battery-exam-2922-2923/` (one page, one unlock), and a hub `/exams/` ("All 12 exams" in the nav).
- Each page: crumb, h1 for the search, Play button + "try free questions" anchor, the real format (with the
  awarding body's page linked), what the exam covers (real question split where published + app counts),
  a free sample of 8 to 10 shipped questions (one per topic, picked by the build; `ids=` pins them), the
  "You've seen N of M" card, how to prepare, 4 to 5 FAQ (FAQPage JSON-LD), the pack's closing card and a
  sources card headed "Where the exam facts come from" (the copy rule for these pages bans the word
  "official"; older pages keep their "Official sources" card).
- Screenshots: real 1.2.0 emulator screens (`/private/tmp/claude-501/sparkwise-test/`, 1080×2400) resized
  to 480×1067 WebP (`src/sparkwise/screens/11-*`, `2x-pat-*`, `3x-am2-*`, `4x-ewa-*`, `50-2391-paywall`);
  `screens` entries carry their size. EV, ESU, 2391 and solar have no screens of their own yet, so they show
  the exam switcher, a PAT or AM2 answered question and the PAT/2391 unlock screen, with honest alt text.
  Replace them with exam-specific shots when the store screenshots for those exams exist.
- Pass marks that the awarding body gives only as "about 75%" (2921, 2391, 2922/2923) are written that way;
  the app's mock cut-off is named as Sparkwise's. AM2 Section E: NET does not publish a pass mark, so the
  page says so and calls the app's 32/45 a working figure.
- Mobile layout: tables of 3 columns at most; the exam list on `/exams/` is a link list, not a table.
