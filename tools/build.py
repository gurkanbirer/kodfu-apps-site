#!/usr/bin/env python3
"""Build the five Kodfu app sites from src/ into <app>/ (served as is). No dependencies.

    python3 tools/build.py            # writes sparkwise/ bluebell/ hivis/ tickover/ fareback/

Sources (edit these, never the generated <app>/ files):
  src/<app>/<page>.html      body fragment with a <!--meta ... --> header; `index.html` is `/`,
                             `guide.html` is `/guide/`, `practice/x.html` is `/practice/x/`
  src/<app>/<page>.questions.json   questions rendered where the fragment has <!--questions-->
  src/<app>/mark.svg         optional brand mark (else a letter tile)
  ../exam-apps/app/assets/content/<brand>.json   shipped question bundles (Sparkwise, HiVis
                             practice pages); questions marked `verify: true` in
                             ../exam-apps/content/ are excluded again here as a second guard.

Fragments link inside their site with `~/path/` (made relative here, so the same files work on
the app's own host and on the GitHub Pages copy). Placeholders: <!--cta-->, <!--sources-->.
FAQ items `<h3 class="faq-q">…</h3><div class="faq-a">…</div>` become FAQPage JSON-LD.
Runbook: docs/deployment.md.
"""
import datetime
import glob
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM_APPS = os.environ.get("EXAM_APPS", os.path.expanduser("~/Code/exam-apps"))
EMAIL = "gurkancaner@kodfu.com"
TODAY = "2026-11-26"

E = html.escape


def play(pkg):
    return f"https://play.google.com/store/apps/details?id={pkg}"


SOURCES = {
    "sparkwise": [
        ("BS 7671 18th Edition wiring regulations", "IET", "https://electrical.theiet.org/bs-7671-18th-edition-wiring-regulations/"),
        ("Requirements for Electrical Installations (2382)", "City & Guilds", "https://www.cityandguilds.com/qualifications-and-apprenticeships/building-services-industry/electrical-installation/2382-requirements-for-electrical-installations"),
        ("Health, Safety & Environmental Assessment", "ECS, run by the JIB", "https://www.ecscard.org.uk/hse-assessment"),
        ("Electrical safety at work", "Health and Safety Executive (HSE)", "https://www.hse.gov.uk/electricity/"),
        ("The Electricity at Work Regulations 1989", "legislation.gov.uk", "https://www.legislation.gov.uk/uksi/1989/635/contents"),
    ],
    "bluebell": [
        ("Life in the UK Test", "GOV.UK", "https://www.gov.uk/life-in-the-uk-test"),
        ("What happens at the test and the pass mark", "GOV.UK", "https://www.gov.uk/life-in-the-uk-test/what-happens-test"),
        ("Cancellations and refunds", "GOV.UK", "https://www.gov.uk/life-in-the-uk-test/cancellations-refunds-complaints"),
        ("Book the test", "Booking service linked from GOV.UK", "https://www.lituktestbooking.co.uk/lituk-web/"),
        ("The handbook and study materials", "Shop linked from GOV.UK", "https://www.officiallifeintheuk.co.uk/shop"),
        ("Settlement (indefinite leave to remain)", "GOV.UK", "https://www.gov.uk/indefinite-leave-to-remain"),
        ("British citizenship", "GOV.UK", "https://www.gov.uk/british-citizenship"),
        ("Citizenship requirements and time outside the UK", "GOV.UK", "https://www.gov.uk/apply-citizenship-indefinite-leave-to-remain"),
        ("Continuous residence and absences for settlement", "Immigration Rules, GOV.UK", "https://www.gov.uk/guidance/immigration-rules/immigration-rules-appendix-continuous-residence"),
    ],
    "hivis": [
        ("About the HS&E test", "CITB", "https://www.citb.co.uk/courses-tests/health-safety-and-environment-hse-test/about-the-health-safety-and-environment-hse-test"),
        ("Operatives test", "CITB", "https://www.citb.co.uk/courses-tests/health-safety-and-environment-hse-test/operatives-test"),
        ("Specialist tests", "CITB", "https://www.citb.co.uk/courses-tests/health-safety-and-environment-hse-test/specialist-test"),
        ("Book the HS&E test", "Pearson VUE, the CITB test provider", "https://www.pearsonvue.com/us/en/citb.html"),
        ("Card Finder", "CSCS", "https://www.cscsonline.uk.com/card-finder"),
        ("Types of CSCS cards", "CSCS", "https://www.cscs.uk.com/types-of-cscs-cards/"),
        ("HS&E test and alternatives", "CSCS", "https://www.cscs.uk.com/applying-for-cards/health-and-safety-test/"),
        ("Construction health and safety", "Health and Safety Executive (HSE)", "https://www.hse.gov.uk/construction/"),
        ("Construction (Design and Management) Regulations 2015", "legislation.gov.uk", "https://www.legislation.gov.uk/uksi/2015/51/contents"),
        ("Health and Safety at Work etc. Act 1974", "legislation.gov.uk", "https://www.legislation.gov.uk/ukpga/1974/37/contents"),
    ],
    "tickover": [
        ("Check MOT history and due date", "GOV.UK", "https://www.gov.uk/check-mot-history"),
        ("Check if a vehicle is taxed", "GOV.UK", "https://www.gov.uk/check-vehicle-tax"),
        ("Getting an MOT", "GOV.UK", "https://www.gov.uk/getting-an-mot"),
        ("Tax your vehicle", "GOV.UK", "https://www.gov.uk/vehicle-tax"),
        ("Make a SORN", "GOV.UK", "https://www.gov.uk/make-a-sorn"),
        ("Get an MOT reminder", "GOV.UK", "https://www.gov.uk/mot-reminder"),
        ("MOT in Northern Ireland", "nidirect", "https://www.nidirect.gov.uk/articles/mot-scheme"),
    ],
    "fareback": [
        ("Compensation and refunds", "National Rail", "https://www.nationalrail.co.uk/help-and-assistance/compensation-and-refunds/"),
        ("Find a train company", "National Rail", "https://www.nationalrail.co.uk/travel-information/find-a-train-company/"),
        ("Know your rail rights", "Office of Rail and Road (ORR)", "https://www.orr.gov.uk/monitoring-regulation/rail/passengers/know-your-rail-rights"),
        ("Rail Ombudsman", "Rail Ombudsman", "https://www.railombudsman.org/"),
        ("Consumer Rights Act and transport services", "GOV.UK", "https://www.gov.uk/government/publications/consumer-rights-act-application-to-transport-services"),
    ],
}

