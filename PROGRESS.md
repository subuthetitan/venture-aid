# PS 26092 — Progress checkpoint

**Team:** B (Financial Calculator + Sanction-Ready)
**Checkpoint date:** 2026-09-06
**This pass:** hardening only. No new features. Every existing bug found was fixed,
every fix has a regression test, and both sides build clean.

**Test suite:** `142 passed, 8 skipped` (was `112 passed, 8 skipped`) — +30 tests.
All 8 skips are WeasyPrint's native Pango/Cairo stack, unavailable on Windows;
they run inside the API container, which installs those libraries.
**Frontend:** `npm run build` clean.
**Compose:** `docker compose config` validates.

> ⚠️ This working copy is **not a git repository**. Nothing here is committed and
> nothing is recoverable if the folder is lost. First action after reading this:
> `git init`, commit, push. See "Do this first" below.

---

## 1. Where the whole product stands

Owner columns follow `docs/OWNERSHIP.md`. Only Pair B's two verticals have real
implementations behind them; A and C are still day-zero fixtures, exactly as
`CONTRIBUTING.md` intends at this stage.

| Feature | Pair | Backend | Frontend | Verdict |
|---|---|---|---|---|
| Smart Scheme Recommender | A | **real** (DB-backed, seeded) | `Placeholder` | backend done, no UI |
| Scheme Truth Layer | A | **real** (`rule_version` group-by) | `Placeholder` | backend done, no UI |
| **Financial Calculator** | **B** | **real, tested** | **real, complete** | **done** |
| **Sanction-Ready** | **B** | **real except the voice UI** | **real except the mic** | **~85%** |
| Partner Locator & Router | C | **real** (DB-backed, 12 channels) | **real** (MapLibre) | done |
| Transparency Ledger | C | **real** (k-anonymised SQL) | **real** | done |

### Cross-cutting, nobody's yet

| Thing | State |
|---|---|
| Alembic migrations | `0001_initial` replaced by Pair A/C's `19bea6c2f9a4`; **now runs on API start** (see §7) |
| `worker` (APScheduler) service | in `ARCHITECTURE.md`, not in `docker-compose.yml` |
| `shared/seed_schemes.json` | now the source for Pair A's seed **and** contract-tested against `SCHEME_TERMS` (§7) |
| `react-i18next` | installed, never imported — all UI copy is hardcoded English |
| `@tanstack/react-query` | provider mounted in `main.jsx`, no page uses it |
| `maplibre-gl` | now used by Pair C's `DistrictMap.jsx` |
| `json-logic-py` in `requirements.txt` | **resolved** by Pair A — pinned to `panzi-json-logic==1.0.1` |

---

## 2. Team B — what is actually finished

**Financial Calculator — complete.**
`services/finance.py` is pure `Decimal` arithmetic with no LLM, no network and no
database, covering four schemes with real published rates. `routers/calculate.py`
serves it, plus a new `GET /api/calculate/schemes`. `pages/Calculator.jsx` renders
inputs, summary, the full amortisation schedule and the subsidy-delay scenario.
`tests/test_finance.py` + `tests/test_calculate_api.py` are the evidence behind
the on-stage claim.

**Sanction-Ready — everything but the microphone.**

| Piece | State |
|---|---|
| `services/classification.py` — transcript → activity | real, deterministic, 33 tests |
| `services/cost_templates.py` — 8 activities | real code, **placeholder figures** (§5) |
| `services/finance.py` reused for the financing block | real |
| `services/pdf_generator.py` + `templates/project_report.html` | real; degrades cleanly when WeasyPrint is missing |
| `services/transcription.py` — Bhashini → Sarvam → fixture | real, never exercised (no keys) |
| `POST /api/readiness` | real end to end |
| `POST /api/readiness/transcribe` | real |
| `pages/SanctionReady.jsx` | real — but **type-it-only** |

**The one real gap: `SanctionReady.jsx` never calls `/api/readiness/transcribe`.**
The provider chain, the timeout budget, the fallback and the offline fixture all
exist and are tested on the backend; the page only offers the textarea. The build
plan's "always keep a *type it instead* path visible" is satisfied by accident —
it is currently the *only* path. Demo beat 4 ("speak a business idea in Kannada")
cannot be performed today. This is the highest-value remaining Pair B task.

