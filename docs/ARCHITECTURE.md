# PS 26092 — System Architecture

**Project:** Application-readiness layer for NSFDC / state SC-corporation credit
**Stage:** pre-build architecture decision record
**Modules in scope:** I01 Scheme Truth Layer · I04 Sanction-Ready · I14 Transparency Ledger · thin I07 Operator Mode
**Companion evidence:** `FINAL_PROBLEM_DISCOVERY_REPORT.md`, `PAIN_POINT_DATABASE.csv`, `IDEA_SCORECARD.csv`

Every deviation from the previously proposed stack is marked **`CHANGE`** with the reason attached. Everything not marked was kept as proposed.

---

## 1. What we are building, and the one scope change

Three modules, one backend, one database.

| Module | Source idea | Score | Role in the product |
|---|---|---|---|
| Scheme Truth Layer | I01 | 101/120 | Versioned, provenance-stamped scheme rules. Foundation — everything else is wrong if this is wrong. |
| Sanction-Ready | I04 | 102/120 | Voice-in, costed project report + honest repayment picture out. Headline capability. |
| Operator Mode | I07 | 98/120 | Thin second screen for CSC/NGO/SCA staff. |
| Transparency Ledger | I14 | 91/120 | District-level pendency and outcome stats aggregated from logged milestones. |

> ### `CHANGE 1` — Added a thin Operator Mode (I07), which was not in the original three
>
> **Why:** the Ledger aggregates application milestones. The only realistic source of milestone *volume* is someone processing twenty applicants a week, not an applicant logging their own file once. Without an operator surface, I14 is a dashboard with three demo rows and a cold-start apology.
>
> `FINAL_PROBLEM_DISCOVERY_REPORT.md` §14 already specifies I07 as "the same engine, but with a screen designed for someone processing twenty applicants a week." Building it is cheaper than building a credible Ledger without it. It also recovers the highest social-impact idea in the scorecard (10/10) and gives the three modules a single causal story:
>
> `Operator uses Sanction-Ready → milestones logged as a byproduct → Ledger aggregates → district pendency that exists nowhere else`

> ### `CHANGE 2` — Reframe the Ledger from adversarial to complementary
>
> **Why:** "publish what the government does not" is a losing frame in front of judges who *are* the ministry. NSFDC tender **GEM/2026/B/7981809** (2 Sept 2026) proves they already know they cannot see their own pipeline.
>
> New framing: the tender fixes visibility into files that *exist*; the Ledger measures the denominator neither side has — people who started and never became a file. State the distinction explicitly so a judge does not think you are re-pitching their live procurement.
>
> Also, pre-empt this in one line during the pitch: **this is an append-only Postgres table, not a blockchain.** The word "Ledger" invites the question and you do not want to spend 90 seconds on it.

---

## 2. Review of the proposed stack

| Proposed | Verdict | Action |
|---|---|---|
| React + Vite + Tailwind + shadcn/ui | Keep | Add TanStack Query, react-i18next, MapLibre |
| FastAPI / Python | Keep | Add APScheduler worker process |
| PostgreSQL + SQLAlchemy | Keep | Add Alembic; append-only versioning schema (§4) |
| JSONLogic | Keep | Wrap in a trace evaluator; add tri-state verdict (§6) |
| Sarvam 105B (LLM) | Keep | Batch-only for extraction; hosted API, not self-hosted |
| Sarvam Saaras + Bulbul (voice) | **Change** | Bhashini primary, Sarvam fallback (`CHANGE 3`) |
| Sarvam Translate | Keep | Fallback behind Bhashini NMT |
| Mappls | Keep | Decouple rendering from the SDK (`CHANGE 5`) |
| ReportLab | **Change** | WeasyPrint (`CHANGE 4`) |
| Vercel + Render/Railway | **Change** | Docker Compose primary, cloud as mirror (`CHANGE 6`) |
| — | **Missing** | Snapshot store, scheduler, scraping layer, offline path |

---

## 3. System shape

