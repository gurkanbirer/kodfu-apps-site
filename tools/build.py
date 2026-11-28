#!/usr/bin/env python3
"""Build the five Kodfu app sites from src/ into <app>/ (served as is). No dependencies
(Pillow only if a screenshot in src/<app>/screens/ is missing and has to be made again).

    python3 tools/build.py            # writes sparkwise/ bluebell/ hivis/ tickover/ fareback/

Goal (owner decision 27/11/2026): conversion. Every page sends visitors to the Google Play
listing: the app's own look, a Play button above the fold, app screenshots, CTAs after the
content, a sticky mobile bar, and every Play link carries an install referrer (see play_link()).

Sources (edit these, never the generated <app>/ files):
  src/<app>/<page>.html      body fragment with a <!--meta ... --> header; `index.html` is `/`,
                             `guide.html` is `/guide/`, `practice/x.html` is `/practice/x/`
                             meta keys: title, description, updated, nav, pitch (one line under
                             the header), shots (comma list of screenshots for the CTA strip)
  src/<app>/<page>.questions.json   questions rendered where the fragment has <!--questions-->
  src/<app>/mark.svg         brand mark (else a letter tile); also the favicon
  src/<app>/screens/*.webp   optimised app screenshots (made from ~/Code/exam-apps/store/<app>/
                             screenshots/android/*.png if missing), copied to <app>/assets/screens/
  ../exam-apps/app/assets/content/<brand>.json   shipped question bundles: practice pages and
                             every question count on the sites; questions marked `verify: true`
                             in ../exam-apps/content/ are excluded again here as a second guard.

Fragment placeholders (all optional):
  ~/path/                    link inside the site (href or src), made relative here
  ~play:<position>           a Google Play link with the install referrer for this page + position
  <!--cta-->                 closing app card (Play button, free vs Pro, screenshot strip)
  <!--appcta\nkey: value\n-->  inline app box; keys: title, text, pos (default inline)
  <!--after-questions:<exam>[/<topic>|/group:<n>]-->   "You've seen 10 of N" card
  <!--shots:a,b,c-->         screenshot strip; <!--shot:name[:eager]--> one screenshot
  <!--ios-->                 the honest iPhone line
  <!--hero-->...<!--/hero--> home hero, moved into the coloured header band
  {{count:all|<exam>|<exam>/<topic>|<exam>/group:<n>|<exam>+<exam>}}, {{free:...}}, {{worked:...}},
                             (Sparkwise: use {{count:bs7671+ecs-hse}}, not all: the bundle also
                             holds the per-exam packs that the £12.99 Pro does not unlock)
  {{topics:<exam>}}          real numbers from the shipped bundle
  {{count:<a>|<b>}}          unique questions over exams that share topic files (2391, solar + battery);
                             {{count:exams}} = number of exams in the bundle; {{price:<pack>|pro|all}}
  <!--sample:<a>[|<b>] n=8 [ids=x,y]-->  free sample from the shipped bank (one per topic, spread)
  <!--after-sample:<a>[|<b>]-->          "You've seen 8 of N" card for that sample
  meta `pack: <key>`         exam page of a Sparkwise 1.2.0 pack (PACKS): its own sticky bar, app boxes,
                             closing card, after-sample line and sources; meta `sticky:` overrides the bar
  <!--sources-->             official sources card (on pack pages: "Where the exam facts come from")
FAQ items `<h3 class="faq-q">…</h3><div class="faq-a">…</div>` become FAQPage JSON-LD.
Runbook: docs/deployment.md.
"""
import datetime
import glob
import hashlib
import html
import json
import os
import re
import shutil
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAM_APPS = os.environ.get("EXAM_APPS", os.path.expanduser("~/Code/exam-apps"))
EMAIL = "gurkancaner@kodfu.com"
TODAY = "2026-11-27"
IOS_LINE = "Android now; iPhone version not yet available."
# Play Console's acquisition report breaks installs down by utm_source and utm_campaign. If the
# position (utm_content) turns out not to be visible there, set this to True: the position is then
# also appended to the campaign (`<page>--<position>`), so it shows up as its own row.
UTM_POSITION_IN_CAMPAIGN = True

E = html.escape


def play(pkg):
    """Plain store URL (JSON-LD downloadUrl, never a visible link)."""
    return f"https://play.google.com/store/apps/details?id={pkg}"


def campaign_slug(path):
    """'' -> 'home', 'practice/18th-edition/ppe/' -> 'practice-18th-edition-ppe'."""
    s = re.sub(r"[^a-z0-9]+", "-", path.lower().replace(".html", "")).strip("-")
    return s or "home"


def play_link(cfg, path, pos):
    """The one place Play links are made. Install referrer, read in Play Console (docs/deployment.md)."""
    camp = campaign_slug(path)
    if UTM_POSITION_IN_CAMPAIGN:
        camp = f"{camp}--{pos}"
    ref = f"utm_source={cfg['host']}&utm_medium=site&utm_campaign={camp}&utm_content={pos}"
    return play(cfg["pkg"]) + "&referrer=" + urllib.parse.quote(ref, safe="")


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

PLAY_BTN = '<a class="btn play" href="~play:{pos}">Get it on Google Play</a>'