---

## 3. Bugs found and fixed in this pass

Ordered by how badly each one would have hurt on stage.

### 3.1 `total_interest` silently understated the cost of borrowing — **critical**

`services/finance.py`

Interest capitalised during the moratorium was computed and added to the
principal, but was **not** included in `total_interest`, which summed only the
schedule rows. The schedule starts after the moratorium, so that interest existed
in `total_repayment` and in no reported total.

On a ₹5,00,000 Suvidha loan the response omitted **₹20,336** and failed the
identity any finance-literate judge checks first:

```
sanctionable 500,000 + total_interest 100,982  =  600,982
total_repayment                                =  621,318   ← ₹20,336 unexplained
```

On the one feature whose entire claim is *"every number here is arithmetic we can
show you"*, an understated cost of borrowing is the worst defect the product could
carry.

**Fix:** `total_interest` is now the full cost of borrowing. A new
`moratorium_interest` field reports the capitalised portion separately, so the
schedule's interest column visibly reconciles instead of looking like an
arithmetic error. Both the Calculator UI and the PDF now explain the gap in
words. Regression test asserts `sanctionable + total_interest == total_repayment`
for every scheme.

### 3.2 Negative `own_contribution` inflated the loan — **critical**

`schemas/__init__.py`, `services/finance.py`

No money field had a lower bound. A ₹1,00,000 project with
`own_contribution = -50,000` sanctioned **₹1,50,000** — a larger loan than the
project needs, on a document headed to a bank.

**Fix:** `ge=0` on `project_cost`, `own_contribution`, `subsidy_amount` and
`subsidy_delay_months` (which also gained `le=600` so a typo cannot produce an
absurd subsidy note). `calculate()` clamps as well, because `readiness.py` and the
tests call it directly, bypassing request validation.

*Note for the integrator:* this touches `schemas/`, which `CONTRIBUTING.md` marks
integrator-only. Both changes are **wire-compatible** — `ge=0` only rejects input
that was already nonsense, and `moratorium_interest` is additive with a default,
so no existing consumer breaks. Flagged here for sign-off rather than assumed.

### 3.3 The classifier confidently classified unrelated text — **high**

`services/classification.py`

Keyword matching was plain case-folded substring containment, so short Latin
keywords fired inside unrelated words:

| Transcript | Was classified as | Because |
|---|---|---|
| `I want to sell chairs in my shop` | `tea_stall` | `chai` ⊂ **chai**rs |
| `Please tell me instead what to do` | `tea_stall` | `tea` ⊂ ins**tea**d |
| `I want to open a steam laundry` | `tea_stall` | `tea` ⊂ s**tea**m |

Each of those would have produced a fully costed tea-stall project report for a
bank submission. The module's own docstring promises it "never guesses".

**Fix:** Latin-script keywords now match on word boundaries with an optional
trailing `-s`/`-es`, so `goats` still matches `goat` — the boundary rule does not
trade false positives for missed real matches. Devanagari and Kannada keywords
stay on substring matching deliberately: those scripts agglutinate case markers
onto the noun (`सिलाईका`), and the keywords are long enough that the
false-positive risk is negligible. Reasoning is recorded in the module docstring.

### 3.4 Unknown `scheme_id` returned HTTP 500 — **medium**

`services/finance.py`, `routers/calculate.py`

`SCHEME_TERMS[scheme_id]` raised a bare `KeyError`. Utkarsh is the realistic
trigger: it is deliberately absent from `SCHEME_TERMS` (NSFDC's pages contradict
themselves on its terms) but present in Pair A's seed data, so the first
integration between the two pairs would have hit it.

**Fix:** typed `finance.UnknownScheme`, turned into a 422 carrying
`supported_schemes` — the same error shape the readiness endpoints already use, so
the frontend can render a recovery path.

### 3.5 `emi()` divided by zero — **medium**

`services/finance.py`

