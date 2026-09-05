"""PAIR B. Sanction-Ready: voice -> activity -> costed report -> PDF."""
import hashlib
import logging
import math
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from app.schemas import ProjectReport, ReadinessRequest
from app.services import finance, pdf_generator, transcription
from app.services.classification import UNRECOGNIZED, classify_activity
from app.services.cost_templates import (COST_TEMPLATES, capex_total,
                                         get_template, opex_total)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/readiness", tags=["readiness"])

# Generated PDFs land here and are served back by the download route below.
# Deliberately a plain local directory: this is an MVP demo, not durable
# storage, and nothing here survives a container rebuild. *.pdf is already
# gitignored. Serving through our own route avoids a StaticFiles mount in
# main.py, which is frozen and owned by the integrator.
PDF_DIR = Path(__file__).parent.parent / "generated"

# Reused verbatim from fixtures/report.json -- the existing list is reasonable
# and is not activity-specific, so it stays static for now.
# TODO(pair-b): make this per-activity (a dairy unit needs a cattle insurance
# doc a tailoring unit does not) once someone confirms the real SCA checklist.
DOCUMENT_CHECKLIST = [
    "Caste certificate",
    "Income certificate",
    "Residence proof",
    "Two machine quotations on letterhead",
    "Bank passbook first page",
    "Passport photographs (3)",
]


def _supported_activity_ids() -> list[str]:
    return sorted(t["id"] for t in COST_TEMPLATES)


@router.post("/transcribe")
def transcribe(audio: UploadFile = File(...), language: str = "hi"):
    """Bhashini primary (6s timeout) -> Sarvam Saaras -> cached fixture.

    Deliberately a sync endpoint: the provider calls are blocking httpx
    requests, so FastAPI runs this in a threadpool rather than tying up the
    event loop for up to 6 seconds per provider.

    The response contract is unchanged -- {"transcript", "provider"} -- because
    the frontend already renders the provider name.
    """
    result = transcription.transcribe(
        audio.file.read(),
        language=language,
        filename=audio.filename or "audio.wav",
        content_type=audio.content_type or "audio/wav",
    )
    return {"transcript": result.transcript, "provider": result.provider}


# Schemes restricted to women applicants. Mahila Samriddhi Yojana is NSFDC's
# micro-credit scheme for women ("mahila" = women); the restriction is inherent
# to the scheme's design, not something we inferred from a cost sheet.
# TODO(pair-b): confirm against the NSFDC scheme page alongside the SCHEME_TERMS
# source URLs, and check whether any other scheme in SCHEME_TERMS carries a
# restriction we have not encoded here.
WOMEN_ONLY_SCHEMES = frozenset({"nsfdc.mahila_samriddhi"})


def _is_eligible_scheme(scheme_id: str, gender: str | None) -> bool:
    """Gender eligibility gate.

    Fails CLOSED: when gender is unknown (None, blank, or anything other than
    an explicit female marker) a women-only scheme is excluded. Recommending a
    scheme the applicant cannot actually receive is the worse failure -- it
    sends someone to an SCA counter to be turned away.
    """
    if scheme_id not in WOMEN_ONLY_SCHEMES:
        return True
    # TODO(pair-b): the accepted markers are ours, not a validated enum. If the
    # frontend sends something else ('F', 'woman', a Hindi string), this gate
    # silently excludes the scheme. Align with whatever the intake form emits.
    return (gender or "").strip().casefold() in {"female", "f", "woman"}


def _pick_scheme(project_cost: int, gender: str | None = None) -> str:
    """Cheapest eligible scheme (lowest rate) whose ceiling covers the project.

    Rationale: the applicant's cost of capital is what we are minimising, and
    any scheme that covers the cost fully avoids a funding gap they would have
    to bridge themselves. If nothing covers it, fall back to the scheme with
    the highest ceiling -- finance.calculate() then caps the sanctionable
    amount, and the shortfall shows up as the gap between project cost and
    sanctionable_amount rather than being silently hidden.

    Gender-restricted schemes are filtered out first, so a male or
    unspecified-gender applicant is never routed to a women-only scheme.
    """
    terms = finance.SCHEME_TERMS
    eligible = [sid for sid in terms if _is_eligible_scheme(sid, gender)]
    covering = [sid for sid in eligible if terms[sid]["max_loan"] >= project_cost]
    if covering:
        return min(covering, key=lambda sid: terms[sid]["rate"])
    return max(eligible, key=lambda sid: terms[sid]["max_loan"])


def _break_even_months(project_cost: int, revenue: int, opex: int, emi: float) -> int:
    """Months of trading to earn back the project cost.

        monthly_surplus    = monthly_revenue - monthly_opex - emi
        break_even_months  = ceil(total_project_cost / monthly_surplus)

    JUDGMENT CALL, needs a finance-literate review before demo:
    this is deliberately CONSERVATIVE. Subtracting the EMI *and* dividing by
    the full project cost double-counts capital recovery, because the EMI is
    already repaying that same capital. The true payback on the applicant's
    own money at risk is shorter. We chose the pessimistic reading so the
    number on a bank submission is not one we have to walk back.

    Returns -1 when the unit does not generate a surplus at all -- the caller
    must not present that as a real break-even figure.
    """
    surplus = revenue - opex - emi
    if surplus <= 0:
        return -1
    return math.ceil(project_cost / surplus)


