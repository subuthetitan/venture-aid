"""
PAIR B. ProjectReport -> PDF bytes. Jinja2 for markup, WeasyPrint for print.

Pure function: no disk writes, no network, no LLM. The caller decides where
the bytes go.

RUNTIME DEPENDENCY: WeasyPrint binds to native Pango / Cairo / GDK-Pixbuf
libraries. Importing it on a machine without them raises OSError at IMPORT
time, not at call time, which would take the whole API down on startup. So the
import here is deferred into generate_pdf() and surfaced as a clear
PdfUnavailable error -- a missing font stack must not stop /api/readiness from
returning its JSON.

The template's own header carries the format disclaimer; see
app/templates/project_report.html.
"""
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas import ProjectReport

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
TEMPLATE_NAME = "project_report.html"


class PdfUnavailable(RuntimeError):
    """WeasyPrint's native dependencies are not available on this machine."""


def _rupees(value) -> str:
    """Thousands-separated amount. Western grouping, matching finance.py.

    TODO(pair-b): Indian grouping (1,25,000) reads more naturally for this
    audience. Deliberately NOT done here so the PDF and the JSON/API show the
    same formatting; change both together or neither.
    """
    if value is None:
        return "-"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["rupees"] = _rupees
    return env


def _titles(report: ProjectReport, language: str) -> tuple[str, str]:
    """(title, subtitle) for the report header.

    ProjectReport carries only activity_label (English), so the localised name
    is looked up from the cost template by activity_id. When a local label
    exists we lead with it and keep the English name as the subtitle, so the
    applicant reads their own language first and a bank officer still gets the
    English name on the same page.
    """
    local = None
    if language and language != "en":
        from app.services.cost_templates import get_template
        template = get_template(report.activity_id)
        if template:
            local = (template.get("label_local") or {}).get(language)
    if local:
        return local, report.activity_label
    return report.activity_label, ""


def render_html(report: ProjectReport, language: str = "en") -> str:
    """Template -> HTML string. Split out so tests can inspect markup without
    needing WeasyPrint's native stack installed."""
    title, subtitle = _titles(report, language)
    return _environment().get_template(TEMPLATE_NAME).render(
        report=report,
        activity_title=title,
        activity_subtitle=subtitle,
        generated_on=date.today().isoformat(),
        language=language,
    )


def pdf_available() -> bool:
    """True when WeasyPrint can actually be imported on this machine."""
    try:
        import weasyprint  # noqa: F401
    except Exception:
        return False
    return True


def generate_pdf(report: ProjectReport, language: str = "en") -> bytes:
    """Render a ProjectReport to PDF bytes.

    `language` is optional so the documented one-argument call form still
    works; it only selects which localised activity label heads the document.

    Raises PdfUnavailable when the native Pango/Cairo stack is missing.
    """
    try:
        from weasyprint import HTML
    except Exception as exc:  # OSError from the native loader, typically
        raise PdfUnavailable(
            "WeasyPrint could not load its native dependencies "
            f"({type(exc).__name__}: {exc}). On Debian/Ubuntu these are "
            "libpango-1.0-0, libpangoft2-1.0-0, libcairo2, libgdk-pixbuf-2.0-0."
        ) from exc

    html = render_html(report, language)
    # base_url lets the template reference files next to it if it ever needs to.
    # It does not fetch anything over the network today, and must not start to.
    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()
