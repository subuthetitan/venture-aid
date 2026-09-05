# PS 26092 — MVP Build Plan (Internal Round)

**Supersedes:** `TEAM_SPLIT.md` §1–3
**Goal:** a clickable product that shows judges how the whole thing works. Not everything needs to run.
**Team:** 6, three pairs.

---

## The pairing logic

The six features are not six projects. They pair on shared data and shared code:

| Pair | PS-mandated feature | Our differentiator | What they share |
|---|---|---|---|
| **A** | Smart Scheme Recommender | Scheme Truth Layer | Same rule store, same eligibility engine |
| **B** | Financial Calculator | Sanction-Ready | The calculator *is* the finance module inside the report |
| **C** | Geospatial Partner Locator + Router | Transparency Ledger | Same map component, same district geography |

Each pair builds the PS-named feature **first** — that's what gets scored — then folds the differentiator into it rather than bolting on a separate tab.

That last point matters. The Truth Layer is not a fourth screen; it's the reason the Recommender can be trusted. The Ledger is not a separate dashboard; it's a layer on the same map. Judges see three features that go deeper than expected, not six half-finished ones.

---

## Pair A — Recommender + Truth Layer

### Smart Scheme Recommender (build first)
Input form: income, caste, state, district, activity, amount needed → ranked list of schemes with per-condition match/fail reasons.

- `json-logic-py` evaluated **leaf by leaf**, not as one nested expression
- Four-state verdict: `ELIGIBLE` / `NOT_ELIGIBLE` / `CONTRADICTORY_SOURCES` / `INSUFFICIENT_DATA`
- Every condition renders a provenance chip: *source · authority · fetched on*
- `INSUFFICIENT_DATA` is used honestly — age criteria and promoter contribution aren't published on any fetchable NSFDC page, so say "not published" instead of inventing a threshold

### Scheme Truth Layer (fold in)
- `source_snapshot` + `rule_version` tables, **hand-seeded**: 4–5 schemes, ~8 fields each, every row with a real URL and a real fetch date
- `live_contradiction` SQL view (~15 lines)
- The reveal: enter family income **₹4.2 lakh** → the recommender returns `CONTRADICTORY_SOURCES`, showing ₹5,00,000 from NSFDC About Us and ₹3,00,000 from NSFDC How-to-Apply and socialjustice.gov.in/schemes/34, both live, both dated

| Real | Fixture | Cut for MVP |
|---|---|---|
| Eligibility engine, trace, verdicts, contradiction view | Rule rows entered by hand | Scheduled crawler |
| Provenance display | Snapshotted page HTML committed | LLM extraction pipeline |
| | | Change detection / diffing |

Show the schema and say plainly: *designed to re-crawl and version; seeded manually for the prototype.* A labelled seed reads as scoping. An unlabelled one reads as a lie when someone asks.

---

## Pair B — Financial Calculator + Sanction-Ready

### Financial Calculator (build first)
Fully real, no external dependency, no AI. This is your guaranteed-working feature.

- Inputs: project cost, scheme, own contribution
- Outputs: sanctionable amount, EMI, moratorium handling, total interest, full repayment schedule table, **subsidy-late scenario**
- Real rates from the report: Suvidha 8% to beneficiary / 5yr / 6mo moratorium · Micro Credit 6.5% / 3yr / 3mo · Mahila Samriddhi 6% / 3yr / 3mo
- Pure Python, `decimal`, unit-tested

The subsidy-late scenario is the differentiator hiding inside a boring feature. Nobody else models "what your repayment looks like if the subsidy arrives three years late," and you have a documented case of exactly that.

### Sanction-Ready (fold in)
Same finance module, now embedded in a document flow.

- Voice in → activity classification → cost template → costed project report PDF
- Bhashini primary, Sarvam Saaras/Bulbul fallback, 6s timeout
- **Always keep a "type it instead" path visible.** ASR failing live must be a shrug, not a dead demo
- Cost library: **8–10 activities**, not 50 — tailoring, dairy, kirana, flour mill, beauty parlour, tea stall, photocopy shop, goat rearing
- Template from a **published** PMEGP or Mudra DPR format, and say that's why you chose it
- WeasyPrint + Jinja2, Noto fonts. Run the Devanagari conjunct test on day one

| Real | Fixture | Cut for MVP |
|---|---|---|
| Finance engine + tests | 8–10 cost templates | Document OCR |
| Voice chain, both providers | One report template | Pre-flight validation |
| PDF generation | Cached ASR response as offline fallback | Multi-format output |

**The line to say on stage:** no number in this document was produced by a language model. Your unit tests are what make that claim safe.

---

## Pair C — Locator + Router + Ledger