SITES = {
    "sparkwise": dict(
        host="sparkwiseapp.co.uk", name="Sparkwise", tagline="UK electrician exam practice",
        pkg="com.kodfu.sparkwise", category="EducationalApplication", bundle="sparkwise", promote=True,
        light="--bg:#FFFFFF;--fg:#14171C;--muted:#4A5260;--line:#E3E6EB;--card:#F6F7F9;--accent:#1D4ED8;--on-accent:#FFFFFF;--chip:#EEF2FF;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#0D1119;--fg:#ECEEF2;--muted:#B4BAC4;--line:#262D3A;--card:#161B26;--accent:#93C5FD;--on-accent:#0B1220;--chip:#1B2546;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        band="--band:#111827;--band2:#18233A;--on-band:#FFFFFF;--band-muted:#C9D1DE;--band-chip:rgba(255,255,255,.09);--band-hl:#FFC21A;--band-line:rgba(255,255,255,.12);--play:#FFC21A;--on-play:#111827",
        band_edge="1px solid #262D3A",
        nav=[("home", "Home", ""), ("exam", "18th Edition", "18th-edition-exam/"), ("ecs", "ECS HS&E", "ecs-hse-assessment/"),
             ("exams", "All 12 exams", "exams/"), ("practice", "Practice", "practice/"), ("a4", "Amendment 4", "amendment-4/"),
             ("faq", "FAQ", "faq/")],
        pitch="Practise for the 18th Edition and the ECS HS&amp;E on your phone: {{count:bs7671+ecs-hse}} original questions, timed mock exams and worked calculations.",
        sticky_sub="Free to try · Pro £12.99 once",
        appcta_sub="Free to try · Pro £12.99 one-off, both exams · no subscription",
        pro_line="Sparkwise Pro is £12.99 one-off and unlocks every question, every mock exam and every worked solution for both exams. No subscription.",
        screens={
            "01-home": ("Prepare for the 18th Edition", "Sparkwise home screen with a readiness score, the days left to the exam and today's practice"),
            "02-exams": ("ECS test and 18th Edition", "Choosing the ECS HS&E assessment, the 18th Edition exam or both in Sparkwise"),
            "03-mock": ("Mock exams, real length", "An 18th Edition mock exam in Sparkwise: question 23 of 60 with the timer and an open-book reminder"),
            "04-question": ("Know where to look", "An answered question in Sparkwise with the explanation and the regulation and table to look up"),
            "05-worked": ("Every calculation, worked", "A Sparkwise worked solution: the maximum Zs for a 20 A Type B circuit-breaker, step by step, with the common mistake"),
            "06-max-zs": ("Max Zs in one tap", "The Sparkwise maximum Zs calculator for Type B, C and D circuit-breakers with the 80% rule"),
            "07-a4": ("What changed in A4:2026", "The Sparkwise Amendment 4 hub listing new and changed regulations to read"),
            "08-results": ("Pay once. Both exams.", "Sparkwise practice test results for the ECS HS&E, by topic (sample data)"),
            # Sparkwise 1.2.0 emulator screens (28/11/2026), 480x1067
            "11-exam-switch": ("12 exams in one app", "The Sparkwise exam switcher: ECS HS&E, 18th Edition, PAT 2377, EV 2921-34, 2391-52, 2391-50, 2391-51, ECS ESU, AM2 knowledge, EWA entry test, Solar PV 2922 and Battery 2923", (480, 1067)),
            "20-pat-home": ("PAT 2377 home", "Sparkwise home screen for PAT 2377 with today's practice, Quick 10 and a 105-minute mock test", (480, 1067)),
            "21-pat-mock": ("PAT mock: 50 questions, 1 h 45", "A Sparkwise PAT 2377 mock test: question 1 of 50, open book, with the timer at 1:44:56", (480, 1067)),
            "22-pat-explain": ("Every answer explained", "An answered PAT 2377 question on equipment types with the explanation and its source", (480, 1067)),
            "23-pat-result": ("Results by area", "A PAT 2377 mock result with the 40 of 50 pass mark and marks by area (sample data)", (480, 1067)),
            "24-pat-paywall": ("Unlock one exam, or all", "The Sparkwise unlock screen: PAT 2377 for £7.99 or All exams for £24.99, both one-off", (480, 1067)),
            "30-am2-mocks": ("AM2 mock tests", "The Sparkwise AM2 knowledge mock list: 45 questions, 90 minutes, open book, one free mock", (480, 1067)),
            "31-am2-mock": ("AM2 knowledge mock", "A Sparkwise AM2 knowledge mock: question 1 of 45, a Select TWO question on Section 443, with the timer", (480, 1067)),
            "32-am2-explain": ("Every answer explained", "An answered AM2 knowledge question on safe isolation with the explanation and where to look", (480, 1067)),
            "33-am2-paywall": ("AM2 knowledge: £9.99 once", "The Sparkwise unlock screen: AM2 knowledge for £9.99 or All exams for £24.99, both one-off", (480, 1067)),
            "40-ewa-topics": ("EWA topics by Part", "The Sparkwise EWA entry test topic list, Part 1 knowledge and Part 2 scenarios", (480, 1067)),
            "41-ewa-mock": ("EWA mock: 50 questions", "A Sparkwise EWA entry test mock: question 1 of 50, open book, with the 100-minute timer", (480, 1067)),
            "42-ewa-result": ("Scored by Part", "An EWA entry test mock result with the score for Part 1 and Part 2 (sample data)", (480, 1067)),
            "43-ewa-paywall": ("EWA entry test: £7.99 once", "The Sparkwise unlock screen: EWA entry test for £7.99 or All exams for £24.99, both one-off", (480, 1067)),
            "50-2391-paywall": ("Three 2391 exams, one unlock", "The Sparkwise unlock screen in dark mode and large text: 2391-52, 2391-50 and 2391-51 for £9.99, or All exams for £24.99", (480, 1067)),
        },
        shots=["03-mock", "04-question", "05-worked"],
        notice='<strong>Not a government app.</strong> Sparkwise is an independent study app made by Kodfu Bilisim. It is not affiliated with or endorsed by the IET, BSI, City &amp; Guilds, EAL, NET, the ECS, the JIB, NICEIC, NAPIT, MCS, HSE or OZEV. It does not contain the real exam questions and never reproduces BS 7671 text.',
        disclaimer='Sparkwise is an independent study app made by Kodfu Bilisim. Not affiliated with or endorsed by the IET, BSI, City &amp; Guilds, EAL, NET, the ECS, the JIB, NICEIC, NAPIT, MCS, HSE or OZEV. Practice questions are original; always check real installations against your own copy of BS 7671.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<div class="cta-head"><img src="~/favicon.svg" width="48" height="48" alt=""><h2 id="cta-h">Practise both exams in the Sparkwise app</h2></div>
<p>{{count:bs7671+ecs-hse}} original questions across every Part of BS 7671:2018+A4:2026 and every ECS HS&amp;E syllabus area, timed mock exams in the real format, worked solutions for calculations and explanations that show where to look in the book.</p>
<ul class="plain">
<li>18th Edition: {{count:bs7671}} questions, 60-question mock exams in 2 hours, a maximum Z<sub>s</sub> calculator and a guide to Amendment 4</li>
<li>ECS HS&amp;E: {{count:ecs-hse}} questions and 50-question mock tests in 30 minutes</li>
<li>Works offline. No ads, no account, no data collected.</li>
</ul>
<!--shots-->
<p><strong>Free:</strong> two full topics in each exam, three questions in every other topic, one full mock exam for each exam, the maximum Z<sub>s</sub> calculator and checklists.<br><strong>Sparkwise Pro, £12.99 one-off:</strong> every question, every mock exam and every worked solution, for both exams. No subscription.</p>
<p>''' + PLAY_BTN.format(pos="footer") + '''</p>
<p class="muted small">Also in Sparkwise, each sold on its own: <a href="~/pat-testing-exam-2377/">PAT 2377</a>, <a href="~/ev-charging-exam-2921/">EV 2921-34</a>, <a href="~/inspection-testing-exam-2391/">2391</a>, <a href="~/ecs-electrical-safety-unit/">ECS Electrical Safety Unit</a>, <a href="~/am2-knowledge-test/">AM2 knowledge test</a>, <a href="~/ewa-entry-test/">EWA entry test</a> and <a href="~/solar-pv-battery-exam-2922-2923/">solar PV and battery storage</a>, or <a href="~/exams/">all {{count:exams}} exams for {{price:all}}</a>.</p>
<p class="muted small"><!--ios--> Sparkwise helps you prepare; it cannot promise a pass.</p>
</section>'''),
    "bluebell": dict(
        host="bluebell.kodfu.com", name="Bluebell", tagline="Life in the UK Test practice",
        pkg="com.kodfu.bluebell", category="EducationalApplication", bundle="bluebell", promote=True,
        light="--bg:#FFFFFF;--fg:#14171C;--muted:#4A5260;--line:#E3E6EB;--card:#F6F7F9;--accent:#4A4FB8;--on-accent:#FFFFFF;--chip:#E9EAFF;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#111316;--fg:#ECEEF2;--muted:#B4BAC4;--line:#2A2F36;--card:#1A1D22;--accent:#AEB1FF;--on-accent:#111316;--chip:#262A5C;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        band="--band:#4A4FB8;--band2:#3F44A8;--on-band:#FFFFFF;--band-muted:#E4E5FF;--band-chip:rgba(0,0,0,.18);--band-hl:#FFFFFF;--band-line:rgba(255,255,255,.18);--play:#FFFFFF;--on-play:#3F44A8",
        band_edge="0",
        nav=[("home", "Home", ""), ("guide", "Test guide", "guide/"), ("practice", "Free practice", "practice/")],
        pitch="Practise for the Life in the UK Test on your phone: {{count:all}} original questions and full 24-question mock tests.",
        sticky_sub="Free to try · Pro £6.99 once",
        appcta_sub="Free to try · Pro £6.99 one-off · no subscription",
        pro_line="Bluebell Pro is £6.99 one-off: every question, every mock test and every study note. No subscription.",
        screens={
            "01-home": ("Life in the UK Test practice", "Bluebell home screen with a readiness score, a test date countdown and today's practice"),
            "02-mock": ("Mock tests like the real one", "A Bluebell mock test: question 7 of 24 with the 45-minute timer"),
            "04-question": ("Clear answers, every time", "An answered Bluebell question with a plain-English explanation and its source"),
            "05-checklist": ("Never miss your refund date", "The Bluebell test-day checklist with the free cancellation deadline"),
            "07-handbook": ("See what's changed since 2013", "Bluebell's Handbook vs today screen: facts that changed since the handbook was printed"),
        },
        shots=["02-mock", "04-question", "07-handbook"],
        notice='<strong>Not a government app.</strong> Bluebell is an independent study app made by Kodfu Bilisim. It does not represent the Home Office, UK Visas and Immigration or any government body, and it is not affiliated with or endorsed by them or by TSO.',
        disclaimer='Not a government app. Bluebell is an independent study app made by Kodfu Bilisim. It is not affiliated with or endorsed by the Home Office, UK Visas and Immigration or TSO (The Stationery Office). Bluebell&#8217;s guides are general information, not immigration advice.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<div class="cta-head"><img src="~/favicon.svg" width="48" height="48" alt=""><h2 id="cta-h">Want more practice? Get the Bluebell app</h2></div>
<p>{{count:all}} original practice questions across all five chapters of the handbook, plain-English explanations, full mock tests of 24 questions in 45 minutes, spaced review and a mistakes list. It works offline, with no ads and no account.</p>
<!--shots-->
<p><strong>Free:</strong> Chapter 1 in full, six free questions in every other topic, two full mock tests and all the tools.<br><strong>Bluebell Pro, £6.99 one-off:</strong> every question, every mock test and every study note. No subscription.</p>
<p>''' + PLAY_BTN.format(pos="footer") + '''</p>
<p class="muted small"><!--ios--> Bluebell helps you prepare; it cannot promise a pass.</p>
</section>'''),
    "hivis": dict(
        host="hivis.kodfu.com", name="HiVis", tagline="CITB HS&E test practice",
        pkg="com.kodfu.hivis", category="EducationalApplication", bundle="hivis", promote=True,
        light="--bg:#FFFFFF;--fg:#14171C;--muted:#4A5260;--line:#E3E6EB;--card:#F6F7F9;--accent:#C2410C;--on-accent:#FFFFFF;--chip:#FFF7ED;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#111316;--fg:#ECEEF2;--muted:#B4BAC4;--line:#2A2F36;--card:#1A1D22;--accent:#FDBA74;--on-accent:#111316;--chip:#3A2416;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        band="--band:#B23A09;--band2:#C2410C;--on-band:#FFFFFF;--band-muted:#FFE7D1;--band-chip:rgba(0,0,0,.2);--band-hl:#FFD400;--band-line:rgba(255,255,255,.18);--play:#FFD400;--on-play:#14171C",
        band_edge="4px solid #FFD400",
        nav=[("home", "Home", ""), ("guide", "Test guide", "guide/"), ("practice", "Free practice", "practice/")],
        pitch="Practise for the CITB HS&amp;E test on your phone: {{count:all}} original questions for seven tests and full 50-question mock tests.",
        sticky_sub="Free to try · Pro £5.99 once",
        appcta_sub="Free to try · Pro £5.99 one-off, every test · no subscription",
        pro_line="HiVis Pro is £5.99 one-off: every question and every mock test for all test levels. No subscription.",
        screens={
            "01-home": ("Prepare for your HS&E test", "HiVis home screen for the Operatives test with a readiness score and the days left to the test"),
            "02-mock": ("50 questions in 45 minutes", "A HiVis mock test: question 23 of 50 with the 45-minute timer"),
            "04-question": ("Simple English, read aloud", "An answered HiVis question with a simple explanation, its source and a read aloud button"),
            "05-card-finder": ("Find the card you need", "The HiVis Card Finder suggesting a card and the test to practise"),
            "06-choose-test": ("Every test, one payment", "Choosing a test in HiVis: Operatives, Supervisory, Managers and Professionals and specialist tests"),
        },
        shots=["02-mock", "04-question", "05-card-finder"],
        notice='<strong>Not a government app.</strong> HiVis is an independent study app made by Kodfu Bilisim. It is not affiliated with or endorsed by CITB, CSCS, Pearson VUE or HSE, and it does not contain the real test questions.',
        disclaimer='Not a government app. HiVis is an independent study app made by Kodfu Bilisim. It is not affiliated with or endorsed by CITB, CSCS or Pearson VUE.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<div class="cta-head"><img src="~/favicon.svg" width="48" height="48" alt=""><h2 id="cta-h">Practise every test in the HiVis app</h2></div>
<p>{{count:all}} original questions for the Operatives, Supervisory, Managers and Professionals and specialist HS&amp;E tests, full timed mock tests of 50 questions in 45 minutes, simple explanations with read aloud, a study plan and spaced review. It works offline, with no ads and no account.</p>
<!--shots-->
<p><strong>Free:</strong> three topics in full, three questions in every other topic, one full mock test for each test, the Card Finder and Site words.<br><strong>HiVis Pro, £5.99 one-off:</strong> every question and every mock test for all test levels. No subscription.</p>
<p>''' + PLAY_BTN.format(pos="footer") + '''</p>
<p class="muted small"><!--ios--> HiVis helps you prepare; it cannot promise a pass.</p>
</section>'''),
    "tickover": dict(
        host="tickover.kodfu.com", name="Tickover", tagline="MOT, tax and insurance reminders",
        pkg="com.kodfu.tickover", category="UtilitiesApplication", promote=False,
        light="--bg:#FFFFFF;--fg:#14171C;--muted:#4A5260;--line:#E3E6EB;--card:#F6F7F9;--accent:#0B6E4F;--on-accent:#FFFFFF;--chip:#D5F2E6;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#111316;--fg:#ECEEF2;--muted:#B4BAC4;--line:#2A2F36;--card:#1A1D22;--accent:#4CC9A0;--on-accent:#00261A;--chip:#0F3B2D;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        band="--band:#0B6E4F;--band2:#0B6E4F;--on-band:#FFFFFF;--band-muted:#D5F2E6;--band-chip:rgba(0,0,0,.18);--band-hl:#FFFFFF;--band-line:rgba(255,255,255,.18);--play:#FFFFFF;--on-play:#0B6E4F",
        band_edge="0",
        nav=[("home", "Home", ""), ("guide", "MOT and tax guide", "guide/")],
        notice='<strong>Not a government service.</strong> Tickover is an independent app made by Kodfu Bilisim. It is not affiliated with or endorsed by DVLA, DVSA, HMRC, TfL or any local council. To tax a vehicle, make a SORN or book an MOT, use GOV.UK.',
        disclaimer='Tickover is an independent app made by Kodfu Bilisim. It is not a government service and is not affiliated with or endorsed by DVLA, DVSA, HMRC, TfL or any local council. For official services, visit <a href="https://www.gov.uk/" rel="noopener">GOV.UK</a>.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<h2 id="cta-h">Never miss an MOT or tax date</h2>
<p>Tickover keeps your vehicles&#8217; MOT, tax and insurance dates in one place and reminds you before each one runs out. Unlimited vehicles and reminders are free. No account, no ads.</p>
<p><strong>Tickover Pro:</strong> £7.99 a year with a 7-day free trial, or £24.99 once for lifetime. Prices include VAT.</p>
<p><a class="btn" href="~play:footer" rel="noopener">Get Tickover on Google Play</a></p>
<p class="muted small">For Android phones, in the United Kingdom.</p>
</section>'''),
    "fareback": dict(
        host="fareback.kodfu.com", name="FareBack", tagline="Help with late train claims",
        pkg="com.kodfu.fareback", category="TravelApplication", promote=True,
        light="--bg:#F5F6F3;--fg:#10212B;--muted:#4A5A63;--line:#DCE1DD;--card:#FFFFFF;--accent:#0A6B57;--on-accent:#FFFFFF;--chip:#E2F1EC;--ok:#17733A;--okbg:#E7F4EC;--warnbg:#FFF3D6",
        dark="--bg:#121412;--fg:#E9EFEB;--muted:#A9B3AE;--line:#2E3833;--card:#1B211E;--accent:#4CD9A0;--on-accent:#0A2E22;--chip:#12392B;--ok:#4ADE80;--okbg:#10301C;--warnbg:#3A2A08",
        band="--band:#0A6B57;--band2:#0A6B57;--on-band:#FFFFFF;--band-muted:#D5EFE6;--band-chip:rgba(0,0,0,.18);--band-hl:#FFFFFF;--band-line:rgba(255,255,255,.18);--play:#FFFFFF;--on-play:#0A6B57",
        band_edge="0",
        nav=[("home", "Support", ""), ("guide", "Delay Repay guide", "guide/")],
        pitch="FareBack checks your saved train journeys, tells you when a delay may qualify and gets your Delay Repay claim ready. Free to use.",
        sticky_sub="Free · for train journeys in Great Britain",
        appcta_sub="Free to use · Pro optional, 7-day free trial on annual",
        notice='<strong>Independent app.</strong> FareBack is made by Kodfu Bilisim. It is not affiliated with or endorsed by any train company, National Rail, Network Rail, Rail Delivery Group, Great British Railways or the Department for Transport. You submit every claim yourself; the train company decides whether to pay.',
        disclaimer='FareBack is made by Kodfu Bilisim. It is not affiliated with or endorsed by any train company, National Rail, Network Rail, Rail Delivery Group, Great British Railways or the Department for Transport. &#8220;Delay Repay&#8221; is the name of the train companies&#8217; compensation scheme and is used here only to describe that scheme.',
        cta='''<section class="card cta" aria-labelledby="cta-h">
<div class="cta-head"><img src="~/favicon.svg" width="48" height="48" alt=""><h2 id="cta-h">Let FareBack watch your journeys</h2></div>
<p>Save a journey and FareBack checks it after the train arrives, tells you when a delay may qualify for compensation and gets your Claim Pack ready. You submit the claim yourself on the train company&#8217;s website, and any money goes to you.</p>
<p><strong>Free</strong> to use. <strong>FareBack Pro</strong> (optional): £1.99 a month or £12.99 a year with a 7-day free trial. Prices include VAT.</p>
<p>''' + PLAY_BTN.format(pos="footer") + '''</p>
<p class="muted small"><!--ios--> For train journeys in Great Britain.</p>
</section>'''),
}