```
                          ┌──────────────────────────────────────┐
   React (Vite) SPA       │  FastAPI (uvicorn)                    │
   ├ Applicant mode  ─────┤  /schemes  /eligibility  /readiness    │
   ├ Operator mode        │  /voice    /report       /ledger       │
   └ Public ledger view   │  /map                                  │
                          └───────┬──────────────┬────────────────┘
                                  │              │
                    ┌─────────────┴───┐   ┌──────┴──────────────┐
                    │ Eligibility     │   │ Finance engine       │
                    │ (JSONLogic +    │   │ (pure Python, no LLM)│
                    │  trace)         │   └──────┬──────────────┘
                    └─────────────┬───┘          │
                                  │              │  WeasyPrint
                          ┌───────┴──────────────┴──────┐
                          │  PostgreSQL                  │
                          │  source_snapshot (raw bytes) │
                          │  rule_version (append-only)  │
                          │  cost_template               │
                          │  application_milestone       │
                          └───────▲──────────────────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │  Worker (APScheduler) — runs OUTSIDE the request   │
        │  crawl → snapshot → LLM extract → diff → flag      │
        └───────────────────────────────────────────────────┘

  External: Bhashini (ULCA/Dhruva) → Sarvam (fallback) │ Mappls (geocode) │ Sarvam 105B (batch extract)
```

Three processes only: `api`, `worker`, `web`. No microservices, no queue broker.

---

## 4. Module 1 — Scheme Truth Layer

### 4.1 Crawl and snapshot

```
httpx (async)  →  selectolax / BeautifulSoup   for static HTML (nsfdc.nic.in, socialjustice.gov.in)
Playwright     →  ONLY for myScheme (JS SPA, unreadable by fetch — see report §8.2)
pdfplumber     →  for scheme PDFs where they resolve (many 404)
```

> ### `MISSING FROM PROPOSED STACK` — Snapshot store
>
> Every fetch writes **raw bytes + SHA-256 + timestamp** to `source_snapshot` before anything parses it. Two reasons:
>
> 1. **Provenance means showing the bytes you actually read.** A screenshot of the contradiction is weak; a stored, hashed, timestamped response body is not.
> 2. **Demo survival.** `nsfdc.nic.in` returning 504 mid-pitch (the report already documents persistent 504s on `cag.gov.in`) must be a story you tell, not a failure you suffer. Snapshot every relevant page now, commit the fixtures, and keep a live "re-crawl" button for theatre with the cache behind it.

### 4.2 Extraction — batch, never in the request path

> ### `CHANGE` — LLM extraction runs offline and its output is committed
>
> **Why:** you have roughly 15 schemes. Extraction is a pipeline you run a few dozen times, not a per-request call. Running it in the request path buys you latency, non-determinism and a live dependency on an API, for no benefit. Run it in the worker, review the output by hand, mark rows `verified_by_human = true`, commit.

Sarvam 105B with structured output into a Pydantic `SchemeRuleSet`. Its 128K context window means a full scheme page plus the Ministry mirror fits in one prompt, which is what makes cross-source comparison cheap.

> ### `EXPLICITLY NOT` — No vector database, no RAG
>
> Fifteen schemes. A `SELECT` covers it. A vector store here is complexity you will defend in Q&A and never use.

### 4.3 Schema — append-only, never UPDATE

```sql
CREATE TABLE source_snapshot (
    id            BIGSERIAL PRIMARY KEY,
    url           TEXT NOT NULL,
    fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    http_status   INT,
    content_type  TEXT,
    content_hash  TEXT NOT NULL,        -- sha256 of raw_body
    raw_body      BYTEA NOT NULL
);

CREATE TABLE rule_version (
    id                     BIGSERIAL PRIMARY KEY,
    scheme_id              TEXT NOT NULL REFERENCES scheme(id),
    field                  TEXT NOT NULL,      -- 'family_income_ceiling'
    value                  JSONB NOT NULL,     -- {"amount": 500000, "currency": "INR"}
    snapshot_id            BIGINT NOT NULL REFERENCES source_snapshot(id),
    source_url             TEXT NOT NULL,
    source_authority       TEXT NOT NULL,      -- 'NSFDC' | 'MoSJE' | 'State:TS'
    extracted_by           TEXT NOT NULL,      -- 'llm:sarvam-105b' | 'human'
    extraction_confidence  NUMERIC,
    effective_from         DATE,               -- 2026-01-07 for the ₹5L revision
    observed_at            TIMESTAMPTZ NOT NULL,
    superseded_at          TIMESTAMPTZ,        -- NULL = currently live
    verified_by_human      BOOLEAN NOT NULL DEFAULT FALSE
);
```