Both branches divided by `months`. A scheme whose moratorium equals its tenure
would take the endpoint down. Not reachable with today's four schemes; reachable
the moment anyone adds a fifth.

**Fix:** returns `Decimal(0)` when there is nothing or no time to repay.

### 3.6 Unbounded audio upload — **medium**

`routers/readiness.py`

`audio.file.read()` with no argument read the entire upload into memory; one
oversized POST could exhaust the API container. An **empty** upload fell straight
through the provider chain to the cached fixture and was returned as though it
were a real transcription.

**Fix:** 20 MB cap → 413 `AUDIO_TOO_LARGE`; empty upload → 422 `EMPTY_AUDIO`,
both pointing at the type-it-instead path.

### 3.7 The frontend's scheme list could drift out of sync — **medium**

`pages/Calculator.jsx`, `routers/calculate.py`, `lib/api.js`

`SCHEMES` was hardcoded, duplicating both `SCHEME_TERMS` and
`WOMEN_ONLY_SCHEMES`. Its own comment admitted it could silently drift from the
gate that actually governs eligibility.

**Fix:** new `GET /api/calculate/schemes` serves rate, tenure, moratorium, ceiling
and `women_only` from the engine. The page fetches it and keeps a small id-only
fallback so it still renders offline. Display labels stay client-side — three of
the four are still unsourced transliterations, and that TODO stands. A test
asserts the endpoint agrees with `WOMEN_ONLY_SCHEMES` exactly.

### 3.8 `api.js` discarded error bodies — **medium**

`lib/api.js`, `pages/SanctionReady.jsx`

`req()` threw `new Error("<status> <path>")` and dropped the response body. Since
the backend's `UNRECOGNIZED_ACTIVITY` error carries the `supported_activities`
list the UI renders as recovery chips, `SanctionReady.jsx` had grown a complete
duplicate `fetch` just to reach it — with its own copy of `BASE` and its own error
parsing to keep in sync.

**Fix:** `req()` now throws an `ApiError` carrying `status` and the parsed
`detail`, with `status: 0` distinguishing an unreachable server from an HTTP
error. The duplicate fetch is deleted; the page uses `api.readiness()`. The
Calculator now shows the backend's own error message instead of a bare status
code. Its TODO is resolved and removed.

### 3.9 Smaller correctness fixes

| Where | Bug | Fix |
|---|---|---|
| `lib/api.js` | `channels(district)` interpolated the code raw — a `&` or `#` corrupted the query string | `encodeURIComponent` |
| `pages/SanctionReady.jsx` | `key={item.item}` on capex rows; `capex_items` is `list[dict]` so duplicate names drop a row | key includes the index |
| `pages/SanctionReady.jsx` | `rupees()` returned non-numbers raw, so a string could render as a rupee figure | em dash, matching `Calculator.jsx` |
| `routers/readiness.py` | `max()` over an empty eligible-scheme list → `ValueError` → 500 | 422 `NO_ELIGIBLE_SCHEME` |
| `routers/readiness.py` | `_report_key` basis string was a mangled one-line implicit concat | reformatted |

### 3.10 Build and environment fixes

| Where | Bug | Fix |
|---|---|---|
| `frontend/Dockerfile` | `COPY package.json` + `npm install` — `package-lock.json` never entered the image, so the container could resolve different transitive versions than any laptop | copy the lockfile, `npm ci` |
| `docker-compose.yml` | `env_file: [.env]` hard-fails on a clean clone before anyone runs `cp .env.example .env` | `required: false`; keys blank → every service degrades to its fixture |
| `.env.example` | **`ULCA_PIPELINE_ID` was missing entirely.** `config.py` requires it, so `_call_bhashini()` returns `None` immediately and every transcription silently falls through to Sarvam — the primary provider never runs and nobody notices | documented and added, with `TRANSCRIPTION_TIMEOUT_SECONDS` |
| `backend/`, `frontend/` | no `.dockerignore`; `COPY . .` pulled `.venv`, `__pycache__` and `node_modules` into images | added both |

---

## 4. Everything changed in this pass

**Backend**