### Geospatial Partner Locator & Router (build first)
- MapLibre base, DataMeet district GeoJSON, mapshaper-simplified to ~2 MB, committed static
- SCA offices + empanelled bank branches as points; geocode once at seed time, cache results
- Click district → list of channels with contact details
- **Router:** Mappls Directions from the user's location to the selected office. This is the one live external call in the MVP and it's justified — routing is explicitly in the PS

Mappls comes back into the stack here (I'd dropped it earlier), because the PS names routing. Keep MapLibre as the renderer so a rate limit or dead wifi degrades the route, not the whole map.

### Transparency Ledger (fold in)
- `application_milestone` table, ~200 **synthetic** records across 12 districts
- District choropleth: median days at stage, pendency
- **"Prototype data — synthetic" printed on the chart itself**, not in a footnote
- k-anonymity (<5 suppressed) stated as a design rule rather than implemented

### The reachability overlay — the argument-making layer
A third toggle on the same map: districts coloured by whether a live channel exists, with **Telangana and Ladakh dark**. "A qualified person here has nowhere to apply." One map, three layers, one strong claim.

| Real | Fixture | Cut for MVP |
|---|---|---|
| Map, layers, district interaction | SCA/branch point data seeded | PWA offline queue |
| Mappls routing | Ledger milestones synthetic | Real milestone capture |
| Reachability layer | | Live pendency |

---

## The app shell — due before hour 0

Pair C ships this in Phase 0, and it is the single most important MVP artifact.

A React shell with **six routes already navigable**, each rendering a labelled placeholder. From hour zero you have a clickable product that communicates the whole idea, and each pair fills in their two screens. If a pair falls behind, the screen still exists and still tells the story.

Also Phase 0 from Pair C: shadcn theme, `react-i18next` scaffolding, `docker-compose.yml`, simplified GeoJSON, and all API keys registered (ULCA/Bhashini, Sarvam, Mappls).

---

## Second hats

| Role | Person from | Job |
|---|---|---|
| Integrator | Pair C | Owns `main`, runs the full stack every 4 hours |
| Pitch owner | Pair A | Deck, demo script, timing, the "what we cannot fix" slide |
| Evidence keeper | Pair B | Every deck claim traceable to `SOURCE_DATABASE.csv`; enforces the four "never say these" from report §16 |

---

## Contracts frozen before build starts

| Contract | Owner | Consumers |
|---|---|---|
| `seed_schemes.json` — 5 schemes, correct, hand-written | A | B, C |
| `GET /recommend` response shape | A | C |
| `POST /calculate` → repayment schema | B | A |
| `district_codes.json` (LGD codes) | C | A, B |
| App shell + design tokens + i18n keys | C | A, B |
| `docker-compose.yml` with empty services | C | A, B |

If a pair needs something another pair hasn't built, they stub it and move on. Nobody waits, and nobody builds in another pair's area.

---

## Build timeline

| Hours | Pair A | Pair B | Pair C |
|---|---|---|---|
| 0–6 | Schema + seed rows loaded | Finance engine + unit tests | Map renders, district click works |
| 6–14 | Recommender working end to end | Calculator screen complete | Locator + router working |
| 14–20 | Contradiction reveal wired in | Voice → report → PDF | Ledger + reachability layers |
| **20** | **Integration freeze — everyone off stubs, onto real endpoints** | | |
| 20–28 | Polish, empty states, error handling | | |
| 28–32 | Bugs only. No new features. | | |
| 32–36 | Three full rehearsals, one with wifi off | | |

---

## Demo script (8 minutes)

1. **Recommender** — enter a normal applicant, get matched schemes with sources shown. *(Pair A, 90s)*
2. **The reveal** — change income to ₹4.2 lakh. Contradiction fires. Hand a judge a phone and let them open both URLs. *(Pair A, 60s)*
3. **Calculator** — pick Suvidha, see the EMI. Then toggle "subsidy delayed 3 years" and watch the picture change. *(Pair B, 90s)*
4. **Sanction-Ready** — speak a business idea in Kannada, PDF comes out. *(Pair B, 120s)*
5. **Locator** — find the district office, route to it. Then flip the reachability layer: Telangana and Ladakh go dark. *(Pair C, 90s)*
6. **Ledger** — district pendency, clearly labelled as synthetic, with the point that no government scheme publishes this at all. *(Pair C, 60s)*
7. **What we cannot fix** — collateral, capital, discrimination. *(Pitch owner, 30s)*

Each of the first three beats is the same move: deliver the PS ask, then show the thing underneath it that nobody else found.

---

## The honest line about field research

You have not spoken to applicants. Say so before a judge asks:

> Everything in our journey reconstruction is labelled hypothesis, because it comes from documents rather than interviews. The first thing we'd do with more time is five applicants — including two who were rejected — and two agency clerks.

Naming that gap costs you nothing and buys more credibility than any feature in the demo.