**The one subtlety that makes contradiction detection work:**

- Supersession is scoped to `(scheme_id, field, source_url)`. When the *same page* changes its value, the old row gets `superseded_at`.
- A contradiction is *across* `source_url`. Two different official pages reporting different values both stay live. That is the ₹3L / ₹5L case, and it is a normal state of the data, not an error.

```sql
CREATE VIEW live_contradiction AS
SELECT scheme_id,
       field,
       COUNT(DISTINCT value::text) AS distinct_values,
       jsonb_agg(jsonb_build_object(
           'value', value, 'source', source_url,
           'authority', source_authority, 'observed_at', observed_at
       )) AS positions
FROM rule_version
WHERE superseded_at IS NULL
GROUP BY scheme_id, field
HAVING COUNT(DISTINCT value::text) > 1;
```

That view is the demo. It is a real, live, checkable-on-a-judge's-phone contradiction, and it falls out of a `GROUP BY`.

---

## 5. Module 2 — Sanction-Ready

### 5.1 Voice

> ### `CHANGE 3` — Bhashini primary, Sarvam fallback (proposed stack was Sarvam-only)
>
> **Why:** pain point **P3** in your own database is that Bhashini — mature, government-owned, 22 languages — "sits unused next to the exact use case it was built for." That gap *is* your novelty claim. A Sarvam-only build discards the differentiator your research spent a stream establishing, and hands a judge the question "so why didn't you use the government's own stack?"
>
> Equally, Bhashini alone is a demo risk: ULCA registration friction, and Dhruva latency you do not control.
>
> **Resolution:** both, behind one interface, with the fallback disclosed on stage. "Bhashini-first, with a commercial fallback so a field worker is never blocked" reads as engineering judgement, not hedging.

```python
class SpeechProvider(Protocol):
    async def asr(self, audio: bytes, lang: str) -> Transcript: ...
    async def tts(self, text: str, lang: str) -> bytes: ...

# Chain: Bhashini (6s timeout) → Sarvam → cached fixture (offline demo)
```

Correct model names, since these matter and were partly conflated in the proposal:

| Task | Primary | Fallback |
|---|---|---|
| ASR | Bhashini ASR via ULCA pipeline → `dhruva-api.bhashini.gov.in` | Sarvam **Saaras v3** (`mode="transcribe"`, 22 languages) |
| Translation | Bhashini NMT | Sarvam Translate |
| TTS | Bhashini TTS | Sarvam **Bulbul v3** |
| Reasoning / extraction | Sarvam **105B** (text LLM — *not* a voice model) | — |

Record which provider served each request and surface it in the UI. "Transcribed by Bhashini" is a claim you can then defend.

**Register for ULCA credentials this week.** Auth is `userID` + `ulcaApiKey` → `getModelsPipeline` → inference endpoint. Credential friction on day one is the standard way this integration dies.

### 5.2 The finance engine — no LLM-generated numbers

> ### `HARD RULE` — the model fills narrative fields; Python computes every number
>
> `ProjectReport` is a Pydantic model. The LLM populates `business_description`, `market_rationale`, `activity_class`. Pure functions compute `capex`, `working_capital`, `emi`, `total_interest`, `break_even_months`, `subsidy_delay_scenario`. Each numeric field carries `provenance: "computed"`.
>
> **Why:** the report (§14, I04) already states "what does not need AI: the cost library, the EMI maths, the band-fitting rules." More practically, this problem statement attracts judges with finance backgrounds. Being able to say **"no figure in this document was produced by a language model"** turns your biggest vulnerability into a credibility line.