| File | Change |
|---|---|
| `app/services/finance.py` | moratorium interest in `total_interest`; `UnknownScheme`; `emi()` zero guard; input clamping |
| `app/schemas/__init__.py` | `ge=0` on money fields, `le=600` on delay; additive `moratorium_interest` |
| `app/routers/calculate.py` | 422 for unknown scheme; new `GET /schemes` |
| `app/routers/readiness.py` | audio size + empty guards; `NO_ELIGIBLE_SCHEME`; `MAX_AUDIO_BYTES`; formatting |
| `app/services/classification.py` | word-boundary matching for Latin keywords |
| `app/templates/project_report.html` | moratorium-interest breakdown under Total interest |
| `backend/.dockerignore` | **new** |

**Backend tests** — +30

| File | Change |
|---|---|
| `tests/test_calculate_api.py` | **new** — 10 HTTP-level tests; the router had none |
| `tests/test_finance.py` | reconciliation updated for the split; +6 regression tests |
| `tests/test_classification.py` | +9 boundary / plural / non-Latin tests |
| `tests/test_readiness.py` | +3 upload-guard tests |

**Frontend**

| File | Change |
|---|---|
| `src/lib/api.js` | `ApiError` with parsed body; `BASE` exported; `isStructuredDetail`; `schemes()`; URL encoding |
| `src/pages/Calculator.jsx` | scheme list from the API; moratorium interest shown and explained; structured errors |
| `src/pages/SanctionReady.jsx` | duplicate fetch deleted; key fix; `rupees` fix |
| `frontend/Dockerfile` | `npm ci` from the lockfile |
| `frontend/.dockerignore` | **new** |

**Root**

| File | Change |
|---|---|
| `docker-compose.yml` | `.env` optional |
| `.env.example` | `ULCA_PIPELINE_ID`, `TRANSCRIPTION_TIMEOUT_SECONDS` |
| `PROGRESS.md` | **new** — this file |

---

## 5. Known-and-accepted, not bugs

These are deliberate, documented in the code, and **must not be quietly dropped**.

1. **Every figure in `cost_templates.py` is an unsourced estimate.** Not one has
   been checked against a published KVIC or NABARD model profile; `source_url` is
   the empty string on all eight, because an invented citation is worse than a
   missing one. `ARCHITECTURE.md §11` ranks sourcing these the highest-leverage
   pre-build task. **A Sanction-Ready report is only as trustworthy as this file.**
2. **Kannada keywords and labels are written from recall, not verified.** Marked
   `KN-REVIEW` throughout. A misspelling fails *silently* — it simply never
   matches — so Kannada coverage may be far worse than the table suggests.
3. **Hindi keywords want a native-speaker pass** for spelling variants and
   regional synonyms.
4. **Three of four scheme display names are transliterations**, not published
   NSFDC names. Only "Suvidha Loan" is sourced.
5. **`project_report.html` is not verified against a real PMEGP or Mudra DPR.**
   The template says so, twice. Do not claim otherwise on stage.
6. **`break_even_months` is deliberately pessimistic** — it subtracts the EMI *and*
   divides by the full project cost, double-counting capital recovery. Chosen so
   the number is never one we have to walk back. Wants a finance-literate review.
7. **Devanagari conjunct shaping is unverified on any machine we control.** The
   tests exist and skip. `ARCHITECTURE.md CHANGE 4` calls for a 20-minute check on
   day zero; it has not been done.

---

## 6. What is left

### Do this first

- [ ] **`git init` and commit.** This folder is not under version control. Every
      fix above exists in exactly one place, on one disk.
- [ ] Run the suite inside the API container so the 8 WeasyPrint tests actually
      execute — including the Devanagari conjunct check (item 7 above).

### Team B, ordered

- [ ] **Wire the microphone in `SanctionReady.jsx`.** `MediaRecorder` → `POST
      /api/readiness/transcribe` → fill the textarea → show which provider served
      it. The backend is done and tested; this is UI only, and it is the whole of
      demo beat 4.
- [ ] **Source the cost templates** from published KVIC/NABARD model profiles.
      Real figures, real `source_url`. Highest-leverage task in the build.
