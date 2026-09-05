"""
ALL tables for all three pairs, in ONE file, created by ONE migration on day zero.

Why: Alembic revision chains conflict badly when three pairs generate migrations
in parallel. Creating every table up front removes that entire class of merge
conflict. Do not add migrations during the build phase. If you need a column,
ask the integrator to add it to migration 0001 and everyone re-runs
`docker compose down -v && docker compose up`.

Ownership is marked per table.
"""
from datetime import date, datetime

from sqlalchemy import (JSON, BigInteger, Boolean, Date, DateTime, ForeignKey,
                        LargeBinary, Numeric, String, Text)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


# ---------------------------------------------------------------- PAIR A ----
class SourceSnapshot(Base):
    """Raw bytes of every page we read. Provenance means showing what you read."""
    __tablename__ = "source_snapshot"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int | None] = mapped_column(nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    raw_body: Mapped[bytes] = mapped_column(LargeBinary)


class Scheme(Base):
    __tablename__ = "scheme"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)   # 'nsfdc.suvidha'
    name: Mapped[str] = mapped_column(Text)
    corporation: Mapped[str] = mapped_column(String(32))            # 'NSFDC'
    status: Mapped[str] = mapped_column(String(16))                 # active | retired


class RuleVersion(Base):
    """
    APPEND ONLY. Never UPDATE a row.

    Supersession is scoped to (scheme_id, field, source_url): when the SAME page
    changes its value, stamp superseded_at on the old row.

    A CONTRADICTION is across source_url: two different official pages reporting
    different values both stay live. That is the Rs 3L / Rs 5L case and it is a
    normal state of the data, not an error.
    """
    __tablename__ = "rule_version"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scheme_id: Mapped[str] = mapped_column(ForeignKey("scheme.id"))
    field: Mapped[str] = mapped_column(String(64))                  # 'family_income_ceiling'
    value: Mapped[dict] = mapped_column(JSON)                       # {"amount": 500000}
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("source_snapshot.id"), nullable=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_authority: Mapped[str] = mapped_column(String(32))       # 'NSFDC' | 'MoSJE'
    extracted_by: Mapped[str] = mapped_column(String(48))           # 'human' | 'llm:sarvam-105b'
    extraction_confidence: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_human: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------- PAIR B ----
class CostTemplate(Base):
    """8-10 activities is enough for the MVP. Source: KVIC/NABARD model profiles."""
    __tablename__ = "cost_template"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)   # 'tailoring_unit'
    label_en: Mapped[str] = mapped_column(Text)
    label_local: Mapped[dict] = mapped_column(JSON)                 # {"hi": "...", "kn": "..."}
    capex_items: Mapped[list] = mapped_column(JSON)                 # [{"item","qty","unit_cost"}]
    monthly_opex: Mapped[list] = mapped_column(JSON)
    monthly_revenue_estimate: Mapped[int] = mapped_column()
    source_url: Mapped[str] = mapped_column(Text)


# ---------------------------------------------------------------- PAIR C ----
class Channel(Base):
    """SCA offices and empanelled branches. Geocoded once at seed time."""
    __tablename__ = "channel"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))                   # sca | bank | csc
    name: Mapped[str] = mapped_column(Text)
    state_code: Mapped[str] = mapped_column(String(8))
    district_code: Mapped[str] = mapped_column(String(8))           # LGD
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    lon: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)


class ApplicationMilestone(Base):
    """
    Transparency Ledger. Synthetic for the MVP - label it as such in the UI.
    No PII: application_ref is a salted hash.
    """
    __tablename__ = "application_milestone"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    application_ref: Mapped[str] = mapped_column(String(64))
    district_code: Mapped[str] = mapped_column(String(8))
    scheme_id: Mapped[str] = mapped_column(String(64))
    stage: Mapped[str] = mapped_column(String(32))
    occurred_on: Mapped[date] = mapped_column(Date)
    reported_by: Mapped[str] = mapped_column(String(16))            # operator | applicant
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
