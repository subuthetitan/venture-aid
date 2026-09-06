# PS 26092 — NSFDC Application Assistant

Smart India Hackathon 2026. AI-driven scheme matching for marginalised
entrepreneurs — plus the layer after discovery that nobody else builds.

## Run it

```bash
cp .env.example .env      # fill in keys, or leave blank and set OFFLINE_MODE=true
docker compose up --build
```

- Web: http://localhost:5173
- API docs: http://localhost:8000/docs

All six screens are navigable from the first commit. Every endpoint returns a
valid fixture, so nothing is ever blocked on anything else.

## What's here

| Feature | Pair | Status |
|---|---|---|
| Smart Scheme Recommender | A | fixture |
| Scheme Truth Layer | A | fixture |
| Financial Calculator | B | **real** |
| Sanction-Ready | B | fixture |
| Partner Locator & Router | C | fixture |
| Transparency Ledger | C | fixture |

## Structure

```
backend/app/
  main.py              all six routers registered - do not edit during build
  models.py            every table, one file, one migration
  schemas/__init__.py  FROZEN CONTRACTS - the reason pairs don't block
  routers/             one file per feature, one owner each
  services/finance.py  pure Python. no LLM touches a number
  fixtures/            day-zero responses in the real shape
frontend/src/
  App.jsx              all six routes registered - do not edit during build
  pages/               one file per feature, one owner each
shared/                seed data both sides read
```

## Rules that are not negotiable

1. **No number in a project report comes from a language model.** The finance
   engine is pure Python and unit-tested. This is what lets us make the claim
   on stage.
2. **Never silently resolve a contradiction.** When two government sources
   disagree, show both values, both URLs, both dates.
3. **Label every mock.** Seeded rules, synthetic ledger data, cached ASR
   responses. A labelled fallback reads as scoping; an unlabelled one reads as
   fraud when a judge asks.
4. **No new Alembic migrations during the build.** See CONTRIBUTING.md.

## Read next

- `docs/ARCHITECTURE.md` — stack decisions and why each one was made
- `docs/MVP_BUILD_PLAN.md` — feature scope, timeline, demo script
- `CONTRIBUTING.md` — branches, ownership, integration cadence