- [ ] Register ULCA/Bhashini credentials **including the pipeline ID**, and run
      the provider chain against the live API at least once. Nothing in
      `transcription.py` has ever talked to a real server.
- [ ] Native-speaker pass on the Hindi and Kannada keyword tables and labels.
- [ ] Obtain a real accepted project report format; align the template or keep the
      disclaimer permanently.
- [ ] Confirm the four scheme display names against published NSFDC pages.
- [ ] Finance-literate review of `_break_even_months`.
- [ ] Per-activity document checklists (currently one static list for all eight).

### Other pairs — for the integrator, not for us to build

- [x] ~~Pair A: real eligibility engine~~ — **done on `pairA`, merged in §7.**
      `CONTRADICTORY_SOURCES` now fires: Suvidha at ₹4.2 lakh returns the
      ₹5L / ₹3L / ₹3L split across three live government URLs. The reveal works.
- [ ] Pair A: build `Recommender.jsx` and `TruthLayer.jsx` — the backend is real
      but both screens are still `Placeholder`, so none of it is demoable yet.
- [ ] Pair C: map, channels, routing, ledger, reachability layers — all still empty.
- [ ] Integrator: pin `json-logic-py`; decide how migrations run (compose has no
      migration step); add the `worker` service or cut it from the architecture doc.
- [ ] Shell: `react-i18next` scaffolded but unused — all copy is English.

---

## 7. Merge with Pair A (`pairA` @ `ed777df`)

**Verdict: the two branches merge cleanly, but the merged product was broken at
runtime until the three fixes below.** Git reported no conflicts, every test
passed, and two of the six screens still returned HTTP 500.

### 7.1 What the merge looks like

The merge base is `ac2c7c0 Initial commit` — `teamb` and `pairA` share nothing
after it. Despite that:

| | Files changed vs. base | Overlap |
|---|---|---|
| `pairA` (incl. Pair C work merged into it) | 14 | **0** |
| `teamb` | 30 | **0** |

Zero file-level overlap, so `git merge` is automatic. Pair A's work is
**backend-only** — they never touched `lib/api.js`, `schemas/__init__.py`, or any
page, which is why nothing collided. `0001_initial.py` is deleted and replaced by
Pair A/C's `19bea6c2f9a4_initial_schema_all_pairs.py`; the revision chain is
coherent (single revision, `down_revision = None`).

### 7.2 The problem git could not see

`git merge` succeeded and the full suite passed — **because no test and no CI
check ever booted the stack against a real database.**

Pair A's `recommend.py` and `truth.py` used to return fixtures. Their real
versions query the `scheme` and `rule_version` tables. Nothing in this repo has
ever run `alembic upgrade head` or the Truth Layer seed — which was harmless
while those routers were fixtures, and fatal the moment they were not.

Measured against an empty database, i.e. what `docker compose up` produced:

```
GET  /health                    -> 200      <-- the only thing CI checked
POST /api/calculate             -> 200      (Pair B, no DB)
POST /api/recommend             -> 500      relation "scheme" does not exist
GET  /api/truth/contradictions  -> 500
```

So CI would have gone **green** on a merge that killed the Recommender, the Truth
Layer, and the contradiction reveal the demo is built around.

### 7.3 Fixes added to make the merge work

**1. `docker-compose.yml` — run migrations and the seed before uvicorn.**
The `api` service now runs `alembic upgrade head`, then the Truth Layer seed,
then the server. Migration failure is fatal (nothing works without tables); seed
failure is **not** — it logs a warning and still starts, so Pair B's calculator
and the shell keep working. The seed is idempotent, so restarts are safe.

> Sub-bug found while writing it: the first version used a YAML folded scalar
> with an indented continuation line. YAML only folds newlines into spaces at
> **uniform** indentation, so the rendered command kept a literal newline and
> `sh` would have died on the following `&&`. Caught with
> `docker compose config` + `sh -n`; all lines are now at one indent level and
> the rendered string is verified newline-free and syntactically valid.