Scheme-band fitting (₹1.25L Micro Credit / ₹9L Suvidha / ₹9–45L Utkarsh) is deterministic rules over the computed project cost. Note in the UI that Utkarsh terms are unverified — the report flags NSFDC's own pages as inconsistent on whether ₹10–50L is loan amount or project cost.

### 5.3 PDF rendering

> ### `CHANGE 4` — WeasyPrint instead of ReportLab
>
> **Why:** the output is a project report in Kannada, Marathi, Hindi or Tamil. Indic scripts need complex text shaping — conjunct formation, matra reordering. ReportLab's open-source layout engine does not do HarfBuzz shaping; you get broken conjuncts, or you spend the hackathon hand-registering TTFs and fighting glyph positioning. WeasyPrint renders through Pango/HarfBuzz and handles this.
>
> You also get Jinja2 + CSS as your template language, which means a designer-editable report format and an HTML preview in the browser that matches the PDF exactly.
>
> **Verify this yourself on day zero, in 20 minutes:** render the string `कृषि प्रसंस्करण इकाई` through both and look at the conjuncts. Do not take my word for it, and do not discover it on day two.
>
> Cost: WeasyPrint needs system libraries (Pango, Cairo, GDK-PixBuf). This is fine in Docker and is one reason for `CHANGE 6`.

Bundle Noto Sans Devanagari / Kannada / Tamil / Bengali as static assets. Do not rely on host fonts.

Build the template from a **real accepted format** obtained from an SCA or bank branch (report §16, verification item 2), and label the output *first draft for human review*, not an approval.

---

## 6. Eligibility engine — JSONLogic with a trace

JSONLogic is kept, but plain evaluation returns a boolean, and a boolean cannot express what differentiates you from myScheme.

> ### `CHANGE` — evaluate atomic conditions individually; return a trace and a tri-state verdict
>
> **Why:** your claimed differentiator is *provenance and counterfactuals* — "eligible under this clause of this document fetched on this date, and here is what would flip it." You cannot reconstruct that from one nested expression's output. Evaluate each leaf separately and keep the result.

```python
@dataclass
class Condition:
    id: str                  # 'income_ceiling'
    logic: dict              # {"<=": [{"var": "family_income"}, 500000]}
    rule_version_id: int     # → source_url, observed_at, authority
    human_text: dict         # {"hi": "...", "kn": "...", "en": "..."}

class Verdict(Enum):
    ELIGIBLE
    NOT_ELIGIBLE
    CONTRADICTORY_SOURCES     # ← first-class, not an exception
    INSUFFICIENT_DATA         # ← rule not published anywhere we could fetch
```

`CONTRADICTORY_SOURCES` is the point. An applicant with family income ₹4.2 lakh gets **both** values, **both** source URLs, **both** observation dates, and a plain-language line saying the government currently disagrees with itself. Never silently pick one.

`INSUFFICIENT_DATA` is equally important and equally honest: age criteria, promoter contribution and women/divyangjan concessions were not stated on any fetchable NSFDC page (report §2.1). Say "not published" rather than inventing a threshold.

**Frontend reuse:** the same JSONLogic fragments run in `json-logic-js` in the browser for instant field-level feedback, with the server staying authoritative. One rule definition, two execution sites.

---

## 7. Modules 3 & 4 — Operator Mode and Ledger

### 7.1 Operator console (thin)

Queue view → fast intake → eligibility triage → document checklist → Sanction-Ready as a tool inside it → batch status.

> ### `MISSING FROM PROPOSED STACK` — offline-first for the operator
>
> Field connectivity is the design constraint. Operator mode is a PWA: IndexedDB write queue, background sync on reconnect, explicit "3 unsynced" indicator. Applicant mode can stay online-only.

### 7.2 Ledger