# Sparkwise 1.2.0 (Google Play, 28/11/2026): every new exam is sold on its own inside the one app
# (owner decision 27/11/2026, ~/Code/exam-apps/AGENTS.md; product ids and prices in
# ~/Code/exam-apps/config/sparkwise.json PRODUCTS). `sparkwise_pro_lifetime` (£12.99) keeps covering
# 18th Edition + ECS HS&E; "All exams" (£24.99) covers every exam, present and future.
# A fragment with `pack: <key>` in its meta gets the pack's sticky bar, app boxes, after-questions
# line, closing card (<!--cta-->) and sources card (<!--sources-->). {{price:<key>|pro|all}} prints a price.
PRO_PRICE = "£12.99"
ALL_EXAMS_PRICE = "£24.99"
C_G = "https://www.cityandguilds.com/qualifications-and-apprenticeships/building-services-industry/electrical-installation/"
PACKS = {
    "cg2377": dict(
        short="PAT 2377", exams=["cg2377"], unlock="PAT 2377", price="£7.99", page="pat-testing-exam-2377/",
        label="PAT testing (2377-77)", what="the C&amp;G 2377-77 PAT testing exam",
        mocks="timed 50-question mocks of 1 hour 45 minutes with the 40-of-50 pass mark",
        shots=["21-pat-mock", "22-pat-explain", "24-pat-paywall"],
        sources=[("2377 Electrical Equipment Maintenance and Testing", "City & Guilds", C_G + "2377-electrical-equipment-maintenance-and-testing"),
                 ("Maintaining portable electrical equipment (INDG236)", "Health and Safety Executive (HSE)", "https://www.hse.gov.uk/pubns/indg236.htm"),
                 ("Portable appliance testing FAQs", "Health and Safety Executive (HSE)", "https://www.hse.gov.uk/electricity/faq-portable-appliance-testing.htm"),
                 ("The Electricity at Work Regulations 1989", "legislation.gov.uk", "https://www.legislation.gov.uk/uksi/1989/635/contents")]),
    "cg2921": dict(
        short="EV 2921", exams=["cg2921"], unlock="EV 2921-34", price="£7.99", page="ev-charging-exam-2921/",
        label="EV charging (2921-34)", what="the C&amp;G 2921-34 EV charging exam",
        mocks="timed 30-question mocks of 1 hour",
        shots=["11-exam-switch", "32-am2-explain", "24-pat-paywall"],
        sources=[("2921 Electric Vehicle Charging", "City & Guilds", C_G + "2921-electric-vehicle-charging"),
                 ("Regulations: electric vehicle smart charge points", "GOV.UK", "https://www.gov.uk/guidance/regulations-electric-vehicle-smart-charge-points"),
                 ("Infrastructure for charging electric vehicles: Approved Document S", "GOV.UK", "https://www.gov.uk/government/publications/infrastructure-for-charging-electric-vehicles-approved-document-s"),
                 ("BS 7671 18th Edition wiring regulations", "IET", "https://electrical.theiet.org/bs-7671-18th-edition-wiring-regulations/")]),
    "cg2391": dict(
        short="2391", exams=["cg2391", "cg2391-50", "cg2391-51"], unlock="2391-52 + 2391-50 + 2391-51", price="£9.99",
        page="inspection-testing-exam-2391/", label="2391 inspection and testing", what="the C&amp;G 2391-52, 2391-50 and 2391-51 exams",
        mocks="timed mocks in each format: 60 questions in 2 hours for 2391-52, 40 questions in 90 minutes for 2391-50 and 2391-51",
        shots=["11-exam-switch", "22-pat-explain", "50-2391-paywall"],
        sources=[("2391 Initial and Periodic Electrical Inspection and Testing", "City & Guilds", C_G + "2391-initial-and-periodic-electrical-inspection-and-testing"),
                 ("BS 7671 18th Edition wiring regulations", "IET", "https://electrical.theiet.org/bs-7671-18th-edition-wiring-regulations/"),
                 ("Electrical safety standards in the private and social rented sectors", "GOV.UK", "https://www.gov.uk/government/publications/electrical-safety-standards-in-the-private-and-social-rented-sectors-guidance")]),
    "ecs-esu": dict(
        short="ECS ESU", exams=["ecs-esu"], unlock="ECS ESU", price="£7.99", page="ecs-electrical-safety-unit/",
        label="ECS Electrical Safety Unit", what="the ECS Electrical Safety Unit assessment",
        mocks="timed 30-question mocks of 30 minutes with the 21-of-30 pass mark",
        shots=["11-exam-switch", "32-am2-explain", "24-pat-paywall"],
        sources=[("Electrical Safety Unit assessment", "ECS, run by the JIB", "https://www.ecscard.org.uk/content/Electrical-Safety-Unit-Assessment"),
                 ("ECS Related Discipline card", "ECS, run by the JIB", "https://www.ecscard.org.uk/card-types/Related-Disciplines/ECS-Related-Discipline"),
                 ("Electricity at work: safe working practices (HSG85)", "Health and Safety Executive (HSE)", "https://www.hse.gov.uk/pubns/books/hsg85.htm")]),
    "am2": dict(
        short="AM2", exams=["am2"], unlock="AM2 knowledge", price="£9.99", page="am2-knowledge-test/",
        label="AM2 knowledge test", what="the AM2, AM2S and AM2E knowledge test (Section E)",
        mocks="timed 45-question mocks of 90 minutes, the AM2S v1 Section E format",
        shots=["31-am2-mock", "32-am2-explain", "33-am2-paywall"],
        sources=[("AM2", "NET", "https://www.netservices.org.uk/am2/"),
                 ("AM2S v1", "NET", "https://www.netservices.org.uk/am2s-v1/"),
                 ("AM2E", "NET", "https://www.netservices.org.uk/am2e/"),
                 ("AM2 pre-assessment manual", "NET", "https://www.netservices.org.uk/pre-assessment-manual/")]),
    "ewa": dict(
        short="EWA", exams=["ewa"], unlock="EWA entry test", price="£7.99", page="ewa-entry-test/",
        label="EWA entry test", what="the EWA entry test",
        mocks="timed 50-question mocks of 100 minutes, scored by Part 1 and Part 2",
        shots=["41-ewa-mock", "42-ewa-result", "43-ewa-paywall"],
        sources=[("EWA entry test", "Electrotechnical Skills Partnership (TESP)", "https://www.electrical-ewa.org.uk/entry-test/"),
                 ("Experienced Worker Entry Test", "NAPIT", "https://www.napit.org.uk/napit-training/electrical-training/ewet/"),
                 ("BS 7671 18th Edition wiring regulations", "IET", "https://electrical.theiet.org/bs-7671-18th-edition-wiring-regulations/")]),
    "cg2922": dict(
        short="Solar + battery", exams=["cg2922", "cg2923"], unlock="Solar PV 2922 + Battery 2923", price="£7.99",
        page="solar-pv-battery-exam-2922-2923/", label="solar PV and battery storage", what="the C&amp;G 2922-34 solar PV and 2923-34 battery storage exams",
        mocks="timed 30-question mocks of 1 hour for each exam",
        shots=["11-exam-switch", "22-pat-explain", "24-pat-paywall"],
        sources=[("2922 Small Solar Photovoltaic Systems", "City & Guilds", C_G + "2922-small-solar-photovoltaic-systems"),
                 ("2923 Small Electrical Energy Storage Systems", "City & Guilds", C_G + "2923-small-electrical-energy-storage-systems"),
                 ("BS 7671 18th Edition wiring regulations", "IET", "https://electrical.theiet.org/bs-7671-18th-edition-wiring-regulations/")]),
}