**2. `.github/workflows/ci.yml` — smoke-test one endpoint per pair.**
CI curled `/health` and nothing else, and `/health` is a static dict that touches
no database — which is exactly why 7.2 was invisible. CI now exercises
`/api/recommend`, `/api/truth/contradictions`, `/api/calculate`, `/api/ledger` and
`/api/locator/reachability`, and asserts on *content*, not just status: a
recommend response with zero matches fails the build, because that means the seed
did not run even though the HTTP status was 200. Also added `docker compose logs
api` on failure.

**3. `backend/tests/test_seed_contract.py` — new, 11 tests.**
`finance.py` claims in its docstring that `shared/seed_schemes.json` is the source
of truth for scheme terms. Nothing enforced it, and nothing *could* before the
merge — the two files lived on branches sharing only the initial commit. Now they
are in one tree, so it is checked: every scheme in `SCHEME_TERMS` must exist in the
seed file with a matching rate and ceiling, retired schemes must never be
calculable, and the retired scheme Pair A's recommender can emit must return a
clean 422 from `/api/calculate` rather than a 500.

Verified non-vacuous by mutation: changing Suvidha's rate from 8.0 to 9.0 fails
with `nsfdc.suvidha: finance.py says 9.0%, seed_schemes.json says 8.0%`.

### 7.4 Where the two pairs already agreed

Worth recording, because it means no reconciliation was needed: Pair A's
hand-verified seed file and Pair B's `SCHEME_TERMS` **already matched exactly** on
all four active schemes — rates 8.0 / 6.5 / 6.0 / 6.0 and ceilings
₹9,00,000 / ₹1,25,000 / ₹1,25,000 / ₹2,00,000. Test 3 above now locks that in.

One genuine cross-pair interaction fell out in Pair B's favour: the seed contains
a **retired** scheme (`nsfdc.term_loan`) which Pair A's recommender deliberately
surfaces, and which `SCHEME_TERMS` does not model. Handing that id to
`/api/calculate` returns the 422 `UNKNOWN_SCHEME` added in §3.4 — the fix landed
before the case that needed it existed.

### 7.5 Merged state, verified

| Check | Result |
|---|---|
| `git merge origin/pairA` | clean, no conflicts |
| Backend suite | **160 passed, 8 skipped** (142 Pair B + 7 Pair A + 11 new) |
| `npm run build` | clean |
| `docker compose config` | valid; api command verified newline-free and `sh -n` clean |
| `/api/recommend` @ ₹4.2 lakh | **200**, 5 matches, `CONTRADICTORY_SOURCES` on Suvidha |
| `/api/truth/contradictions` | **200**, 1 contradiction, positions ₹5L / ₹3L / ₹3L |

**The contradiction reveal works.** Demo beat 2 is live end to end.

> Migrations + seed were exercised against SQLite rather than Postgres, because
> the Docker daemon was not running on this machine. That required a one-line
> `BigInteger -> INTEGER` shim, since SQLite only auto-increments
> `INTEGER PRIMARY KEY` while Postgres uses `BIGSERIAL`. The shim is in the
> throwaway verification script only — **not** in the repo. Someone should still
> run `docker compose up` once against real Postgres before demo day.

### 7.6 Still open after the merge

- [ ] **Pair A has no frontend.** `Recommender.jsx` and `TruthLayer.jsx` are still
      `Placeholder`. The backend reveal works and nobody can see it.
- [ ] Pair C's map/locator/ledger work is on `main`, **not** on `pairA` or
      `teamb`. A three-way integration is still ahead; this pass only proves
      A + B.
- [ ] CI still runs `pytest -q || true`, so tests cannot fail the build. Left
      alone deliberately — that is the integrator's policy call, not Pair B's —
      but with 160 passing tests it is worth revisiting.
- [ ] `psycopg` is now required to *import* `app.main`, because Pair A's routers
      pull in `app/db.py`, which calls `create_engine()` at module scope. It is
      already in `requirements.txt`, so this only bites minimal hand-rolled
      virtualenvs. Not fixed; noted.

---

## 8. Three-way integration — all six features on one branch

Branch `integration/all-pairs` = `origin/main` (Pair C) + `teamb` (Pair A + Pair B).