@router.post("", response_model=ProjectReport)
def generate(req: ReadinessRequest) -> ProjectReport:
    # ReadinessRequest carries BOTH activity_id and transcript, each optional.
    # An explicit activity_id is a user/operator choice, so it wins; the
    # transcript is only classified when no id was supplied.
    activity_id = req.activity_id or classify_activity(req.transcript or "", req.language)

    if activity_id == UNRECOGNIZED:
        raise HTTPException(
            status_code=422,
            detail={
                "error": UNRECOGNIZED,
                "message": (
                    "Could not identify a business activity from the transcript. "
                    "Ask the applicant which trade they plan to start, or pass "
                    "activity_id explicitly."
                ),
                "supported_activities": _supported_activity_ids(),
                "transcript": req.transcript,
            },
        )

    template = get_template(activity_id)
    if template is None:
        # Explicit activity_id that we have no cost sheet for. Never substitute
        # a different template -- a wrong cost sheet on a bank submission is
        # worse than no report.
        raise HTTPException(
            status_code=422,
            detail={
                "error": "NO_COST_TEMPLATE",
                "message": f"No cost template exists for activity_id '{activity_id}'.",
                "supported_activities": _supported_activity_ids(),
            },
        )

    # -- costs ---------------------------------------------------------------
    # NOTE: every figure behind these totals is an unsourced ESTIMATE. See the
    # module docstring in services/cost_templates.py before quoting them.
    capex_items = [
        {**item, "total": item["qty"] * item["unit_cost"]}
        for item in template["capex_items"]
    ]
    total_project_cost = capex_total(template)
    monthly_opex = opex_total(template)
    revenue = template["monthly_revenue_estimate"]

    # -- financing (delegated to the existing, tested engine) -----------------
    scheme_id = _pick_scheme(total_project_cost, req.profile.gender)
    fin = finance.calculate(scheme_id=scheme_id, project_cost=total_project_cost)

    break_even = _break_even_months(total_project_cost, revenue, monthly_opex, fin.emi)

    # -- narrative (templated, NOT generated) --------------------------------
    # Deterministic f-string. No LLM provider is wired into this repo and this
    # pass does not add one speculatively.
    capex_summary = ", ".join(
        f"{item['item']} x{item['qty']}" for item in template["capex_items"]
    )
    narrative = (
        f"{template['label_en']} set up with {capex_summary}. "
        f"Estimated project cost Rs {total_project_cost:,}, financed under "
        f"{scheme_id} at {fin.interest_rate}% over {fin.tenure_months} months "
        f"including a {fin.moratorium_months}-month moratorium, with a monthly "
        f"instalment of Rs {fin.emi:,.0f}. Estimated monthly revenue Rs "
        f"{revenue:,} against monthly operating cost Rs {monthly_opex:,}. "
        f"All cost figures are unverified estimates pending KVIC/NABARD sourcing."
    )

    report = ProjectReport(
        activity_id=activity_id,
        activity_label=template["label_en"],
        narrative=narrative,
        capex_items=capex_items,
        total_project_cost=total_project_cost,
        recommended_scheme_id=scheme_id,
        finance=fin,
        break_even_months=break_even,
        document_checklist=DOCUMENT_CHECKLIST,
        pdf_url=None,
    )
    report.pdf_url = _store_pdf(report, req.language)
    return report


def _report_key(report: ProjectReport, language: str) -> str:
    """Stable id derived from the report's content.

    Same inputs -> same filename, so repeated requests overwrite one file
    instead of filling the disk with near-identical PDFs. Content-derived
    rather than random so it stays deterministic, like the rest of Pair B.
    """
    basis = f"{report.activity_id}|{language}|{report.total_project_cost}|"             f"{report.recommended_scheme_id}|{report.finance.emi}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def _store_pdf(report: ProjectReport, language: str) -> str | None:
    """Render the report to a PDF on disk and return its download URL.

    Returns None -- leaving pdf_url null -- when PDF generation is unavailable
    or fails. The JSON report is the primary artefact and must still be
    returned; a missing font stack is not a reason to fail the whole request.
    """
    try:
        pdf_bytes = pdf_generator.generate_pdf(report, language)
    except pdf_generator.PdfUnavailable as exc:
        log.warning("PDF generation unavailable, returning report without pdf_url: %s", exc)
        return None
    except Exception:
        log.exception("PDF generation failed, returning report without pdf_url")
        return None

    key = _report_key(report, language)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    (PDF_DIR / f"{key}.pdf").write_bytes(pdf_bytes)
    return f"/api/readiness/pdf/{key}"


@router.get("/pdf/{key}")
def download_pdf(key: str) -> Response:
    """Serve a previously generated report PDF."""
    # Reject anything that is not a bare hex key so the path cannot escape
    # PDF_DIR (no '..', no separators).
    if not key or len(key) > 64 or any(c not in "0123456789abcdef" for c in key):
        raise HTTPException(status_code=404, detail="Not found")

    path = PDF_DIR / f"{key}.pdf"
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Report PDF not found. Generated PDFs do not survive a restart; "
                   "POST /api/readiness again to regenerate it.",
        )
    return Response(
        content=path.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="project-report-{key}.pdf"'},
    )