```sql
CREATE TABLE application_milestone (
    id             BIGSERIAL PRIMARY KEY,
    application_ref TEXT NOT NULL,     -- salted hash, no PII
    district_code   TEXT NOT NULL,     -- LGD code
    scheme_id       TEXT NOT NULL,
    stage           TEXT NOT NULL,     -- applied | docs_submitted | committee | sanctioned
                                       -- | disbursed | subsidy_received | rejected | abandoned
    occurred_on     DATE NOT NULL,
    reported_by     TEXT NOT NULL,     -- 'operator' | 'applicant'
    reported_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Aggregation rules, both of which should be stated in the pitch:

1. **k-anonymity:** suppress any district cell with fewer than 5 applications.
2. **Self-selection is disclosed on the chart itself,** not buried. The Ledger reports what its users reported. That caveat, printed on the visual, is the same credibility move as the "what we cannot fix" slide.

---

## 8. Map

> ### `CHANGE 5` — Mappls kept for geocoding; rendering moved to MapLibre
>
> **Why:** two independent reasons.
>
> **Resilience.** Mappls quota is shared across web and mobile against a daily limit, and their terms require the Mappls logo and copyright to stay visible. If you hit a limit or the wifi dies, an SDK-rendered map goes blank. MapLibre rendering static GeoJSON does not.
>
> **The map should make an argument.** A "nearest office" pin-drop is forgettable. Your research already contains a far better map: **channel reachability**. India by district, coloured by whether a live SCA channel exists, with **Telangana and Ladakh dark**. "A qualified person here has nowhere to apply" is a map that argues. Layer 2 is Ledger pendency by district — numbers that exist nowhere else.

| Layer | Source | Notes |
|---|---|---|
| District boundaries | DataMeet, CC BY 4.0 | Simplify with `mapshaper` to ~2 MB; ship static, renders offline |
| Channel reachability | SCA list + Standing Committee | 38 SCAs; 2 states with none; 14 underperforming |
| Office / branch points | Mappls Nearby + RBI Master Office File | Geocode once at seed time, cache the results |
| Live address lookup | Mappls Place Search | The only genuinely live Mappls call |
| Ledger pendency | `application_milestone` | k-anonymised |

Google Maps is the wrong choice here regardless of quality: the universal $200 monthly credit was retired in March 2025 in favour of per-product free tiers that no longer pool, so a student team needs a billing card on file.

---

## 9. Deployment

> ### `CHANGE 6` — Docker Compose is the primary target; cloud is a mirror
>
> **Why three problems with Vercel + Render/Railway as the primary:**
>
> 1. **Vercel cannot run your backend.** WeasyPrint needs Pango/Cairo system libraries and Playwright needs a browser binary. Neither fits Vercel's Python serverless runtime. Vercel is fine for the static React bundle only.
> 2. **Free-tier cold starts.** Render spins down inactive free web services; a 50-second wake on the first judge interaction is a lost demo. Either pay for the smallest always-on instance for one week, or keep a cron pinging it.
> 3. **Venue connectivity.** Hackathon wifi is unreliable and sometimes filtered. If your demo requires the public internet to reach your own backend, you have added a dependency you did not need.
>
> **Resolution:** `docker-compose.yml` with `postgres`, `api`, `worker`, `web`, `caddy` runs the whole product on a laptop. The identical images deploy to Render for the judges' link. Vercel or Cloudflare Pages for the static frontend if you want a public URL.

External API calls (Bhashini, Sarvam, Mappls) sit behind a cache with committed fixtures, so a fully offline run still demos end to end. Say openly that the offline mode is using cached responses — a labelled fallback reads as preparation, an undisclosed one reads as fraud.

---

## 10. Explicitly not building

State these before a judge asks.

| Not building | Why |
|---|---|
| Blockchain anything | The Ledger is an append-only Postgres table. Say so first. |
| Vector DB / RAG | ~15 schemes. A `SELECT` covers it. |
| Kafka, microservices, Kubernetes | Three processes. Show the scaling *path*, not a deployment. |
| Approval-prediction ML | Report §7/G2: no scheme publishes an application-to-rejection funnel. There is no training signal. Any team claiming this is bluffing. |
| Aadhaar eKYC | Licensed AUA/KUA only. Confirmed unavailable (§8.2). |
| DigiLocker production integration | Partner onboarding required; auto-fetch confirmed working in only KA/MH/TN. **Manual capture is the default path, not the fallback.** |
| Fine-tuning any model | No labelled data exists to fine-tune on. |

Mocks for the above must be visibly labelled in the UI.

---

## 11. Before the clock starts

Ordered by how badly a late start hurts.

| # | Task | Why it is first |
|---|---|---|
| 1 | Register ULCA/Bhashini + Sarvam + Mappls keys | Signup friction is the standard day-one failure |
| 2 | Scrape 30–50 KVIC/NABARD model project profiles into `cost_template` | **Highest-leverage work in the whole build.** Without real capex/opex for "tailoring unit" or "two-buffalo dairy", Sanction-Ready is a template with invented numbers — the one weakness a domain judge finds in thirty seconds |
| 3 | Snapshot every NSFDC / MoSJE / state page; commit fixtures | Demo insurance against 504s |
| 4 | 20-minute WeasyPrint vs ReportLab Devanagari test | Settles `CHANGE 4` with evidence, not opinion |
| 5 | Obtain one real accepted project report format | I04 depends on it (report §16 item 2) |
| 6 | Simplify DataMeet GeoJSON with mapshaper | Slow map = bad first impression |
| 7 | Field interviews: 2 SCA staff, 2 CSC operators, 5 applicants (2 rejected) | Report §16 item 1. Everything in §4 of the report is reconstructed from documents |

---

## 12. Final stack

| Layer | Choice | Purpose | vs. proposed |
|---|---|---|---|
| **Frontend** | React 18 + Vite | SPA — applicant, operator, public ledger | Kept |
| | Tailwind + shadcn/ui | Component layer; 360px-first | Kept |
| | TanStack Query | Server state, caching, retry | **Added** |
| | react-i18next | UI string localisation | **Added** |
| | `json-logic-js` | Client-side field validation from server rules | **Added** |
| | MapLibre GL JS | Map rendering, works offline from static GeoJSON | **Changed** from Mappls SDK rendering |
| | Workbox + IndexedDB | Operator PWA offline queue | **Added** |
| **Backend** | FastAPI + uvicorn | REST API | Kept |
| | Pydantic v2 | Schemas + LLM structured-output targets | Kept |
| | SQLAlchemy 2.0 + Alembic | ORM and migrations | Kept (Alembic added) |
| | APScheduler | Crawl / extract / diff scheduling | **Added** — no scheduler was specified |
| **Database** | PostgreSQL 16 | Append-only `rule_version`, snapshots, milestones, ledger | Kept |
| **Rules** | `json-logic-py` + trace wrapper | Eligibility with per-condition provenance and tri-state verdict | Kept, wrapped |
| **Ingest** | httpx + selectolax | Static government HTML | **Added** — unspecified |
| | Playwright | myScheme only (JS SPA) | **Added** |
| | pdfplumber | Scheme PDFs | **Added** |
| **AI — text** | Sarvam 105B (hosted API) | Rule extraction from prose/PDF; report narrative; activity classification | Kept, **batch-only** |
| **AI — voice** | Bhashini (ULCA / Dhruva) | ASR, NMT, TTS — primary | **Changed** — was Sarvam-only |
| | Sarvam Saaras v3 / Bulbul v3 / Translate | Automatic fallback on timeout | Kept, demoted to fallback |
| **Finance** | Pure Python (`decimal`), unit-tested | EMI, cashflow, break-even, subsidy-delay scenario. No LLM touches a number | **Added as a hard rule** |
| **Documents** | Jinja2 + WeasyPrint + Noto fonts | Project report PDF with correct Indic shaping | **Changed** from ReportLab |
| **Maps** | Mappls Place Search / Nearby | Geocoding, office lookup | Kept, scope narrowed |
| | DataMeet district GeoJSON (CC BY 4.0) | Boundaries, static | **Added** |
| **Deploy** | Docker Compose | Primary demo target, fully offline-capable | **Changed** |
| | Render (Docker) | Public mirror — avoid free tier spin-down | Kept, with caveat |
| | Vercel / Cloudflare Pages | Static frontend only | Kept, scope narrowed |

---

## 13. One-line position

Finding the scheme is solved. This architecture builds the layer after it: a provenance-stamped registry that shows where every rule came from and where the government contradicts itself, a voice-first copilot that turns a spoken business idea into a costed and bankable application, and a console for the person who is actually holding the phone.