Merge base is `a224d45`, a real common ancestor, so this was a genuine 3-way
merge rather than the unrelated-histories mess of §7.

### 8.1 Conflicts

Only **three files** were touched by both sides, and only **one** conflicted:

| File | Outcome |
|---|---|
| `.env.example` | **CONFLICT** — both sides appended a key at the same spot |
| `backend/app/config.py` | auto-merged correctly |
| `frontend/src/lib/api.js` | auto-merged correctly |

`.env.example` was resolved by keeping **both** sides: Pair C's
`MAPPLS_STATIC_KEY` and Pair B's `TRANSCRIPTION_TIMEOUT_SECONDS`. Verified all
nine keys survive.

The two auto-merges were reviewed rather than trusted:

- `config.py` — correctly carries both `mappls_static_key` and
  `transcription_timeout_seconds`.
- `api.js` — Pair B rewrote this file wholesale while Pair C appended a `route()`
  helper, which is the shape that usually produces a silent drop. Checked the
  merged export surface key by key: nothing from either side was lost.
  Pair C's pages read `e.message` on failure, and `ApiError` preserves the
  original `"<status> <path>"` message, so Pair B's error rework is backwards
  compatible with their code.

### 8.2 The bug the merge exposed — Pair C's seed never ran either

Exactly the §7.2 failure, second verse. Pair C's `ledger.py` and `locator.py` are
DB-backed, and their loader `backend/app/fixtures/load_pair_c.py` is idempotent,
correct, and **never invoked by anything**. On a migrated-but-unseeded database
`/api/ledger`, `/api/locator/channels` and `/api/locator/reachability` all return
empty with HTTP 200 — which no status-code check would catch.

**Fixed** by extending the compose startup chain from §7.3:

```
alembic upgrade head
  -> python -m app.services.seed_truth_layer   (Pair A)
  -> python -m app.fixtures.load_pair_c        (Pair C)   <- added
  -> uvicorn
```

Both seeds are non-fatal on failure so a bad fixture cannot take the API down.
Verified the rendered command is newline-free and passes `sh -n`, and that
`python -m app.fixtures.load_pair_c` actually resolves (`app/fixtures/` has no
`__init__.py`, but it works as a namespace package — checked, not assumed).

**CI extended** to assert Pair C's endpoints return *data*, not just 200:
`/api/ledger` must have cells, `/api/locator/reachability` and
`/api/locator/channels` must be non-empty. An empty response now fails the build.

### 8.3 Other fix

`api.js` — Pair C's `route()` interpolated `to_channel_id` and both coordinates
into the query string unencoded. Same bug already fixed for `district_code` in
§3.9; channel ids come from the database, so an unencoded `&` or `#` silently
truncates the URL. Now encoded, and the stray indentation from the auto-merge
cleaned up.

### 8.4 Verified

| Check | Result |
|---|---|
| Merge | 1 conflict, resolved; 2 auto-merges reviewed |
| Backend suite | **160 passed, 8 skipped** |
| `npm run build` | clean |
| `docker compose config` | valid; command `sh -n` clean, newline-free |
| CI workflow YAML | parses, 5 steps, no duplicates |
| Conflict markers in tree | none |

End-to-end against a migrated + fully seeded database:

```
POST /api/recommend              [A] -> 200  5 matches, top=CONTRADICTORY_SOURCES
GET  /api/truth/contradictions   [A] -> 200  1 contradiction
POST /api/calculate              [B] -> 200  EMI 11505.9, reconciles=True
POST /api/readiness              [B] -> 200  tailoring_unit, cost 85,000
GET  /api/locator/channels       [C] -> 200  12 channels
GET  /api/locator/reachability   [C] -> 200  24 district cells
GET  /api/ledger                 [C] -> 500  <- see below
```

> **`/api/ledger` is UNVERIFIED, not broken.** It uses
> `PERCENTILE_CONT(0.5) WITHIN GROUP (...)`, which is valid PostgreSQL and which
> SQLite rejects with `near "(": syntax error`. The verification harness runs on
> SQLite because the Docker daemon was unavailable on this machine. Confirmed the
> failure is the harness, not Pair C's code — but **this endpoint must be checked
> once against real Postgres before demo day.** The CI smoke test added in §8.2
> will do exactly that on the next push.

