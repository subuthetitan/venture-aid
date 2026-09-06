# Who owns what

| Pair | PS-mandated feature | Our differentiator | Files |
|---|---|---|---|
| A | Smart Scheme Recommender | Scheme Truth Layer | `routers/recommend.py`, `routers/truth.py`, `services/eligibility.py`, `pages/Recommender.jsx`, `pages/TruthLayer.jsx` |
| B | Financial Calculator | Sanction-Ready | `routers/calculate.py`, `routers/readiness.py`, `services/finance.py`, `pages/Calculator.jsx`, `pages/SanctionReady.jsx` |
| C | Partner Locator & Router | Transparency Ledger | `routers/locator.py`, `routers/ledger.py`, `components/`, `docker-compose.yml` |

## Second hats

| Role | Sits with | Job |
|---|---|---|
| Integrator | Pair C | Owns `main`. Runs the full stack every 4 hours. Only person who edits `models.py`, `schemas/`, `migrations/` |
| Pitch owner | Pair A | Deck, demo script, timing, the "what we cannot fix" slide |
| Evidence keeper | Pair B | Every deck claim traceable to `SOURCE_DATABASE.csv`; enforces the four "never say these" from the discovery report |