def price(key):
    return {"pro": PRO_PRICE, "all": ALL_EXAMS_PRICE}.get(key) or PACKS[key]["price"]


def pack_key(pack):
    return "|".join(pack["exams"])


def pack_cfg(cfg, key):
    """Site config for a page that sells one exam pack."""
    p = PACKS[key]
    k = pack_key(p)
    one = len(p["exams"]) == 1
    scope = "this exam" if one else "these exams"
    each = "" if one else " in each exam"
    free_line = (f"two full topics and three questions in every other topic{each}, and one full mock "
                 + ("" if one else "for each exam ") + "({{free:" + k + "}} questions)")
    pro_line = (f"The {p['unlock']} unlock is {p['price']} one-off: every question and every mock for {scope}. "
                f"Or get All exams, {ALL_EXAMS_PRICE} one-off: all {{{{count:exams}}}} exams in Sparkwise and any exam added later. No subscription.")
    cta = f'''<section class="card cta" aria-labelledby="cta-h">
<div class="cta-head"><img src="~/favicon.svg" width="48" height="48" alt=""><h2 id="cta-h">Practise {p['what']} in the Sparkwise app</h2></div>
<p>{{{{count:{k}}}}} original questions for {p['what']}, each with an explanation and where to look, and {p['mocks']}. Spaced review brings back the questions you got wrong.</p>
<ul class="plain">
<li>Works offline. No ads, no account, no data collected.</li>
<li>The same app has the 18th Edition, the ECS HS&amp;E and every other exam: <a href="~/exams/">see all {{{{count:exams}}}}</a>.</li>
</ul>
<!--shots-->
<p><strong>Free:</strong> {free_line}.<br><strong>{p['unlock']}, {p['price']} one-off:</strong> every question and every mock for {scope}.<br><strong>All exams, {ALL_EXAMS_PRICE} one-off:</strong> all {{{{count:exams}}}} exams in Sparkwise and every exam we add later. No subscription.</p>
<p>''' + PLAY_BTN.format(pos="footer") + '''</p>
<p class="muted small"><!--ios--> Sparkwise helps you prepare; it cannot promise a pass.</p>
</section>'''
    return dict(cfg, pack=key, cta=cta, pro_line=pro_line, shots=p["shots"],
                sticky_sub=f"Free to try · {p['short']} {p['price']} once",
                appcta_sub=f"Free to try · {p['price']} one-off for {scope} · no subscription")


