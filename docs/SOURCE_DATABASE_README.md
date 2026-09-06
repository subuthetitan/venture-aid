# SOURCE_DATABASE.csv

Pair B's evidence-keeper deliverable, per `docs/MVP_BUILD_PLAN.md` §"Second hats":

> | Evidence keeper | Pair B | Every deck claim traceable to `SOURCE_DATABASE.csv`; enforces the four "never say these" from report §16 |

**How to use it: before stating any figure or claim on stage, find its row and check the
`stage_safe` column.**

`YES` means say it plainly. `YES_WITH_CAVEAT` means say it only with the caveat in `notes`
attached. `NO` means do not say it as fact at all.

## What this file is for

It exists to make visible what **is** and **is not** sourced. A large majority of the numbers
this project displays are unsourced placeholders, and the point of this file is that you can
see exactly which ones at a glance rather than discovering it when a judge asks.

Nothing in this file was researched, verified, or upgraded in confidence while writing it. Every
row records what was already known about a claim during the build. Where a value was a guess,
it is recorded as a guess.

## Columns

| Column | Meaning |
| --- | --- |
| `claim_id` | Stable id. Prefix indicates the group (`ST-` scheme terms, `CT-` cost templates, `NAME-`, `ELIG-`, `FMT-`, `LLM-`, `CALC-`, `LANG-`, `TIME-`, `TECH-`). |
| `claim_text` | The claim itself, as it would be stated. |
| `category` | `RATE`, `FEE_OR_COST`, `ELIGIBILITY`, `TIMELINE`, `DEMOGRAPHIC`, `FORMAT_CLAIM`, `TECHNICAL_CLAIM`. |
| `value_or_figure` | The specific figure or value asserted. |
| `source_type` | `VERIFIED_PUBLISHED` (exact source, confident) / `ESTIMATED` (placeholder, not from a real source) / `INFERRED` (reasoned from a related fact, not directly stated anywhere) / `UNVERIFIED_GUESS` (a name, label or slug invented for functional reasons). |
| `source_detail` | Where the claim actually comes from — file, test, or attestation. |
| `confidence` | `HIGH` / `MEDIUM` / `LOW`. |
| `stage_safe` | `YES` / `YES_WITH_CAVEAT` / `NO`. |
| `notes` | The caveat text, when `stage_safe` is not a plain `YES`. |

## Two distinctions this file is careful about

**The numbers and the URLs are rated separately.** The scheme rates, tenures, moratoria and
ceilings (`ST-01`..`ST-16`) and the four source URLs (`ST-URL-01`..`ST-URL-04`) are now both
`VERIFIED_PUBLISHED`, corroborated by `shared/seed_schemes.json`. That was **not** true in the
first version of this file: the URLs were then invented placeholders, and one of them was flat
wrong. The distinction still matters as a habit — **a real number can carry a fake citation** —
so the two are rated as separate rows rather than one.

**Claims about NSFDC are rated separately from claims about our system.** `ELIG-01` ("Mahila
Samriddhi is women-only") is *inferred* from the scheme's name and is not confirmed. `ELIG-02`
("our system never auto-recommends a women-only scheme to an unspecified applicant") is a claim
about our own code and is test-enforced. The second is safe to state flatly; the first is not.

## The strongest claim here

`LLM-01` — **"No number in the financial report was produced by a language model."** It is
directly checkable in the code (`Decimal` arithmetic throughout, no LLM or network call anywhere
in the app) and enforced by the test suite (`provenance='computed'` asserted for every scheme).
Say it flatly, without hedging. `LLM-02`, `ELIG-02`, `FMT-02`, `CT-SRC-01` and `TECH-03` are in
the same category.

## Open gap — the four "never say these"

**The four "never say these" items from report §16 are not reproduced anywhere in this
repository** — the build plan and `OWNERSHIP.md` reference them, but the report itself is not
checked in, so their exact wording is unknown to this file. They have deliberately **not** been
guessed at.

Whoever holds report §16 should transcribe those four items here. Until then, treat the rows
marked `stage_safe = NO` as the working never-say list. Two of them are already phrased as
explicit prohibitions:

- `FMT-01` — never claim the PDF matches the published PMEGP/Mudra DPR format.
- `TIME-01` — never repeat "one documented case ran three years" as fact. This sentence **was**
  shown to users in the subsidy note; it has since been removed from `finance.py` and a
  regression test blocks its return. The claim itself is still uncited: `MVP_BUILD_PLAN.md:60`
  asserts a documented case exists but names none.
- `LANG-01` — never claim Kannada support. See the demo-script conflict flagged in that row.
- `TIME-03` — never claim the retired Term Loan is "still the top search result"; the retirement
  date is verified, the ranking is not.
- `FMT-03` — never describe the PDF as labelled for human review; that label is currently missing.

## Correction history — this file has been wrong twice

Recording this because a file whose whole job is honesty should show its own error history.

**First pass** rated ~6% of claims stage-safe. It was built without ever opening
`shared/seed_schemes.json`, whose `_note` reads *"Hand-written, verified against live pages on
2026-09-03."* 26 rows were wrongly logged as guesses when a verified in-repo source existed:
three scheme display names, four source URLs (one of which Pair B had guessed *wrongly* —
`/en/suvidha` vs the real `/en/suvidha-loan`), and the sixteen scheme-term figures.

**Second pass** (this audit) read every file under `shared/` and `docs/` end to end, rather than
grepping them. `docs/MVP_BUILD_PLAN.md` and `docs/ARCHITECTURE.md` had only ever been grepped and
turned out to be blind spots too. Seven rows were added and four corrected — see rows whose notes
begin `SECOND-PASS CORRECTION`.

The lesson worth keeping: **grepping a document is not reading it.** Both misses came from
searching a file for one string and concluding nothing else in it was relevant.

## Scope limit — this file is not yet the whole deck

`docs/OWNERSHIP.md` assigns the evidence keeper *"every deck claim"*. In practice this file
covers Pair B's surface thoroughly and Pair A/C claims only where they were encountered
(`ELIG-04`, `ELIG-05`–`07`, `TIME-02`, `TIME-03`). Pair C's claims — the ~200 synthetic ledger
records, the "Telangana and Ladakh go dark" reachability assertion, Mappls routing — are **not
logged here**. Someone should extend this file before the deck is final.

## Regenerating

The figure rows are generated directly from `backend/app/services/finance.py` and
`cost_templates.py`, so the CSV cannot silently drift from the code. If those figures change,
regenerate rather than hand-editing, and re-check the qualitative rows by hand.
