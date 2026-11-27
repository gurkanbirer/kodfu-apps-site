# SEO strategy and daily routine (Kodfu UK app sites)

Owner decision 27/11/2026: SEO for these sites is important; a daily scheduled task
(`kodfu-apps-seo-gunluk`) works on it with full authority and never asks the owner. This file is what
that routine reads first on every run. Newer monthly reviews in `docs/seo-reviews/` override the
priorities below; the run log is `docs/seo-log.md`.

## Sites and goals

| Host | App (Google Play) | Goal | Weight |
|---|---|---|---|
| `https://sparkwiseapp.co.uk/` | Sparkwise `com.kodfu.sparkwise` (18th Edition C&G 2382-26, BS 7671:2018+A4:2026, ECS HS&E) | Organic UK searches → Play installs → Pro (£12.99). The only app with a sale (25/11/2026). | **Lead: most runs** |
| `https://bluebell.kodfu.com/` | Bluebell `com.kodfu.bluebell` (Life in the UK Test) | Very crowded market; long-tail practice and chapter pages. | Second |
| `https://hivis.kodfu.com/` | HiVis `com.kodfu.hivis` (CITB HS&E test for the CSCS card) | Long-tail topic practice pages, test guides. | Third |
| `https://fareback.kodfu.com/` | FareBack `com.kodfu.fareback` (Delay Repay claims; live rail data since 27/11/2026) | Delay Repay how-to guides per operator / route. | Occasional |
| `https://tickover.kodfu.com/` | Tickover: **unpublished 27/11/2026**, to be re-released by another company | None. Keep the pages up, do not invest. | — |

Search Console (account `info.kodfu@gmail.com`): `sc-domain:sparkwiseapp.co.uk` and URL-prefix
properties for the four `*.kodfu.com` hosts. Keyword research and competitor notes from the store
side: `~/Code/exam-apps/store/<brand>/aso.md` (Sparkwise, Bluebell, HiVis), `~/Code/fareback/store/aso.md`.

## What to build (priority order, until a monthly review says otherwise)

1. **Sparkwise topic depth.** Each `/practice/18th-edition/<topic>/` and `/practice/ecs-hse/<topic>/`
   page shows 10 shipped questions. Add supporting guide pages that target what electricians search:
   regulation-area explainers (e.g. RCD protection, earthing arrangements TN-C-S/TN-S/TT, zones in
   bathrooms, cable sizing and voltage drop worked examples, Zs and max earth fault loop impedance,
   SPDs after A4, EV charging Section 722, solar PV Section 712, inspection and testing sequence,
   EICR codes C1/C2/C3/FI), "18th Edition exam tips", "open-book exam: how to find regulations fast",
   "2382-26 vs 2382-22", "AM2 / 2391 are different qualifications" (only facts you can source).
   One solid page beats three thin ones: 600–1,200 words, a worked example or table, 3–6 FAQ items,
   links to the matching practice topic and to Google Play.
2. **Bluebell:** chapter guides and "Handbook vs today" explainers; test-day guide; practice per chapter.
3. **HiVis:** test-specific guides (Operatives, Supervisory, Managers and Professionals, Specialist),
   topic explainers matching the 19 Operatives topics; scenario question walkthroughs.
4. **FareBack:** Delay Repay guides by operator (thresholds 15/30/60/120 min, how to claim, time limits),
   only from each operator's own published page.
5. **CTR fixes** from Search Console data (see the routine).

## Hard rules (owner conventions; breaking one is a failed run)

- Never imply official status; no logos; never copy BS 7671, the Life in the UK handbook, CITB/ECS/City &
  Guilds question banks or official text. Questions shown on the sites come only from the apps' shipped
  bundles (`~/Code/exam-apps/app/assets/content/<brand>.json`); ids marked `verify: true` in
  `~/Code/exam-apps/content/` are never published (the build drops them). Write any new questions in
  the app repo's content workflow, not on the site.
- Every factual claim (regulation numbers, exam format, fees, pass marks, Delay Repay rules) must come
  from a primary or clearly authoritative public source, linked or recorded in the commit message.
  Uncertain facts are worded cautiously or left out. Never promise a pass.
- Brand disclaimer on every page (the build adds it); en-GB, UK spelling, dates DD/MM/YYYY.
- No cookies, analytics, trackers or third-party scripts (the apps declare "Data not collected").
- Privacy and terms pages: change only to fix a factual error, and move "Last updated".
- Keep `googleea66026b8981bf38.html` (Search Console verification) and FareBack's `id="delete"`.
- Do not change DNS, Cloudflare settings, nginx vhosts, the server, the apps, store listings or the
  GitHub Pages setting. Publishing is only `python3 tools/build.py` → commit → `deploy/deploy.sh <app>`
  → `deploy/deploy.sh check` → `git push origin main` (see `docs/deployment.md`).

## Owner reminders (report, do not act)

- GitHub Pages switch-off: after Google has approved the 27/11/2026 Play privacy-URL changes and the
  1.1.0 / FareBack 1.0.1 updates have been out about a week (≈ from 05/12/2026), the coordinator turns
  Pages off. The routine only reports when that point looks reached.
