# Conversion strategy and daily routine (Kodfu UK app sites)

Owner decision 27/11/2026 (latest): **conversion is the only goal** ("bizim yegane hedefimiz dönüşüm,
sistemi buna göre kurgula"). A site, page or change is judged only by Google Play installs and Pro
purchases it produces, never by traffic, impressions or rankings on their own. SEO is the way people
arrive; the page's job is to send them to the Play listing. A daily scheduled task
(`kodfu-apps-seo-gunluk`) works on this with full authority and never asks the owner. This file is what
that routine reads first on every run. Newer monthly reviews in `docs/seo-reviews/` override the
priorities below; the run log is `docs/seo-log.md`.

## Sites and goals

| Host | App (Google Play) | Goal | Weight |
|---|---|---|---|
| `https://sparkwiseapp.co.uk/` | Sparkwise `com.kodfu.sparkwise` (18th Edition C&G 2382-26, BS 7671:2018+A4:2026, ECS HS&E) | Play installs → Pro (£12.99). The only app with a sale (25/11/2026). | **Lead: most runs** |
| `https://bluebell.kodfu.com/` | Bluebell `com.kodfu.bluebell` (Life in the UK Test) | Play installs → Pro (£6.99). Very crowded market: win high-intent long-tail searches. | Second |
| `https://hivis.kodfu.com/` | HiVis `com.kodfu.hivis` (CITB HS&E test for the CSCS card) | Play installs → Pro (£5.99). Test-level and topic practice searches. | Third |
| `https://fareback.kodfu.com/` | FareBack `com.kodfu.fareback` (Delay Repay claims; live rail data since 27/11/2026) | Play installs (subscription). Delay Repay how-to by operator. | Occasional |
| `https://tickover.kodfu.com/` | Tickover: **unpublished 27/11/2026**, to be re-released by another company | None. Keep the pages up, do not invest. | — |

Search Console (account `info.kodfu@gmail.com`): `sc-domain:sparkwiseapp.co.uk` and URL-prefix
properties for the four `*.kodfu.com` hosts. Keyword research and competitor notes from the store
side: `~/Code/exam-apps/store/<brand>/aso.md` (Sparkwise, Bluebell, HiVis), `~/Code/fareback/store/aso.md`.

## Measuring conversion (no trackers on the sites)

Every Play link on the sites carries an install referrer
`&referrer=utm_source=<site>&utm_medium=site&utm_campaign=<page-slug>&utm_content=<position>`
(built by one helper in `tools/build.py`; scheme in `docs/deployment.md`). Play Console →
Statistics / Store listing acquisition (filter by UTM source and campaign) shows store-listing visitors,
installers and the conversion rate per page and per button; Play Console orders / financial reports
show Pro purchases. Search Console shows how many people reach each page. The funnel per page is:
GSC clicks → listing visitors (UTM) → installers → Pro. The weakest step is where the work goes.
Never add analytics, cookies or scripts to measure more: the apps declare "Data not collected".

## What to work on (priority order, until a monthly review says otherwise)

1. **Conversion leaks on pages that already get visitors.** A page with GSC clicks but few Play
   listing visitors from its UTM campaign needs a better offer, not more words: clearer value line and
   button above the fold, a CTA tied to what the searcher wanted (the topic's questions in the app, the
   max Zs calculator), the real question count, free vs Pro stated plainly, the right screenshot.
   Change one thing per run so the effect can be read.
2. **High-intent pages before informational ones.** Searches from people about to sit the exam and
   looking for a tool convert best: "18th Edition mock test", "18th Edition exam questions / practice
   app", "2382-26 practice questions", "ECS HS&E test practice / mock", "18th Edition open book exam
   tips", "how to pass the 18th Edition" (never promise a pass), "2382-26 vs 2382-22"; for Bluebell and
   HiVis the equivalent "mock test / practice questions / app" searches. These pages lead with the
   practice offer.
3. **Sparkwise topic depth that feeds a buyer path.** Regulation-area explainers that electricians
   search (RCD protection, earthing TN-C-S/TN-S/TT, bathroom zones, cable sizing and voltage drop, Zs and
   max earth fault loop impedance, SPDs after A4, EV charging 722, solar PV 712, inspection and testing
   sequence, EICR codes C1/C2/C3/FI), each ending in the matching app practice and Play CTA. One solid
   page beats three thin ones: 600–1,200 words, a worked example or table, 3–6 FAQ items.
4. **CTR fixes** from Search Console data: titles and meta descriptions that promise the practice
   (free questions, mock exams, worked answers) to the query the page actually gets.
5. **Bluebell, HiVis, FareBack** content in that order, same rules: high-intent first.

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
