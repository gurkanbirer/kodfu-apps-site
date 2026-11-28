# FareBack: site lines waiting for app 1.1.0

The FareBack site describes only what the version on Google Play does today (the live-data listing,
`~/Code/fareback/store/listing/en-GB/android/full_description.txt`, owner rule "every feature we sell must visibly
work", 28/11/2026). The app agent is building the features below for 1.1.0. When 1.1.0 is live on Google Play **and**
its listing names the feature, add these lines (then delete them here). Written 28/11/2026.

| Feature (1.1.0) | Where on the site | Line to add |
| --- | --- | --- |
| Delay evidence export | `/rejected-claim/` "Evidence that wins", `/rail-ombudsman/` app box, home "How FareBack works" | "FareBack exports a dated evidence report for each journey: the scheduled and actual times from National Rail data, when they were checked, your ticket and the claim you sent." |
| Claim timeline | train company pages "How FareBack helps", `/rejected-claim/` | "Every claim keeps a dated timeline: when you claimed, the reference, the answer and every follow-up." |
| Challenge flow for rejected or underpaid claims | `/rejected-claim/` (new app box above the template letter), each train company page "Why claims get rejected", `/rail-ombudsman/` | "Claim rejected or underpaid? FareBack walks you through the challenge: a reply to the train company with your evidence, reminders at 20 and 40 working days, then the Rail Ombudsman, with every date kept. You still send each step yourself." |
| Multi-leg journeys and split tickets | `/split-tickets/`, `/missed-connections/` app boxes | "Save a journey with a change or on split tickets and FareBack measures the delay at your final destination, with every ticket in the Claim Pack." |
| Reliability report | `/commuters/`, `/season-tickets/` | "Your commute's reliability report: how often your trains were late, what you claimed and what you were paid, month by month." |
| Cancelled-train refunds (if shipped) | `/cancelled-trains/` | "If your train is cancelled and you don't travel, FareBack reminds you to ask the retailer for a fee-free refund within 28 days." |

Also when 1.1.0 is live: update the closing card (`cta` for `fareback` in `tools/build.py`), the Pro plan list on the home
page and the FAQ answer "How much does FareBack cost?" if the Pro feature list changes, and the screenshots
(`src/fareback/screens/`) when the store screenshots change.