CSS = """:root{color-scheme:light dark;%(light)s;%(band)s}
@media (prefers-color-scheme:dark){:root{%(dark)s}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%%}
body{margin:0;background:var(--bg);color:var(--fg);font:400 1.0625rem/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,system-ui,sans-serif;overflow-wrap:break-word}
.wrap{max-width:760px;margin:0 auto;padding:0 max(16px,env(safe-area-inset-right)) 0 max(16px,env(safe-area-inset-left))}
.home .wrap{max-width:960px}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px;border-radius:4px}
.band a:focus-visible,.sticky a:focus-visible{outline-color:var(--band-hl)}
.skip{position:absolute;left:-9999px;top:0}
.skip:focus{left:16px;top:8px;background:var(--bg);color:var(--fg);padding:8px 12px;z-index:20}
header.site{background:linear-gradient(180deg,var(--band),var(--band2));color:var(--on-band);border-bottom:%(band_edge)s;margin-bottom:20px}
.band a{color:var(--on-band)}
.brand{display:inline-flex;align-items:center;gap:12px;text-decoration:none;margin:12px 0 10px}
.brand svg,.mark{width:44px;height:44px;border-radius:11px;flex:none}
.mark{background:var(--play);color:var(--on-play);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:20px}
.brand strong{display:block;font-size:1.25rem;line-height:1.2}
.brand small{display:block;color:var(--band-muted);font-size:.9375rem}
nav.main ul{display:flex;gap:6px;list-style:none;margin:0;padding:0 0 12px;overflow-x:auto;scrollbar-width:thin}
nav.main li{flex:none}
nav.main a{display:inline-flex;align-items:center;min-height:44px;padding:0 14px;border-radius:12px;background:var(--band-chip);text-decoration:none;font-weight:600;font-size:.9375rem;white-space:nowrap}
nav.main a[aria-current=page]{box-shadow:inset 0 -3px 0 var(--band-hl)}
.pitch{display:flex;align-items:center;justify-content:space-between;gap:16px;border-top:1px solid var(--band-line);padding:10px 0 12px}
.pitch p{margin:0;font-size:.9375rem;line-height:1.45;max-width:none}
.pitch .btn{display:none;flex:none}
.btn{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 20px;border-radius:12px;background:var(--accent);color:var(--on-accent);font-weight:700;text-decoration:none;text-align:center;line-height:1.2}
.btn.ghost{background:transparent;color:var(--accent);border:1.5px solid var(--line)}
.band .btn.play,.sticky .btn{background:var(--play);color:var(--on-play)}
.band .btn.ghost{color:var(--on-band);border-color:var(--band-line);background:var(--band-chip)}
.hero{display:grid;gap:20px;align-items:center;padding:8px 0 28px}
.hero h1{font-size:2rem;margin:4px 0 12px}
.hero .lead{max-width:38em}
.hero .kicker{margin:0;font-weight:700;color:var(--band-hl);font-size:.9375rem;letter-spacing:.02em}
.hero .actions{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 10px}
.hero .facts{color:var(--band-muted);font-size:.9375rem;margin:6px 0}
.hero .shot{justify-self:center;width:min(240px,62vw);border:0;box-shadow:0 12px 40px rgba(0,0,0,.35)}
main{padding-bottom:40px}
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
.cta{border:2px solid var(--accent)}
.cta-head{display:flex;align-items:center;gap:12px;margin-bottom:8px}
.cta-head img{width:48px;height:48px;border-radius:12px;flex:none}
.cta-head h2{margin:0}
.callout{border-left:4px solid var(--accent);background:var(--chip);border-radius:0 12px 12px 0;padding:12px 16px;margin:16px 0}
.callout>:first-child{margin-top:0}.callout>:last-child{margin-bottom:0}
.appcta{display:grid;grid-template-columns:44px 1fr;gap:14px;align-items:start;background:var(--chip);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:14px;padding:14px 16px;margin:24px 0}
.appcta img{width:44px;height:44px;border-radius:11px}
.appcta p{margin:0 0 8px}
.appcta p:last-child{margin:0}
.appcta .sub{font-size:.875rem;color:var(--muted)}
.aq{border:2px solid var(--accent)}
.aq h2{margin-top:0}
.shots{display:flex;gap:12px;overflow-x:auto;margin:14px 0;padding:2px 2px 8px;list-style:none}
.shots li{flex:0 0 140px;margin:0}
.shot{display:block;width:100%%;height:auto;border-radius:14px;border:1px solid var(--line)}
.features{display:grid;gap:8px;max-width:760px}
.feature{display:grid;gap:16px;align-items:center;margin:16px 0}
.feature .shot{width:min(200px,56vw);justify-self:center}
.feature h3{margin-top:0}
.plans{display:grid;gap:14px;margin:16px 0}
.plan{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 18px}
.plan.pro{border:2px solid var(--accent)}
.plan h3{margin:0 0 4px}
.plan .price{font-size:1.5rem;font-weight:800;margin:0 0 8px}
.plan ul{padding-left:20px;margin:0 0 12px}
.ios{font-size:.875rem}
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
.sticky{position:sticky;bottom:0;z-index:10;background:var(--band);color:var(--on-band);border-top:1px solid var(--band-line);box-shadow:0 -4px 16px rgba(0,0,0,.18)}
.sticky .wrap{display:flex;align-items:center;gap:10px;padding-top:8px;padding-bottom:calc(8px + env(safe-area-inset-bottom))}
.sticky img{width:36px;height:36px;border-radius:9px;flex:none}
.sticky .s-txt{flex:1;min-width:0;line-height:1.25}
.sticky strong{display:block;font-size:.9375rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sticky small{display:block;font-size:.8125rem;color:var(--band-muted)}
.sticky .btn{min-height:44px;padding:0 14px;font-size:.9375rem;flex:none}
@media (max-width:480px){h1{font-size:1.625rem}.hero h1{font-size:1.75rem}.lead{font-size:1.0625rem}.pitch p{font-size:.875rem}}
@media (max-width:359px){.sticky small{display:none}}
@media (min-width:640px){.plans{grid-template-columns:1fr 1fr}.feature{grid-template-columns:200px 1fr;gap:28px}.feature.flip{grid-template-columns:1fr 200px}.feature.flip .shot{order:2}.feature .shot{width:200px}}
@media (min-width:760px){.hero{grid-template-columns:1fr 260px;padding:16px 0 40px}.hero .shot{width:260px}.hero h1{font-size:2.375rem}.pitch .btn{display:inline-flex}.sticky{display:none}}
@media (prefers-color-scheme:dark){.hero .shot{box-shadow:0 12px 40px rgba(0,0,0,.6)}}
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
    return re.sub(r'(href|src)="~/([^"]*)"', sub, body)


def relink_href(target, path):
    return re.search(r'href="([^"]*)"', relink(f'href="~/{target}"', path)).group(1)


def sources_card(app, pack=None):
    items = "\n".join(f'<li><a href="{E(u)}" rel="noopener">{E(t)}</a> <span class="muted">({E(p)})</span></li>'
                      for t, p, u in (PACKS[pack]["sources"] if pack else SOURCES[app]))
    if pack:  # exam pages: never the word "official" (owner copy rule for the 1.2.0 exam pages)
        return (f'<section class="card" aria-labelledby="sources-h">\n<h2 id="sources-h">Where the exam facts come from</h2>\n'
                f'<p class="muted">The format, time and pass mark above come from these public pages. Check them, or ask your centre, before you book.</p>\n<ul class="plain">\n{items}\n</ul>\n'
                f'<p class="muted small">Exam details can change. Sparkwise is not linked to any awarding or assessment body.</p>\n</section>')
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


# ---------- shipped bundle facts (every number on the sites comes from here) ----------

def unverified_ids(brand):
    ids = set()
    for f in glob.glob(os.path.join(EXAM_APPS, "content", brand, "**", "*.json"), recursive=True):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("questions"), list):
            for q in d["questions"]:
                if isinstance(q, dict) and q.get("verify"):
                    ids.add(q.get("id"))
    return ids


_BUNDLES = {}


def load_bundle(brand):
    if brand not in _BUNDLES:
        d = json.load(open(os.path.join(EXAM_APPS, "app", "assets", "content", f"{brand}.json")))
        bad = unverified_ids(brand)
        files = d["files"]
        for f in files.values():
            if isinstance(f, dict) and isinstance(f.get("questions"), list):
                f["questions"] = [q for q in f["questions"] if q.get("id") not in bad and q.get("correct") and q.get("options")]
        _BUNDLES[brand] = files
    return _BUNDLES[brand]


_FACTS = {}


def facts(brand):
    """Counts per exam and topic: n (shipped questions), free (questions free in the app), worked."""
    if brand in _FACTS:
        return _FACTS[brand]
    files = load_bundle(brand)
    exams = {}
    for k, m in files.items():
        if not (k.startswith("manifest.") and k != "manifest.json"):
            continue
        free_ids, per = m.get("freeTopicIds", []), m.get("freeQuestionsPerTopic", 0)
        topics = {}
        for t in m["topics"]:
            qs = files[t["file"]]["questions"]
            n = len(qs)
            free_q = qs if t["id"] in free_ids else qs[:per]   # free = free topics in full + first N of the rest
            topics[t["id"]] = dict(n=n, free=len(free_q), free_topic=t["id"] in free_ids,
                                   worked=sum(1 for q in qs if q.get("worked")), title=t["title"],
                                   group=t.get("group", ""), part=t.get("part") or t.get("area") or "",
                                   ids={q["id"] for q in qs}, free_set={q["id"] for q in free_q},
                                   worked_set={q["id"] for q in qs if q.get("worked")})
        ids = set().union(*(t["ids"] for t in topics.values()))
        free_set = set().union(*(t["free_set"] for t in topics.values()))
        worked_set = set().union(*(t["worked_set"] for t in topics.values()))
        exams[m["id"]] = dict(title=m["title"], short=m.get("shortTitle", m["title"]), mock=m["mock"], topics=topics,
                              free_ids=free_ids, per=per, n=len(ids), ids=ids, free_set=free_set, worked_set=worked_set,
                              free=len(free_set), worked=len(worked_set), description=m.get("description", ""),
                              order=m.get("order", 99))
    total = sum(len(f["questions"]) for f in files.values() if isinstance(f, dict) and isinstance(f.get("questions"), list))
    _FACTS[brand] = dict(exams=exams, total=total)
    return _FACTS[brand]


def fact(brand, kind, key):
    F = facts(brand)
    if "|" in key:  # {{count:cg2391|cg2391-50|cg2391-51}}: unique questions over exams that share topic files
        keys = [k.strip() for k in key.split("|")]
        for k in keys:
            if k not in F["exams"]:
                raise SystemExit(f"{brand}: unknown exam '{k}' in {{{{{kind}:{key}}}}}")
        if kind == "topics":
            return len({t for k in keys for t in F["exams"][k]["topics"]})
        field = {"count": "ids", "free": "free_set", "worked": "worked_set"}[kind]
        return len(set().union(*(F["exams"][k][field] for k in keys)))
    if "+" in key:  # {{count:bs7671+ecs-hse}}: the sum over several exams (Sparkwise Pro covers two)
        return sum(fact(brand, kind, k.strip()) for k in key.split("+"))
    if key == "exams":
        return len(F["exams"])
    if key == "all":
        if kind == "count":
            return F["total"]
        raise SystemExit(f"{{{{{kind}:all}}}} is not defined")
    exam, _, sub = key.partition("/")
    if exam not in F["exams"]:
        raise SystemExit(f"{brand}: unknown exam '{exam}' in {{{{{kind}:{key}}}}}")
    ex = F["exams"][exam]
    if kind == "topics":
        return len(ex["topics"])
    field = {"count": "n", "free": "free", "worked": "worked"}[kind]
    if not sub:
        return ex[field]
    if sub.startswith("group:"):
        g = sub[6:]
        ts = [t for t in ex["topics"].values() if t["group"].split(" ")[0] == g]
        if not ts:
            raise SystemExit(f"{brand}: no topics in group {g}")
        return sum(t[field] for t in ts)
    if sub not in ex["topics"]:
        raise SystemExit(f"{brand}: unknown topic '{sub}' in {{{{{kind}:{key}}}}}")
    return ex["topics"][sub][field]


def fill_counts(s, brand):
    s = re.sub(r"\{\{price:([\w-]+)\}\}", lambda m: price(m.group(1)), s)
    if not brand:
        return s
    return re.sub(r"\{\{(count|free|worked|topics):([^}]+)\}\}", lambda m: f"{fact(brand, m.group(1), m.group(2).strip()):,}", s)


def duration(minutes):
    if minutes % 60 == 0:
        h = minutes // 60
        return f"{h} hour" + ("s" if h > 1 else "")
    return f"{minutes} minutes"


def after_questions(app, cfg, shown, exam_id, sub=None, label=None):
    """The 'You've seen 10 of N' card after the questions on a practice page."""
    F = facts(cfg["bundle"])
    ex = F["exams"][exam_id]
    key = exam_id + (f"/{sub}" if sub else "")
    n, free = fact(cfg["bundle"], "count", key), fact(cfg["bundle"], "free", key)
    worked = fact(cfg["bundle"], "worked", key)
    name, mock = cfg["name"], ex["mock"]
    scope = label or ("this topic" if sub and not sub.startswith("group:") else ex["short"])
    worked_txt = f", and {worked} with a step-by-step worked solution" if worked else ""
    mock_txt = f"timed {mock['questionCount']}-question mock {'exams' if app == 'sparkwise' else 'tests'} of {duration(mock['minutes'])}"
    if sub:
        whole = f" Across the whole {ex['short']} there are {ex['n']:,} questions in {len(ex['topics'])} topics, plus {mock_txt}."
    else:
        whole = f" It also has {mock_txt}."
    if free == n:
        free_txt = f"<strong>All {n:,} are free</strong> in the app."
    else:
        free_txt = f"<strong>{free:,} of them are free</strong> in the app, the rest come with Pro."
    return f"""<section class="card aq" aria-labelledby="aq-h">
<h2 id="aq-h">You&#8217;ve seen {shown} of {n:,} questions {'in ' + E(scope) if scope else ''}</h2>
<p>The {E(name)} app has all {n:,}, each with an explanation{worked_txt}.{whole}</p>
<p>{free_txt} {cfg['pro_line']}</p>
<p>{PLAY_BTN.format(pos='after-questions')}</p>
<p class="muted ios"><!--ios--></p>
</section>"""


