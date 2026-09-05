# How three pairs combine work

## One repo, not three

Monorepo. One `docker compose up`, one set of contracts, one deploy. Three repos
means three deploys and a day lost to wiring them together.

## Branches

Trunk-based with short-lived branches. Nothing lives longer than four hours.

```
main                    always runnable, always demoable
  pair-a/recommender
  pair-b/finance-engine
  pair-c/map-layers
```

Merge to `main` at least every four hours, even if the feature is half-done
behind a flag. Long-lived branches are how hackathon teams discover at hour 30
that nothing fits together.

## Why you will not get merge conflicts

Three files cause almost every conflict in a project like this. All three are
finished on **day zero** and then nobody touches them:

| File | Pre-filled with | Rule |
|---|---|---|
| `backend/app/main.py` | All six routers registered | Do not edit during the build |
| `frontend/src/App.jsx` | All six routes registered | Do not edit during the build |
| `backend/migrations/versions/0001_initial.py` | Every table for every pair | **No new migrations during the build** |

Need a column? Ask the integrator to add it to `0001_initial`, then everyone runs
`docker compose down -v && docker compose up --build`. You lose your local data,
which is seed data, which is in git.

## Why you will not block each other

**Every endpoint returns a valid fixture from day zero.** Not a stub the frontend
has to mock — a real HTTP response in the real shape from the real server.

So Pair C builds the operator queue against `POST /api/readiness` on hour one,
while Pair B is still writing the finance engine. When Pair B is ready, they
replace the function body. The response shape never changes, so nothing on the
frontend breaks.

The contracts that make this work are frozen in `backend/app/schemas/__init__.py`.
Changing one requires agreement from all three pairs plus the integrator.

## Directory ownership

| Path | Owner |
|---|---|
| `backend/app/routers/recommend.py`, `truth.py` · `frontend/src/pages/Recommender.jsx`, `TruthLayer.jsx` | Pair A |
| `backend/app/routers/calculate.py`, `readiness.py` · `backend/app/services/finance.py` · `frontend/src/pages/Calculator.jsx`, `SanctionReady.jsx` | Pair B |
| `backend/app/routers/locator.py`, `ledger.py` · `frontend/src/components/` · `docker-compose.yml` · Dockerfiles | Pair C |
| `backend/app/models.py` · `backend/app/schemas/` · `migrations/` | Integrator only |

If you need a change in another pair's file, ask them. Do not edit it.

## Integration cadence

The integrator runs this every four hours from a clean clone:

```bash
git checkout main && git pull
docker compose down -v
docker compose up --build
# open http://localhost:5173 and click all six tabs
```

If it fails, **revert the last merge**. Do not debug on `main` while five people
are blocked. The pair fixes it on their branch and re-merges.

## Commits

`pair-a: seed rule_version with suvidha income ceiling`

Prefix with the pair. That is the whole convention.

## Hour 20: integration freeze

Everyone off fixtures, onto real endpoints. After hour 28, bug fixes only.
Verticals that integrate at hour 30 do not integrate.
