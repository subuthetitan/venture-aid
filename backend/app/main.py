"""
All six routers registered here on DAY ZERO.

Why this matters: router registration is the classic three-way merge conflict.
Register everything before the build starts and nobody touches this file again.
Same rule applies to frontend/src/App.jsx.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (calculate, ledger, locator, readiness, recommend,
                         truth)

app = FastAPI(title="PS 26092 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(recommend.router)   # Pair A
app.include_router(truth.router)       # Pair A
app.include_router(calculate.router)   # Pair B
app.include_router(readiness.router)   # Pair B
app.include_router(locator.router)     # Pair C
app.include_router(ledger.router)      # Pair C


@app.get("/health")
def health():
    return {"ok": True}