def sample_questions(brand, exams, n, ids=None):
    """A free sample for an exam page: one question from each topic file of the exams (shared files
    once), spread evenly, single-answer or 'Select TWO' items of middle difficulty first. `ids` picks them by hand."""
    files = load_bundle(brand)
    seen, per_topic, by_id = set(), [], {}
    for e in exams:
        for t in files[f"manifest.{e}.json"]["topics"]:
            if t["file"] in seen:
                continue
            seen.add(t["file"])
            qs = files[t["file"]]["questions"]
            for q in qs:
                by_id[q["id"]] = q
            good = [q for q in qs if q.get("difficulty") == 2 and q["type"] in ("single", "multi")
                    and len(q.get("explanation", "")) >= 60 and not q.get("scenario")] or qs
            per_topic.append(good[len(good) // 2])
    if ids:
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise SystemExit(f"{brand}: sample ids not shipped: {missing}")
        return [by_id[i] for i in ids]
    return pick(per_topic, n)


def after_sample(cfg, shown, key):
    """'You've seen 8 of N' card after the sample on an exam page (the page's pack sets pro_line)."""
    exams = key.split("|")
    F = facts(cfg["bundle"])
    n, free, worked = (fact(cfg["bundle"], k, key) for k in ("count", "free", "worked"))
    p = PACKS.get(cfg.get("pack"), {})
    label = p.get("label") or F["exams"][exams[0]]["short"]
    topics = fact(cfg["bundle"], "topics", key)
    worked_txt = f", and {worked} calculations have a step-by-step worked solution" if worked else ""
    return f"""<section class="card aq" aria-labelledby="aq-h">
<h2 id="aq-h">You&#8217;ve seen {shown} of {n:,} questions for the {E(label)}</h2>
<p>The {E(cfg['name'])} app has all {n:,} across {topics} topics, each with an explanation and where to look{worked_txt}. It also has {p.get('mocks', 'timed mock exams')}.</p>
<p><strong>{free:,} of them are free</strong> in the app. {cfg['pro_line']}</p>
<p>{PLAY_BTN.format(pos='after-questions')}</p>
<p class="muted ios"><!--ios--></p>
</section>"""


# ---------- screenshots ----------

SHOT_W, SHOT_H = 480, 853


def ensure_screens(app, cfg, out):
    names = list(cfg.get("screens", {}))
    if not names:
        return
    src = os.path.join(ROOT, "src", app, "screens")
    dst = os.path.join(out, "assets", "screens")
    os.makedirs(dst, exist_ok=True)
    for n in names:
        f = os.path.join(src, f"{n}.webp")
        if not os.path.exists(f):
            from PIL import Image   # only needed when a new screenshot is added
            png = os.path.join(EXAM_APPS, "store", app, "screenshots", "android", f"{n}.png")
            os.makedirs(src, exist_ok=True)
            Image.open(png).convert("RGB").resize((SHOT_W, SHOT_H), Image.LANCZOS).save(f, "WEBP", quality=78, method=6)
        shutil.copy(f, os.path.join(dst, f"{n}.webp"))


def shot_img(cfg, name, eager=False):
    cap, alt, *size = cfg["screens"][name]
    w, h = size[0] if size else (SHOT_W, SHOT_H)   # emulator shots (1.2.0) are 480x1067
    lazy = "" if eager else ' loading="lazy"'
    return (f'<img class="shot" src="~/assets/screens/{name}.webp" width="{w}" height="{h}"'
            f' alt="{E(cap)}: {E(alt)}"{lazy} decoding="async">')


def shots_strip(cfg, names):
    names = [n for n in names if n in cfg.get("screens", {})]
    if not names:
        return ""
    items = "".join(f"<li>{shot_img(cfg, n)}</li>" for n in names)
    return f'<ul class="shots" aria-label="{E(cfg["name"])} app screens">{items}</ul>'


def appcta(cfg, block):
    kv = {}
    for line in block.strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            kv[k.strip()] = v.strip()
    pos = kv.get("pos", "inline")
    return (f'<aside class="appcta" aria-label="{E(cfg["name"])} app"><img src="~/favicon.svg" width="44" height="44" alt="">'
            f'<div><p><strong>{kv["title"]}</strong></p><p>{kv["text"]}</p>'
            f'<p>{PLAY_BTN.format(pos=pos)}</p><p class="sub">{cfg.get("appcta_sub", "")} · <!--ios--></p></div></aside>')


def expand(app, cfg, path, body, meta):
    """All conversion placeholders -> HTML (before relinking)."""
    is_home = path == ""
    shots = meta.get("shots")
    names = [s.strip() for s in shots.split(",")] if shots else cfg.get("shots", [])
    body = body.replace("<!--cta-->", cfg["cta"])
    body = body.replace("<!--shots-->", "" if is_home else shots_strip(cfg, names))
    body = re.sub(r"<!--appcta\n(.*?)-->", lambda m: appcta(cfg, m.group(1)), body, flags=re.S)
    body = re.sub(r"<!--shots:([^>]*?)-->", lambda m: shots_strip(cfg, [s.strip() for s in m.group(1).split(",")]), body)
    body = re.sub(r"<!--shot:([\w-]+)(:eager)?-->", lambda m: shot_img(cfg, m.group(1), bool(m.group(2))), body)

    def aq(m):
        exam, _, sub = m.group(1).partition("/")
        shown = int(m.group(2) or 10)
        return after_questions(app, cfg, shown, exam, sub or None, m.group(3))
    body = re.sub(r"<!--after-questions:([^\s>]+?)(?: shown=(\d+))?(?: label=([^>]*?))?-->", aq, body)
    shown = {}

    def sample(m):
        ids = [i.strip() for i in m.group(3).split(",")] if m.group(3) else None
        qs = sample_questions(cfg["bundle"], m.group(1).split("|"), int(m.group(2) or 8), ids)
        shown[m.group(1)] = len(qs)
        return render_questions(qs)
    body = re.sub(r"<!--sample:([\w|-]+)(?: n=(\d+))?(?: ids=([\w,-]+))?-->", sample, body)
    body = re.sub(r"<!--after-sample:([\w|-]+)-->", lambda m: after_sample(cfg, shown.get(m.group(1), 8), m.group(1)), body)
    body = body.replace("<!--ios-->", IOS_LINE)
    body = fill_counts(body, cfg.get("bundle"))
    # old hard-coded store links get a referrer too
    plain = re.escape(play(cfg["pkg"]))
    body = re.sub(rf'href="{plain}"', 'href="~play:inline"', body)
    body = re.sub(r'href="~play:([\w-]+)"', lambda m: f'href="{E(play_link(cfg, path, m.group(1)))}"', body)
    return body


def page(app, cfg, path, meta, body, crumbs=None):
    """Wrap a body in the layout. `path` is the URL path below the host ('' or 'x/y/')."""
    host = cfg["host"]
    url = f"https://{host}/{path}"
    pre = rel_prefix(path)
    nav_key = meta.get("nav", "home" if path == "" else "")
    legal = path in ("privacy/", "terms/")
    promote = cfg.get("promote")
    if meta.get("pack"):
        cfg = pack_cfg(cfg, meta["pack"])
        crumbs = crumbs or [("All exams", f"https://{host}/exams/")]
    body = expand(app, cfg, path, body, meta)
    body = body.replace("<!--sources-->", sources_card(app, cfg.get("pack")))
    hero = ""
    m = re.search(r"<!--hero-->(.*?)<!--/hero-->", body, re.S)
    if m:
        hero, body = m.group(1).strip(), body[:m.start()] + body[m.end():]
    body = relink(body, path)
    hero = relink(hero, path)
    body = re.sub(r'\s+style="[^"]*"', "", body)   # CSP: style-src 'self' (no inline styles)
    title = fill_counts(meta["title"], cfg.get("bundle"))
    desc = fill_counts(meta.get("description", ""), cfg.get("bundle"))
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
    notice = f'<p class="notice">{cfg["notice"]}</p>\n'
    footer_date = "" if "Last updated" in body else f" · Last updated {ddmmyyyy(updated)}"
    home = pre
    top = ""
    if hero:
        top = f'<div class="hero">{hero}</div>'
    elif promote:
        pitch = fill_counts(meta.get("pitch") or cfg["pitch"], cfg.get("bundle"))
        top = (f'<div class="pitch"><p>{pitch}</p>'
               f'<a class="btn play" href="{E(play_link(cfg, path, "hero"))}">Get it on Google Play</a></div>')
    sticky = ""
    if promote:
        sticky = (f'<div class="sticky" role="complementary" aria-label="Get {E(cfg["name"])}"><div class="wrap">'
                  f'<img src="{pre}favicon.svg" width="36" height="36" alt="">'
                  f'<span class="s-txt"><strong>{E(cfg["name"])}</strong><small>{meta.get("sticky") or cfg["sticky_sub"]}</small></span>'
                  f'<a class="btn play" href="{E(play_link(cfg, path, "sticky"))}">Get it on Google Play</a></div></div>\n')
    body_class = ' class="home"' if hero else ""
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
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
<body{body_class}>
<a class="skip" href="#main">Skip to content</a>
<header class="site band"><div class="wrap">
<a class="brand" href="{home}">{mark_html(app, cfg)}<span><strong>{E(cfg['name'])}</strong><small>{E(cfg['tagline'])}</small></span></a>
<nav class="main" aria-label="{E(cfg['name'])} pages"><ul>{nav}</ul></nav>
{top}
</div></header>
<main id="main" class="wrap">
{notice}{body.strip()}
</main>
<footer class="site"><div class="wrap">
<p>{cfg['disclaimer']}</p>
<p><a href="{home}">{'Home' if cfg['nav'][0][1] == 'Home' else 'Support'}</a> · <a href="{pre}privacy/">Privacy policy</a> · <a href="{pre}terms/">Terms of use</a> · <a href="mailto:{EMAIL}">{EMAIL}</a></p>
<p>This site has no cookies, analytics or trackers. © 2026 Kodfu Bilisim{footer_date}</p>
</div></footer>
{sticky}</body>
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


def topic_pitch(cfg, bundle, exam_id, topic_id, short):
    t = facts(bundle)["exams"][exam_id]["topics"][topic_id]
    free = "all free" if t["free"] == t["n"] else f"{t['free']} free, the rest with Pro"
    return f"The {cfg['name']} app has all {t['n']} {E(short)} questions in this topic, with explanations: {free}."


def more_exams_links():
    """Links from /practice/ to the per-exam pages of the Sparkwise 1.2.0 packs."""
    F = facts("sparkwise")
    items = []
    for key, p in PACKS.items():
        k = pack_key(p)
        names = " and ".join(F["exams"][e]["title"] for e in p["exams"]) if len(p["exams"]) < 3 else \
            "2391-52, 2391-50 and 2391-51 inspection and testing"
        items.append(f'<li><a href="~/{p["page"]}">{E(p["label"][0].upper() + p["label"][1:])}: free exam questions'
                     f'<span>{names} · {fact("sparkwise", "count", k):,} questions in the app · {p["price"]} once</span></a></li>')
    return '<ul class="links">' + "".join(items) + "</ul>"


def sparkwise_practice(cfg, out):
    files = load_bundle("sparkwise")
    PER = 10
    exams = [("18th-edition", "bs7671", files["manifest.bs7671.json"], "18th Edition", "Where to look"),
             ("ecs-hse", "ecs-hse", files["manifest.ecs-hse.json"], "ECS HS&E", "Source")]
    total = 0
    for slug, exam_id, ex, short, label in exams:
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
<!--after-questions:{exam_id}/{t['id']} shown={len(qs)}-->
{notes_html(tf.get('notes'))}
<h2 id="more">More {E(short)} topics</h2>
<ul class="links"><li><a href="~/practice/{slug}/{prv['id']}/">Previous: {E(prv['title'])}<span>{E(prv['summary'])}</span></a></li>
<li><a href="~/practice/{slug}/{nxt['id']}/">Next: {E(nxt['title'])}<span>{E(nxt['summary'])}</span></a></li>
<li><a href="~/{'18th-edition-exam' if slug == '18th-edition' else 'ecs-hse-assessment'}/">{'18th Edition exam guide' if slug == '18th-edition' else 'ECS HS&amp;E assessment guide'}<span>Format, rules, booking and how to prepare</span></a></li></ul>
<!--cta-->"""
            meta = {"title": short_title(t['title'], short, "Sparkwise"),
                    "description": f"Free {short} practice questions on {t['title'].lower()}, with answers and explanations. "
                                   + ("BS 7671:2018+A4:2026, C&G 2382-26." if slug == "18th-edition" else "ECS Health, Safety & Environmental assessment."),
                    "nav": "practice", "updated": files["manifest.json"].get("updated", TODAY),
                    "pitch": topic_pitch(cfg, "sparkwise", exam_id, t["id"], short),
                    "shots": ("05-worked,06-max-zs,04-question" if t["id"] == "design-calcs" else
                              "07-a4,04-question,03-mock" if t["id"] == "amendment-4" else
                              "02-exams,08-results" if slug == "ecs-hse" else "")}
            if not meta["shots"]:
                del meta["shots"]
            meta["description"] = meta["description"][:158]
            write(out, path, page("sparkwise", cfg, path, meta, body, [("Free practice", f"https://{cfg['host']}/practice/")]))
    bs, ecs = files["manifest.bs7671.json"], files["manifest.ecs-hse.json"]
    body = f"""<h1>Free 18th Edition and ECS HS&amp;E practice questions</h1>
<p class="lead">{total} free practice questions by topic for the 18th Edition (City &amp; Guilds 2382-26, BS 7671:2018+A4:2026) and the ECS Health, Safety and Environmental assessment, each with the answer and an explanation.</p>
<p class="muted">Free, with no sign-up and nothing saved. Every question is original and comes from the Sparkwise app, which has all {{{{count:bs7671+ecs-hse}}}}; only questions we have checked are published. No app or website can show you the real exam questions.</p>
<div class="toc"><a href="#18th-edition">18th Edition topics</a> · <a href="#ecs-hse">ECS HS&amp;E topics</a> · <a href="#more-exams">2391, AM2, EWA, PAT, EV, ESU, solar PV</a></div>
<h2 id="18th-edition">18th Edition practice (BS 7671:2018+A4:2026)</h2>
<p>The City &amp; Guilds 2382-26 exam tests whether you can find and apply the requirements of the current Wiring Regulations. It is an online multiple-choice exam of {bs['mock']['questionCount']} questions in {bs['mock']['minutes']} minutes, and it is open book, so practise with your own copy of BS 7671 to hand. Each answer points to a regulation, table or appendix to look up. Read the <a href="~/18th-edition-exam/">18th Edition exam guide</a> and <a href="~/amendment-4/">what changed in Amendment 4</a>.</p>
{topic_links('practice/18th-edition/', bs, files, PER)}
<p class="muted">Sitting the 2391, AM2, EWA entry test, PAT, EV charging, the ECS Electrical Safety Unit or solar PV? <a href="#more-exams">Jump to those exams</a>.</p>
<!--appcta
title: All {{{{count:bs7671}}}} 18th Edition questions, and full mock exams, in the app
text: Practise every Part of BS 7671 with explanations that point to the regulation to look up, worked solutions for calculations and timed 60-question mock exams of 2 hours. {{{{free:bs7671}}}} of the 18th Edition questions are free in the app.
pos: inline-18th
-->
<h2 id="ecs-hse">ECS HS&amp;E practice</h2>
<p>The ECS Health, Safety and Environmental assessment is the test most electrotechnical workers pass to get or renew an ECS card. It has {ecs['mock']['questionCount']} multiple-choice questions in {ecs['mock']['minutes']} minutes and is closed book. The CITB HS&amp;E test used for CSCS cards does not count for ECS. Read the <a href="~/ecs-hse-assessment/">ECS HS&amp;E assessment guide</a>.</p>
{topic_links('practice/ecs-hse/', ecs, files, PER)}
<h2 id="more-exams">Free questions for the other exams in Sparkwise</h2>
<p>Each page has 8 to 10 free questions with answers and explanations, the real exam format and what it covers.</p>
{more_exams_links()}
<!--cta-->
<!--sources-->"""
    meta = {"title": "Free 18th Edition, ECS, 2391 & AM2 Practice Questions | Sparkwise",
            "description": f"{total} free practice questions by topic for the 18th Edition (C&G 2382-26, BS 7671 A4:2026) and the ECS HS&E assessment, with answers and explanations.",
            "nav": "practice", "updated": files["manifest.json"].get("updated", TODAY),
            "pitch": "Try free questions here, then practise all {{count:bs7671+ecs-hse}} in the Sparkwise app, with timed mock exams in the real format."}
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
<!--after-questions:operatives/{t['id']} shown={len(qs)}-->
{notes_html(tf.get('notes'))}
<h2 id="more">More topics</h2>
<ul class="links"><li><a href="~/practice/{prv['id']}/">Previous: {E(prv['title'])}<span>{E(prv['summary'])}</span></a></li>
<li><a href="~/practice/{nxt['id']}/">Next: {E(nxt['title'])}<span>{E(nxt['summary'])}</span></a></li>
<li><a href="~/guide/">HS&amp;E test guide<span>Format, pass mark, booking, ID and how to prepare</span></a></li></ul>
<!--cta-->"""
        meta = {"title": short_title(t['title'], "HS&E Test", "HiVis"),
                "description": f"Free CITB HS&E test practice questions on {t['title'].lower()}, with answers and explanations. Original questions, no sign-up."[:158],
                "nav": "practice", "pitch": topic_pitch(cfg, "hivis", "operatives", t["id"], "Operatives")}
        write(out, path, page("hivis", cfg, path, meta, body, [("Free practice", f"https://{cfg['host']}/practice/")]))
    m = ex["mock"]
    body = f"""<h1>Free CITB HS&amp;E test practice questions</h1>
<p class="lead">{total} free practice questions for the CITB Health, Safety and Environment Operatives test, by topic, each with the answer and an explanation.</p>
<p class="muted">Free, with no sign-up and nothing saved. Every question is original and comes from the HiVis app, which has {{{{count:operatives}}}} Operatives questions and {{{{count:all}}}} across all seven tests. No app or website can show you the real test questions.</p>
<p>{E(ex['description'])} The real test has {m['questionCount']} questions in {m['minutes']} minutes. Read the <a href="~/guide/">HS&amp;E test guide</a> for the format, booking and what to bring.</p>
<!--appcta
title: Practise all {{{{count:operatives}}}} Operatives questions in HiVis
text: Every topic, simple explanations with read aloud, and full 50-question mock tests timed at 45 minutes with 45 to pass. {{{{free:operatives}}}} of the Operatives questions are free in the app.
pos: inline-top
-->
<h2 id="topics">Topics</h2>
{topic_links('practice/', ex, files, PER)}
<!--cta-->
<!--sources-->"""
    meta = {"title": "Free CITB HS&E Test Practice Questions 2026 | HiVis",
            "description": f"{total} free CITB HS&E Operatives test practice questions by topic, with answers and explanations. Original questions, no sign-up, nothing saved.",
            "nav": "practice",
            "pitch": "Try free questions here, then practise all {{count:operatives}} Operatives questions in the HiVis app, with timed 50-question mocks."}
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
    CSS_VERSION = hashlib.sha1(css.encode()).hexdigest()[:8]
    # remove previously generated pages (keeps README.md)
    for f in glob.glob(os.path.join(out, "**", "index.html"), recursive=True):
        os.remove(f)
    for d in sorted(glob.glob(os.path.join(out, "**", ""), recursive=True), reverse=True):
        if d.rstrip("/") != out and not os.listdir(d):
            os.rmdir(d)
    start = len(WRITTEN)
    ensure_screens(app, cfg, out)
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
    nf = page(app, cfg, "404.html", {"title": f"Page not found | {cfg['name']}", "description": "", "nav": "-"},
              '<h1>Page not found</h1><p class="lead">That page does not exist or has moved.</p><p><a class="btn" href="~/">Go to the home page</a></p>')
    nf = nf.replace('href="./', 'href="/').replace('src="./', 'src="/')
    nf = re.sub(r'<link rel="canonical"[^>]*>\n', "", nf)
    nf = re.sub(r'<script type="application/ld\+json">.*?</script>\n?', "", nf)
    nf = nf.replace("<head>", '<head>\n<meta name="robots" content="noindex">', 1)
    open(os.path.join(out, "404.html"), "w").write(nf)
    pages = [p for p, _ in WRITTEN[start:]]
    urls = "\n".join(f"  <url><loc>https://{cfg['host']}/{p}</loc><lastmod>{TODAY}</lastmod></url>" for p in sorted(pages, key=lambda p: (p.count('/'), p)))
    open(os.path.join(out, "sitemap.xml"), "w").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n')
    open(os.path.join(out, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: https://{cfg['host']}/sitemap.xml\n")
    # Google Search Console HTML-file verification (account info.kodfu@gmail.com): the repo-root
    # google*.html files are copied to every host's root so URL-prefix properties verify.
    for name in os.listdir(ROOT):
        if name.startswith("google") and name.endswith(".html"):
            shutil.copy(os.path.join(ROOT, name), os.path.join(out, name))
    print(f"{app}: {len(pages)} pages -> https://{cfg['host']}/" + (f" ({extra} practice questions)" if extra else ""))


if __name__ == "__main__":
    apps = sys.argv[1:] or list(SITES)
    for a in apps:
        build(a)