SITES = {
    "sparkwise": dict(
        host="sparkwiseapp.co.uk", name="Sparkwise", tagline="18th Edition and ECS HS&E exam practice",
        pkg="com.kodfu.sparkwise", category="EducationalApplication",
        light="--bg:#FFFFFF;--fg:#14171C;--muted:#4A5260;--line:#E3E6EB;--card:#F6F7F9;--accent:#1D4ED8;--on-accent:#FFFFFF;--chip:#EEF2FF;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#111316;--fg:#ECEEF2;--muted:#B4BAC4;--line:#2A2F36;--card:#1A1D22;--accent:#93C5FD;--on-accent:#0B1220;--chip:#1B2546;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        nav=[("home", "Home", ""), ("exam", "18th Edition", "18th-edition-exam/"), ("a4", "Amendment 4", "amendment-4/"),
             ("ecs", "ECS HS&E", "ecs-hse-assessment/"), ("practice", "Practice", "practice/"), ("faq", "FAQ", "faq/")],
        notice='<strong>Not a government app.</strong> Sparkwise is an independent study app made by Kodfu Bilisim. It is not affiliated with or endorsed by the IET, BSI, City &amp; Guilds, ECS or JIB. It does not contain the real exam questions and never reproduces BS 7671 text.',
        disclaimer='Sparkwise is an independent study app made by Kodfu Bilisim. Not affiliated with or endorsed by the IET, BSI, City &amp; Guilds, ECS or JIB. Practice questions are original; always check real installations against your own copy of BS 7671.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<h2 id="cta-h">Practise both exams in the Sparkwise app</h2>
<p>Original questions across every Part of BS 7671:2018+A4:2026 and every ECS HS&amp;E syllabus area, timed mock exams in the real format, worked solutions for calculations and explanations that show where to look in the book.</p>
<ul class="plain">
<li>18th Edition: 60-question mock exams in 2 hours, a maximum Z<sub>s</sub> calculator and a guide to Amendment 4</li>
<li>ECS HS&amp;E: 50-question mock tests in 30 minutes</li>
<li>Works offline. No ads, no account, no data collected.</li>
</ul>
<p><strong>Free:</strong> two full topics in each exam, three questions in every other topic, one full mock exam for each exam, the maximum Z<sub>s</sub> calculator and checklists.<br><strong>Sparkwise Pro, £12.99 one-off:</strong> every question, every mock exam and every worked solution, for both exams. No subscription.</p>
<p><a class="btn" href="{play}" rel="noopener">Get Sparkwise on Google Play</a></p>
<p class="muted small">For Android phones. Sparkwise helps you prepare; it cannot promise a pass.</p>
</section>'''),
    "bluebell": dict(
        host="bluebell.kodfu.com", name="Bluebell", tagline="Life in the UK Test practice",
        pkg="com.kodfu.bluebell", category="EducationalApplication",
        light="--bg:#FFFFFF;--fg:#14171C;--muted:#4A5260;--line:#E3E6EB;--card:#F6F7F9;--accent:#4A4FB8;--on-accent:#FFFFFF;--chip:#E9EAFF;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#111316;--fg:#ECEEF2;--muted:#B4BAC4;--line:#2A2F36;--card:#1A1D22;--accent:#AEB1FF;--on-accent:#111316;--chip:#262A5C;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        nav=[("home", "Support", ""), ("guide", "Test guide", "guide/"), ("practice", "Free practice", "practice/")],
        notice='<strong>Not a government app.</strong> Bluebell is an independent study app made by Kodfu Bilisim. It does not represent the Home Office, UK Visas and Immigration or any government body, and it is not affiliated with or endorsed by them or by TSO.',
        disclaimer='Not a government app. Bluebell is an independent study app made by Kodfu Bilisim. It is not affiliated with or endorsed by the Home Office, UK Visas and Immigration or TSO (The Stationery Office). Bluebell&#8217;s guides are general information, not immigration advice.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<h2 id="cta-h">Want more practice?</h2>
<p>Bluebell is an Android app with 900+ original practice questions across all five chapters, plain-English explanations, full mock tests of 24 questions in 45 minutes, spaced review and a mistakes list. It works offline, with no ads and no account.</p>
<p><strong>Free:</strong> Chapter 1 in full, six free questions in every other topic, two full mock tests and all the tools.<br><strong>Bluebell Pro, £6.99 one-off:</strong> every question, every mock test and every study note. No subscription.</p>
<p><a class="btn" href="{play}" rel="noopener">Get Bluebell on Google Play</a></p>
<p class="muted small">For Android phones. Bluebell helps you prepare; it cannot promise a pass.</p>
</section>'''),
    "hivis": dict(
        host="hivis.kodfu.com", name="HiVis", tagline="CITB HS&E test practice",
        pkg="com.kodfu.hivis", category="EducationalApplication",
        light="--bg:#FFFFFF;--fg:#14171C;--muted:#4A5260;--line:#E3E6EB;--card:#F6F7F9;--accent:#C2410C;--on-accent:#FFFFFF;--chip:#FFF7ED;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#111316;--fg:#ECEEF2;--muted:#B4BAC4;--line:#2A2F36;--card:#1A1D22;--accent:#FDBA74;--on-accent:#111316;--chip:#3A2416;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        nav=[("home", "Support", ""), ("guide", "Test guide", "guide/"), ("practice", "Free practice", "practice/")],
        notice='<strong>Not a government app.</strong> HiVis is an independent study app made by Kodfu Bilisim. It is not affiliated with or endorsed by CITB, CSCS, Pearson VUE or HSE, and it does not contain the real test questions.',
        disclaimer='Not a government app. HiVis is an independent study app made by Kodfu Bilisim. It is not affiliated with or endorsed by CITB, CSCS or Pearson VUE.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<h2 id="cta-h">Practise every test in the HiVis app</h2>
<p>HiVis is an Android app with original questions for the Operatives, Managers and Professionals and specialist HS&amp;E tests, full timed mock tests of 50 questions in 45 minutes, clear explanations and spaced review. It works offline, with no ads and no account.</p>
<p><strong>Free:</strong> three topics in full, three questions in every other topic and one full mock test for each test.<br><strong>HiVis Pro, £5.99 one-off:</strong> every question and every mock test for all test levels. No subscription.</p>
<p><a class="btn" href="{play}" rel="noopener">Get HiVis on Google Play</a></p>
<p class="muted small">For Android phones. HiVis helps you prepare; it cannot promise a pass.</p>
</section>'''),
    "tickover": dict(
        host="tickover.kodfu.com", name="Tickover", tagline="MOT, tax and insurance reminders",
        pkg="com.kodfu.tickover", category="UtilitiesApplication",
        light="--bg:#FFFFFF;--fg:#14171C;--muted:#4A5260;--line:#E3E6EB;--card:#F6F7F9;--accent:#0B6E4F;--on-accent:#FFFFFF;--chip:#D5F2E6;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#111316;--fg:#ECEEF2;--muted:#B4BAC4;--line:#2A2F36;--card:#1A1D22;--accent:#4CC9A0;--on-accent:#00261A;--chip:#0F3B2D;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        nav=[("home", "Home", ""), ("guide", "MOT and tax guide", "guide/")],
        notice='<strong>Not a government service.</strong> Tickover is an independent app made by Kodfu Bilisim. It is not affiliated with or endorsed by DVLA, DVSA, HMRC, TfL or any local council. To tax a vehicle, make a SORN or book an MOT, use GOV.UK.',
        disclaimer='Tickover is an independent app made by Kodfu Bilisim. It is not a government service and is not affiliated with or endorsed by DVLA, DVSA, HMRC, TfL or any local council. For official services, visit <a href="https://www.gov.uk/" rel="noopener">GOV.UK</a>.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<h2 id="cta-h">Never miss an MOT or tax date</h2>
<p>Tickover keeps your vehicles&#8217; MOT, tax and insurance dates in one place and reminds you before each one runs out. Unlimited vehicles and reminders are free. No account, no ads.</p>
<p><strong>Tickover Pro:</strong> £7.99 a year with a 7-day free trial, or £24.99 once for lifetime. Prices include VAT.</p>
<p><a class="btn" href="{play}" rel="noopener">Get Tickover on Google Play</a></p>
<p class="muted small">For Android phones, in the United Kingdom.</p>
</section>'''),
    "fareback": dict(
        host="fareback.kodfu.com", name="FareBack", tagline="Help with late train claims",
        pkg="com.kodfu.fareback", category="TravelApplication",
        light="--bg:#F5F6F3;--fg:#10212B;--muted:#4A5A63;--line:#DCE1DD;--card:#FFFFFF;--accent:#0A6B57;--on-accent:#FFFFFF;--chip:#E2F1EC;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#121412;--fg:#E9EFEB;--muted:#A9B3AE;--line:#2E3833;--card:#1B211E;--accent:#4CD9A0;--on-accent:#0A2E22;--chip:#12392B;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        nav=[("home", "Support", ""), ("guide", "Delay Repay guide", "guide/")],
        notice='<strong>Independent app.</strong> FareBack is made by Kodfu Bilisim. It is not affiliated with or endorsed by any train company, National Rail, Network Rail, Rail Delivery Group, Great British Railways or the Department for Transport. You submit every claim yourself; the train company decides whether to pay.',
        disclaimer='FareBack is made by Kodfu Bilisim. It is not affiliated with or endorsed by any train company, National Rail, Network Rail, Rail Delivery Group, Great British Railways or the Department for Transport. &#8220;Delay Repay&#8221; is the name of the train companies&#8217; compensation scheme and is used here only to describe that scheme.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<h2 id="cta-h">Let FareBack watch your journeys</h2>
<p>Save a journey and FareBack checks it after the train arrives, tells you when a delay may qualify for compensation and gets your Claim Pack ready. You submit the claim yourself on the train company&#8217;s website, and any money goes to you.</p>
<p><strong>Free</strong> to use. <strong>FareBack Pro</strong> (optional): £1.99 a month or £12.99 a year with a 7-day free trial. Prices include VAT.</p>
<p><a class="btn" href="{play}" rel="noopener">Get FareBack on Google Play</a></p>
<p class="muted small">For Android phones, in Great Britain.</p>
</section>'''),
}

CSS = """:root{color-scheme:light dark;%(light)s}
@media (prefers-color-scheme:dark){:root{%(dark)s}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%%}
body{margin:0;background:var(--bg);color:var(--fg);font:400 1.0625rem/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,system-ui,sans-serif;overflow-wrap:break-word}
.wrap{max-width:760px;margin:0 auto;padding:0 16px}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px;border-radius:4px}
.skip{position:absolute;left:-9999px;top:0}
.skip:focus{left:16px;top:8px;background:var(--bg);padding:8px 12px;z-index:9}
header.site{border-bottom:1px solid var(--line);padding:12px 0 0;margin-bottom:24px}
.brand{display:inline-flex;align-items:center;gap:12px;text-decoration:none;color:var(--fg);margin:4px 0 10px}
.brand svg,.mark{width:44px;height:44px;border-radius:11px;flex:none}
.mark{background:var(--accent);color:var(--on-accent);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:20px}
.brand strong{display:block;font-size:1.25rem;line-height:1.2}
.brand small{display:block;color:var(--muted);font-size:.9375rem}
nav.main ul{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:0;padding:0 0 12px}
nav.main a{display:inline-flex;align-items:center;min-height:44px;padding:0 14px;border-radius:12px;background:var(--chip);text-decoration:none;font-weight:600;font-size:.9375rem}
nav.main a[aria-current=page]{outline:2px solid var(--accent)}
main{padding-bottom:48px}
h1{font-size:1.875rem;line-height:1.2;letter-spacing:-.01em;margin:8px 0 12px}
h2{font-size:1.3125rem;line-height:1.3;margin:36px 0 8px}
h3{font-size:1.125rem;line-height:1.35;margin:24px 0 6px}
p,li,dd{max-width:70ch}
li{margin:4px 0}
.lead{font-size:1.1875rem;line-height:1.55}
.muted{color:var(--muted)}
.small{font-size:.9375rem}
.crumb{font-size:.9375rem;margin:0 0 8px}
.notice{background:var(--warnbg);border-radius:12px;padding:12px 14px;font-size:.9375rem;margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:20px 0}
.card>:first-child{margin-top:0}
.card>:last-child{margin-bottom:0}
.callout{border-left:4px solid var(--accent);background:var(--chip);border-radius:0 12px 12px 0;padding:12px 16px;margin:16px 0}
.callout>:first-child{margin-top:0}.callout>:last-child{margin-bottom:0}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 20px;border-radius:12px;background:var(--accent);color:var(--on-accent);font-weight:700;text-decoration:none}
.btn.ghost{background:transparent;color:var(--accent);border:1.5px solid var(--line)}
ul.plain{padding-left:20px}
ul.links{list-style:none;margin:12px 0;padding:0;display:grid;gap:8px}
ul.links a{display:block;min-height:44px;padding:10px 14px;border:1.5px solid var(--line);border-radius:12px;text-decoration:none;font-weight:600;background:var(--bg)}
ul.links a:hover{border-color:var(--accent)}
ul.links a span{display:block;font-weight:400;font-size:.9375rem;color:var(--muted)}
.toc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px 12px 34px;font-size:.9375rem}
.table-wrap{overflow-x:auto;margin:12px 0}
table{width:100%%;border-collapse:collapse;font-size:1rem}
th,td{text-align:left;vertical-align:top;padding:10px 8px;border-bottom:1px solid var(--line)}
th{font-weight:700}
dt{font-weight:700;margin-top:12px}
dd{margin:2px 0 0}
details{margin:8px 0}
summary{cursor:pointer;font-weight:600;min-height:44px;display:flex;align-items:center}
kbd{font:inherit;font-size:.9em;border:1px solid var(--line);border-radius:4px;padding:0 4px}
.faq-a>:first-child{margin-top:0}
ol.qs{list-style:none;margin:16px 0;padding:0;counter-reset:q}
li.q{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin:0 0 16px;max-width:none}
.q .hint{font-size:.875rem;font-weight:700;color:var(--accent);margin:0 0 4px}
.q .scenario{font-style:italic;margin:0 0 6px}
.q h3{font-size:1.125rem;margin:0 0 10px}
.q ol.opts{margin:0 0 6px;padding-left:28px}
.q ol.opts li{margin:6px 0}
.q details{border-top:1px solid var(--line);margin-top:10px;padding-top:4px}
.q .ans{background:var(--okbg);border-radius:10px;padding:8px 12px;margin:6px 0}
.q .ans strong{color:var(--ok)}
.q .src{font-size:.875rem;color:var(--muted)}
.q .worked{font-size:.9375rem}
.notes h3{margin-top:16px}
footer.site{border-top:1px solid var(--line);color:var(--muted);font-size:.9375rem;padding:16px 0 32px}
footer.site p{margin:8px 0;max-width:none}
footer.site a{color:inherit}
@media (max-width:480px){h1{font-size:1.625rem}.lead{font-size:1.0625rem}}
"""


def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_fragment(path):
    s = open(path, encoding="utf-8").read()
    m = re.match(r"<!--meta\n(.*?)\n-->\n?", s, re.S)
    if not m:
        raise SystemExit(f"{path}: missing <!--meta ... --> header")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, s[m.end():]


def url_path(rel_file):
    """'index.html' -> '', 'guide.html' -> 'guide/', 'practice/x.html' -> 'practice/x/'."""
    p = rel_file[:-5]
    return "" if p == "index" else p + "/"


def rel_prefix(path):
    depth = path.count("/")
    return "../" * depth if depth else "./"


def relink(body, path):
    pre = rel_prefix(path)

    def sub(m):
        target = m.group(2)
        out = pre + target if target else pre
        if out.startswith("./") and len(out) > 2:
            out = out[2:]
        return f'{m.group(1)}="{out}"'
    return re.sub(r'(href)="~/([^"]*)"', sub, body)


def relink_href(target, path):
    return re.search(r'href="([^"]*)"', relink(f'href="~/{target}"', path)).group(1)


def sources_card(app):
    items = "\n".join(f'<li><a href="{E(u)}" rel="noopener">{E(t)}</a> <span class="muted">({E(p)})</span></li>'
                      for t, p, u in SOURCES[app])
    note = {"bluebell": "Bluebell&#8217;s guides are general information, not immigration advice.",
            "sparkwise": "Exam details can change. Check with the awarding body or your exam centre before you book, and always check real installations against your own copy of BS 7671.",
            "hivis": "Test details can change. Check with CITB before you book.",
            "tickover": "Check your vehicle&#8217;s own record on GOV.UK. Tickover only shows the dates you enter.",
            "fareback": "Each train company sets its own claim rules and makes the final decision."}[app]
    return (f'<section class="card" aria-labelledby="sources-h">\n<h2 id="sources-h">Official sources</h2>\n'
            f'<p class="muted">Check these public pages before you book, apply or claim.</p>\n<ul class="plain">\n{items}\n</ul>\n'
            f'<p class="muted small">{note}</p>\n</section>')


def faq_items(body):
    out = []
    for q, a in re.findall(r'<h3 class="faq-q"[^>]*>(.*?)</h3>\s*<div class="faq-a">(.*?)</div>', body, re.S):
        out.append({"@type": "Question", "name": strip_tags(q),
                    "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}})
    return out


def mark_html(app, cfg):
    svg = os.path.join(ROOT, "src", app, "mark.svg")
    if os.path.exists(svg):
        return open(svg).read().strip()
    return f'<span class="mark" aria-hidden="true">{cfg["name"][0]}</span>'


def favicon(app, cfg):
    svg = os.path.join(ROOT, "src", app, "mark.svg")
    if os.path.exists(svg):
        s = open(svg).read().strip()
        return s.replace(' aria-hidden="true" focusable="false"', "")
    col = re.search(r"--accent:(#[0-9A-Fa-f]{6})", cfg["light"]).group(1)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{col}"/>'
            f'<text x="32" y="44" font-family="Arial,Helvetica,sans-serif" font-size="36" font-weight="700" fill="#fff" text-anchor="middle">{cfg["name"][0]}</text></svg>')


def ddmmyyyy(iso):
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def page(app, cfg, path, meta, body, crumbs=None):
    """Wrap a body in the layout. `path` is the URL path below the host ('' or 'x/y/')."""
    host = cfg["host"]
    url = f"https://{host}/{path}"
    pre = rel_prefix(path)
    nav_key = meta.get("nav", "home" if path == "" else "")
    legal = path in ("privacy/", "terms/")
    body = body.replace("<!--cta-->", cfg["cta"].format(play=play(cfg["pkg"])))
    body = body.replace("<!--sources-->", sources_card(app))
    body = relink(body, path)
    body = re.sub(r'\s+style="[^"]*"', "", body)   # CSP: style-src 'self' (no inline styles)
    title, desc = meta["title"], meta.get("description", "")
    updated = meta.get("updated", TODAY)
    lds = []
    if path == "":
        lds.append({"@context": "https://schema.org", "@type": "SoftwareApplication", "name": cfg["name"],
                    "description": desc, "operatingSystem": "Android", "applicationCategory": cfg["category"],
                    "url": url, "downloadUrl": play(cfg["pkg"]), "inLanguage": "en-GB",
                    "offers": {"@type": "Offer", "price": "0", "priceCurrency": "GBP"},
                    "publisher": {"@type": "Organization", "name": "Kodfu Bilisim", "email": EMAIL}})
        lds.append({"@context": "https://schema.org", "@type": "WebSite", "name": cfg["name"], "url": url, "inLanguage": "en-GB"})
    faqs = faq_items(body)
    if faqs:
        lds.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": faqs})
    if path and not legal:
        trail = [(cfg["name"], f"https://{host}/")] + (crumbs or []) + [(strip_tags(re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S).group(1)) if "<h1" in body else title, url)]
        lds.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(trail)]})
    ld = "\n".join('<script type="application/ld+json">%s</script>' % json.dumps(x, ensure_ascii=False).replace("</", "<\\/") for x in lds)
    cur = ' aria-current="page"'
    nav = "".join(
        f'<li><a href="{relink_href(href, path)}"{cur if key == nav_key else ""}>{E(label)}</a></li>'
        for key, label, href in cfg["nav"])
    notice = "" if legal or path == "" else f'<p class="notice">{cfg["notice"]}</p>\n'
    footer_date = "" if "Last updated" in body else f" · Last updated {ddmmyyyy(updated)}"
    home = pre
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{E(cfg['name'])}">
<meta property="og:locale" content="en_GB">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta name="twitter:card" content="summary">
<link rel="icon" href="{pre}favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{pre}assets/site.css?v={CSS_VERSION}">
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site"><div class="wrap">
<a class="brand" href="{home}">{mark_html(app, cfg)}<span><strong>{E(cfg['name'])}</strong><small>{E(cfg['tagline'])}</small></span></a>
<nav class="main" aria-label="{E(cfg['name'])} pages"><ul>{nav}</ul></nav>
</div></header>
<main id="main" class="wrap">
{notice}{body.strip()}
</main>
<footer class="site"><div class="wrap">
<p>{cfg['disclaimer']}</p>
<p><a href="{home}">{'Home' if cfg['nav'][0][1] == 'Home' else 'Support'}</a> · <a href="{pre}privacy/">Privacy policy</a> · <a href="{pre}terms/">Terms of use</a> · <a href="mailto:{EMAIL}">{EMAIL}</a></p>
<p>This site has no cookies, analytics or trackers. © 2026 Kodfu Bilisim{footer_date}</p>
</div></footer>
</body>
</html>
"""


# ---------- questions ----------

def hint(q):
    n = len(q.get("correct", []))
    if q["type"] == "multi":
        return {2: "Select TWO answers", 3: "Select THREE answers"}.get(n, "Select all that apply")
    if q["type"] == "truefalse":
        return "True or false?"
    return "Choose one answer"


def render_questions(qs, source_label="Source"):
    out = ['<ol class="qs">']
    for i, q in enumerate(qs, 1):
        qid = q.get("id") or f"{i}"
        letters = "ABCDEFGH"
        opts = "".join(f"<li>{E(o)}</li>" for o in q["options"])
        correct = sorted(q["correct"])
        ans = ", ".join(f"{letters[c]}: {E(q['options'][c])}" for c in correct)
        scen = f'<p class="scenario">{E(q["scenario"])}</p>' if q.get("scenario") else ""
        worked = ""
        w = q.get("worked")
        if w:
            steps = "".join(f"<li><strong>{E(s.get('title', ''))}:</strong> {E(s.get('body', ''))}</li>" for s in w.get("steps", []))
            worked = (f'<div class="worked"><p><strong>Worked solution.</strong> Formula: {E(w.get("formula", ""))}</p>'
                      f'<ol>{steps}</ol>' + (f'<p>Common mistake: {E(w["mistake"])}</p>' if w.get("mistake") else "") + "</div>")
        src = f'<p class="src">{source_label}: {E(q["source"])}</p>' if q.get("source") else ""
        out.append(
            f'<li class="q" id="q{i}"><p class="hint">Question {i} · {hint(q)}</p>{scen}<h3>{E(q["stem"])}</h3>'
            f'<ol class="opts" type="A">{opts}</ol>'
            f'<details><summary>Show the answer</summary><p class="ans"><strong>Answer</strong> {ans}</p>'
            f'<p>{E(q.get("explanation", ""))}</p>{worked}{src}</details></li>')
    out.append("</ol>")
    return "\n".join(out)


def unverified_ids(brand):
    ids = set()
    for f in glob.glob(os.path.join(EXAM_APPS, "content", brand, "**", "*.json"), recursive=True):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if isinstance(d, dict):
            for q in d.get("questions", []):
                if q.get("verify"):
                    ids.add(q["id"])
    return ids


def short_title(topic, kind, brand):
    for t in (f"{topic}: {kind} Practice Questions | {brand}", f"{topic}: {kind} Practice | {brand}",
              f"{topic}: {kind} Practice", f"{topic} | {kind}"):
        if len(t) <= 60:
            return t
    return f"{topic} | {kind}"


def pick(qs, k):
    if len(qs) <= k:
        return qs
    idx = sorted({round(i * (len(qs) - 1) / (k - 1)) for i in range(k)})
    return [qs[i] for i in idx]


def load_bundle(brand):
    d = json.load(open(os.path.join(EXAM_APPS, "app", "assets", "content", f"{brand}.json")))
    bad = unverified_ids(brand)
    files = d["files"]
    for f in files.values():
        if isinstance(f, dict) and "questions" in f:
            f["questions"] = [q for q in f["questions"] if q.get("id") not in bad and q.get("correct") and q.get("options")]
    return files


def notes_html(notes):
    if not notes:
        return ""
    parts = "".join(f'<h3>{E(n["heading"])}</h3><p>{E(n["body"])}</p>' for n in notes)
    return f'<section class="card notes" aria-labelledby="notes-h"><h2 id="notes-h">Revision notes</h2>{parts}</section>'


def topic_links(base, exam, files, per_page):
    groups, order = {}, []
    for t in exam["topics"]:
        g = t.get("part") or t.get("area") or ""
        if g not in groups:
            groups[g] = []
            order.append(g)
        n = min(per_page, len(files[t["file"]]["questions"]))
        groups[g].append(f'<li><a href="~/{base}{t["id"]}/">{E(t["title"])}<span>{E(t["summary"])} · {n} questions</span></a></li>')
    return "\n".join((f"<h3>{E(g)}</h3>" if g else "") + '<ul class="links">' + "".join(groups[g]) + "</ul>" for g in order)


def sparkwise_practice(cfg, out):
    files = load_bundle("sparkwise")
    PER = 10
    exams = [("18th-edition", files["manifest.bs7671.json"], "18th Edition", "Where to look"),
             ("ecs-hse", files["manifest.ecs-hse.json"], "ECS HS&E", "Source")]
    total = 0
    for slug, ex, short, label in exams:
        topics = ex["topics"]
        for i, t in enumerate(topics):
            tf = files[t["file"]]
            qs = pick(tf["questions"], PER)
            total += len(qs)
            path = f"practice/{slug}/{t['id']}/"
            nxt = topics[(i + 1) % len(topics)]
            prv = topics[i - 1]
            exam_line = ("Open book: have your copy of BS 7671:2018+A4:2026 ready and look each answer up, as you would in the exam."
                         if slug == "18th-edition" else
                         "Closed book, like the real assessment: answer first, then open the explanation.")
            body = f"""<p class="crumb"><a href="~/practice/">Free practice</a> › <a href="~/practice/#{slug}">{E(short)}</a></p>
<h1>{E(t['title'])}: free {E(short)} practice questions</h1>
<p class="lead">{E(t['summary'])}</p>
<p class="muted">{len(qs)} original questions from the Sparkwise app, each with the answer and an explanation. {E(exam_line)} No sign-up, nothing saved. These are not the real exam questions: no app or website can show you those.</p>
{render_questions(qs, label)}
{notes_html(tf.get('notes'))}
<h2 id="more">More {E(short)} topics</h2>
<ul class="links"><li><a href="~/practice/{slug}/{prv['id']}/">Previous: {E(prv['title'])}<span>{E(prv['summary'])}</span></a></li>
<li><a href="~/practice/{slug}/{nxt['id']}/">Next: {E(nxt['title'])}<span>{E(nxt['summary'])}</span></a></li>
<li><a href="~/{'18th-edition-exam' if slug == '18th-edition' else 'ecs-hse-assessment'}/">{'18th Edition exam guide' if slug == '18th-edition' else 'ECS HS&amp;E assessment guide'}<span>Format, rules, booking and how to prepare</span></a></li></ul>
<!--cta-->"""
            meta = {"title": short_title(t['title'], short, "Sparkwise"),
                    "description": f"Free {short} practice questions on {t['title'].lower()}, with answers and explanations. "
                                   + ("BS 7671:2018+A4:2026, C&G 2382-26." if slug == "18th-edition" else "ECS Health, Safety & Environmental assessment."),
                    "nav": "practice", "updated": files["manifest.json"].get("updated", TODAY)}
            meta["description"] = meta["description"][:158]
            write(out, path, page("sparkwise", cfg, path, meta, body, [("Free practice", f"https://{cfg['host']}/practice/")]))
    bs, ecs = files["manifest.bs7671.json"], files["manifest.ecs-hse.json"]
    body = f"""<h1>Free 18th Edition and ECS HS&amp;E practice questions</h1>
<p class="lead">{total} free practice questions by topic for the 18th Edition (City &amp; Guilds 2382-26, BS 7671:2018+A4:2026) and the ECS Health, Safety and Environmental assessment, each with the answer and an explanation.</p>
<p class="muted">Free, with no sign-up and nothing saved. Every question is original and comes from the Sparkwise app; only questions we have checked are published. No app or website can show you the real exam questions.</p>
<div class="toc"><a href="#18th-edition">18th Edition topics</a> · <a href="#ecs-hse">ECS HS&amp;E topics</a></div>
<h2 id="18th-edition">18th Edition practice (BS 7671:2018+A4:2026)</h2>
<p>The City &amp; Guilds 2382-26 exam tests whether you can find and apply the requirements of the current Wiring Regulations. It is an online multiple-choice exam of {bs['mock']['questionCount']} questions in {bs['mock']['minutes']} minutes, and it is open book, so practise with your own copy of BS 7671 to hand. Each answer points to a regulation, table or appendix to look up. Read the <a href="~/18th-edition-exam/">18th Edition exam guide</a> and <a href="~/amendment-4/">what changed in Amendment 4</a>.</p>
{topic_links('practice/18th-edition/', bs, files, PER)}
<h2 id="ecs-hse">ECS HS&amp;E practice</h2>
<p>The ECS Health, Safety and Environmental assessment is the test most electrotechnical workers pass to get or renew an ECS card. It has {ecs['mock']['questionCount']} multiple-choice questions in {ecs['mock']['minutes']} minutes and is closed book. The CITB HS&amp;E test used for CSCS cards does not count for ECS. Read the <a href="~/ecs-hse-assessment/">ECS HS&amp;E assessment guide</a>.</p>
{topic_links('practice/ecs-hse/', ecs, files, PER)}
<!--cta-->
<!--sources-->"""
    meta = {"title": "Free 18th Edition & ECS HS&E Practice Questions | Sparkwise",
            "description": f"{total} free practice questions by topic for the 18th Edition (C&G 2382-26, BS 7671 A4:2026) and the ECS HS&E assessment, with answers and explanations.",
            "nav": "practice", "updated": files["manifest.json"].get("updated", TODAY)}
    write(out, "practice/", page("sparkwise", cfg, "practice/", meta, body))
    return total


def hivis_practice(cfg, out):
    files = load_bundle("hivis")
    PER = 6
    ex = files["manifest.operatives.json"]
    topics = ex["topics"]
    total = 0
    for i, t in enumerate(topics):
        tf = files[t["file"]]
        qs = pick(tf["questions"], PER)
        total += len(qs)
        path = f"practice/{t['id']}/"
        nxt, prv = topics[(i + 1) % len(topics)], topics[i - 1]
        body = f"""<p class="crumb"><a href="~/practice/">Free practice</a> › {E(t.get('area', ''))}</p>
<h1>{E(t['title'])}: free HS&amp;E test practice questions</h1>
<p class="lead">{E(t['summary'])}</p>
<p class="muted">{len(qs)} original questions from the HiVis app for the CITB HS&amp;E Operatives test, each with the answer and an explanation. No sign-up, nothing saved. These are not the real test questions: no app or website can show you those.</p>
{render_questions(qs)}
{notes_html(tf.get('notes'))}
<h2 id="more">More topics</h2>
<ul class="links"><li><a href="~/practice/{prv['id']}/">Previous: {E(prv['title'])}<span>{E(prv['summary'])}</span></a></li>
<li><a href="~/practice/{nxt['id']}/">Next: {E(nxt['title'])}<span>{E(nxt['summary'])}</span></a></li>
<li><a href="~/guide/">HS&amp;E test guide<span>Format, pass mark, booking, ID and how to prepare</span></a></li></ul>
<!--cta-->"""
        meta = {"title": short_title(t['title'], "HS&E Test", "HiVis"),
                "description": f"Free CITB HS&E test practice questions on {t['title'].lower()}, with answers and explanations. Original questions, no sign-up."[:158],
                "nav": "practice"}
        write(out, path, page("hivis", cfg, path, meta, body, [("Free practice", f"https://{cfg['host']}/practice/")]))
    m = ex["mock"]
    body = f"""<h1>Free CITB HS&amp;E test practice questions</h1>
<p class="lead">{total} free practice questions for the CITB Health, Safety and Environment Operatives test, by topic, each with the answer and an explanation.</p>
<p class="muted">Free, with no sign-up and nothing saved. Every question is original and comes from the HiVis app. No app or website can show you the real test questions.</p>
<p>{E(ex['description'])} The real test has {m['questionCount']} questions in {m['minutes']} minutes. Read the <a href="~/guide/">HS&amp;E test guide</a> for the format, booking and what to bring.</p>
<h2 id="topics">Topics</h2>
{topic_links('practice/', ex, files, PER)}
<!--cta-->
<!--sources-->"""
    meta = {"title": "Free CITB HS&E Test Practice Questions 2026 | HiVis",
            "description": f"{total} free CITB HS&E Operatives test practice questions by topic, with answers and explanations. Original questions, no sign-up, nothing saved.",
            "nav": "practice"}
    write(out, "practice/", page("hivis", cfg, "practice/", meta, body))
    return total


# ---------- output ----------

WRITTEN = []


def write(out, path, content):
    f = os.path.join(out, path, "index.html") if path.endswith("/") or path == "" else os.path.join(out, path)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(content)
    WRITTEN.append((path, f))


CSS_VERSION = "1"


def build(app):
    global CSS_VERSION
    cfg = SITES[app]
    out = os.path.join(ROOT, app)
    css = CSS % cfg
    import hashlib
    CSS_VERSION = hashlib.sha1(css.encode()).hexdigest()[:8]
    # remove previously generated pages (keeps README.md)
    for f in glob.glob(os.path.join(out, "**", "index.html"), recursive=True):
        os.remove(f)
    for d in sorted(glob.glob(os.path.join(out, "**", ""), recursive=True), reverse=True):
        if d.rstrip("/") != out and not os.listdir(d):
            os.rmdir(d)
    start = len(WRITTEN)
    src = os.path.join(ROOT, "src", app)
    for f in sorted(glob.glob(os.path.join(src, "**", "*.html"), recursive=True)):
        rel = os.path.relpath(f, src)
        meta, body = parse_fragment(f)
        qf = f[:-5] + ".questions.json"
        if "<!--questions-->" in body:
            body = body.replace("<!--questions-->", render_questions(json.load(open(qf))))
        path = url_path(rel)
        crumbs = [("Free practice", f"https://{cfg['host']}/practice/")] if path.startswith("practice/") and path != "practice/" else None
        write(out, path, page(app, cfg, path, meta, body, crumbs))
    extra = None
    if app == "sparkwise":
        extra = sparkwise_practice(cfg, out)
    if app == "hivis":
        extra = hivis_practice(cfg, out)
    os.makedirs(os.path.join(out, "assets"), exist_ok=True)
    open(os.path.join(out, "assets", "site.css"), "w").write(css)
    open(os.path.join(out, "favicon.svg"), "w").write(favicon(app, cfg) + "\n")
    # 404 page: root-absolute links (served by nginx for any depth on the app's own host)
    nf = page(app, cfg, "", {"title": f"Page not found | {cfg['name']}", "description": "", "nav": "-"},
              '<h1>Page not found</h1><p class="lead">That page does not exist or has moved.</p><p><a class="btn" href="~/">Go to the home page</a></p>')
    nf = nf.replace('href="./', 'href="/').replace('href="./"', 'href="/"')
    nf = re.sub(r'<link rel="canonical"[^>]*>\n', "", nf)
    nf = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", nf)
    nf = nf.replace("<head>", '<head>\n<meta name="robots" content="noindex">', 1)
    open(os.path.join(out, "404.html"), "w").write(nf)
    pages = [p for p, _ in WRITTEN[start:]]
    urls = "\n".join(f"  <url><loc>https://{cfg['host']}/{p}</loc><lastmod>{TODAY}</lastmod></url>" for p in sorted(pages, key=lambda p: (p.count('/'), p)))
    open(os.path.join(out, "sitemap.xml"), "w").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n')
    open(os.path.join(out, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: https://{cfg['host']}/sitemap.xml\n")
    print(f"{app}: {len(pages)} pages -> https://{cfg['host']}/" + (f" ({extra} practice questions)" if extra else ""))


if __name__ == "__main__":
    apps = sys.argv[1:] or list(SITES)
    for a in apps:
        build(a)