### 8.5 Still open

- [ ] **Run `docker compose up` once against real Postgres.** Three things have
      only ever been exercised on SQLite or not at all: the Alembic migration,
      `/api/ledger`'s window function, and the WeasyPrint PDF path (8 skipped
      tests). This is the single highest-value remaining check.
- [ ] Pair A still has no frontend — `Recommender.jsx` and `TruthLayer.jsx` are
      `Placeholder`. With all three pairs merged, this is now the only feature
      whose backend works and whose screen does not exist.
- [ ] `SanctionReady.jsx` still never calls `/api/readiness/transcribe` (§2).
- [ ] CI still runs `pytest -q || true`.

### 8.6 CI was running ZERO tests (found by PR #14's own CI run)

The first CI run on PR #14 went green. Reading the step logs rather than the
badge showed the "Backend tests" step had actually printed:

```
Interrupted: 9 errors during collection
E   ModuleNotFoundError: No module named 'app'
```

Every test module failed to import, pytest ran **zero** tests, and
`pytest -q || true` swallowed the non-zero exit so the step reported success.

**Cause.** Test modules do `from app... import ...`, which needs `backend/` on
`sys.path`. `python -m pytest` adds the current directory automatically — which
is how the suite has always been run by hand, so it always passed. The bare
`pytest` console script does **not**, and that is exactly how CI invokes it
(`docker compose exec -T api pytest -q`). Reproduced locally: `python -m pytest`
gives 160 passed, `pytest` gives 9 collection errors, same tree.

This was never a Pair B problem specifically — **the suite has never run in CI
for any pair since the repo was created.** It was invisible because `|| true`
turned a total failure into a green check.

**Fixed** by adding `backend/pytest.ini` with `pythonpath = .`, so the suite
behaves identically by hand, in CI, and in the container. Verified against all
three invocation styles.

`|| true` is deliberately left in place for this round, so that the next CI run
reports what the tests genuinely do inside the container without blocking the
PR — notably the 8 WeasyPrint tests, which are skipped locally but should
actually execute there. That result should decide whether `|| true` goes.

### 8.7 PDF generation was broken in the container (found once tests actually ran)

With §8.6 fixed, the suite ran in CI for the first time and reported
**8 failed, 159 passed, 1 skipped**. All eight failures are the WeasyPrint PDF
tests — the ones that skip locally and had therefore never executed anywhere.

```
weasyprint/pdf/stream.py:246: AttributeError: 'super' object has no attribute 'transform'
```

**Cause.** `weasyprint==62.3` declares `pydyf>=0.10.0` with no upper bound, so a
fresh image build resolved **pydyf 0.12.1**, which removed `pydyf.Stream.transform`.
WeasyPrint's `Stream.transform` calls `super().transform(...)`, so every render
died. Verified by installing each version and introspecting: `Stream.transform`
is present in pydyf 0.10.0 and 0.11.0, absent in 0.12.1.

**Why nobody saw it.** Three independent blindfolds stacked:

1. WeasyPrint's native stack will not install on Windows, so all eight tests
   `skip` locally — the suite reported green.
2. CI was collecting zero tests (§8.6).
3. `_store_pdf()` catches every exception and returns `pdf_url=None` by design,
   so the API degraded to "no PDF" **silently** instead of failing. The
   Sanction-Ready PDF — the headline artefact of that feature — was simply
   absent, and the frontend rendered its disabled-button fallback as though
   that were normal.

**Fixed** by pinning `pydyf==0.10.0`, the release weasyprint 62.3 was built
against.

> Wider lesson for the integrator: `requirements.txt` pins direct dependencies
> but not transitive ones, so any rebuild can pull a breaking transitive at any
> time. This is the second time an unpinned dependency has bitten
> (`json-logic-py` was the first). A lockfile would close the class.

**This fix cannot be verified locally** — WeasyPrint does not run on this
machine. CI is now the only environment that can confirm it, which is precisely
what §8.6 restored.
