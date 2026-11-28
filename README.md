# kodfu-apps-site

Websites for the Kodfu UK apps (owner decision 26/11/2026):

| App | Site |
| --- | --- |
| Sparkwise | https://sparkwiseapp.co.uk |
| Bluebell | https://bluebell.kodfu.com |
| HiVis | https://hivis.kodfu.com |
| Tickover | https://tickover.kodfu.com |
| FareBack | https://fareback.kodfu.com (moving to https://fareback.co.uk: `docs/deployment.md`) |

Each has `/` (about the app), `/privacy/`, `/terms/` and content pages (guides, free practice). FareBack is a full
rail passenger-rights site (one page per train company and per right, built from `src/fareback/operators.json`).
The same generated files are also served by GitHub Pages at
`https://gurkanbirer.github.io/kodfu-apps-site/<app>/` (temporary; canonical links point to the new hosts).

Edit `src/<app>/` and run `python3 tools/build.py`; never edit the generated `<app>/` folders by hand.
`python3 tools/linkcheck.py <app>` checks every internal link and anchor (`--live` also every sitemap URL on the host).
Hosting, DNS, certificates and how to deploy: `docs/deployment.md`.
Plain static HTML/CSS, en-GB, light/dark, no scripts, cookies, analytics or trackers.
Goal: Google Play installs and Pro purchases (owner decision 27/11/2026). Every Play link carries an
install referrer naming the page and the button; the scheme and where to read it: `docs/deployment.md`.
