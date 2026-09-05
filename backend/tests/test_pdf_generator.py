"""
PAIR B. PDF generation tests, including the Devanagari conjunct check.

The conjunct tests are the point of this file. Devanagari conjuncts (क्ष, ज्ञ,
स्वास्थ्य) are where a text stack usually breaks: the shaping engine has to
combine consonants across a virama into a single ligature. If that fails the
PDF shows broken or reordered glyphs, and a report in Hindi is unusable.

These tests SKIP rather than fail when WeasyPrint's native Pango/Cairo stack
is missing, because that is an environment gap, not a code defect. A skip here
means the conjunct question is UNANSWERED on this machine -- not that it
passed. Read the skip reason before believing Devanagari works.
"""
import pytest

from app.schemas import CalculateResponse, ProjectReport
from app.services import finance
from app.services.pdf_generator import (PdfUnavailable, generate_pdf,
                                        pdf_available, render_html)

# Genuine conjuncts, not just multi-byte characters:
#   क्ष = क + ् + ष     ज्ञ = ज + ् + ञ     स्वास्थ्य contains स् + व and स् + थ्
#
# The fourth entry is different in kind from the first three and is here on
# purpose. The first three are virama stacks -- they exercise CONJUNCT FORMATION
# only, and contain no pre-base matra at all. कृषि प्रसंस्करण इकाई is the string
# docs/ARCHITECTURE.md:229 names for this check, and it additionally contains:
#   * कृ  = क + ृ  (DEVANAGARI VOWEL SIGN VOCALIC R, an attached below-base matra)
#   * षि = ष + ि  (VOWEL SIGN I -- typed AFTER its consonant, drawn BEFORE it:
#                   the pre-base reordering case none of the other three reach)
#   * सं  anusvara, and प्र / स्क virama stacks
# ARCHITECTURE.md:225 gives "conjunct formation, matra reordering" as the two
# reasons WeasyPrint was chosen over ReportLab; entries 1-3 only cover the first.
#
# NOTE ON WHAT THIS BUYS: the assertion below is a codepoint round trip through
# pdfplumber, for every entry in this list including the fourth. It proves the
# text layer survives. It does NOT verify glyph position, and therefore does NOT
# prove that matra reordering actually happened -- a PDF that drew ि on the wrong
# side of ष would still extract the correct codepoints and still pass. A real
# shaping guarantee needs golden-image comparison, which this suite does not do.
# The fourth string widens string coverage and would catch a font that dropped
# these codepoints entirely; it does not upgrade the guarantee.
CONJUNCTS = ["क्ष", "ज्ञ", "स्वास्थ्य", "कृषि प्रसंस्करण इकाई"]

requires_weasyprint = pytest.mark.skipif(
    not pdf_available(),
    reason="WeasyPrint native deps (Pango/Cairo/GDK-Pixbuf) unavailable here; "
           "Devanagari rendering is UNVERIFIED on this machine.",
)


def _sample_report(narrative: str = "A two-machine tailoring unit.") -> ProjectReport:
    fin = finance.calculate("nsfdc.micro_credit", project_cost=85000)
    return ProjectReport(
        activity_id="tailoring_unit",
        activity_label="Tailoring unit (2 machines)",
        narrative=narrative,
        capex_items=[
            {"item": "Sewing machine (motorised)", "qty": 2, "unit_cost": 18000, "total": 36000},
            {"item": "Overlock machine", "qty": 1, "unit_cost": 22000, "total": 22000},
        ],
        total_project_cost=85000,
        recommended_scheme_id="nsfdc.micro_credit",
        finance=fin,
        break_even_months=9,
        document_checklist=["Caste certificate", "Income certificate"],
        pdf_url=None,
    )


# ------------------------------------------------------ HTML (no native deps) --
def test_html_contains_the_key_report_sections():
    html = render_html(_sample_report())
    for expected in ["Tailoring unit (2 machines)", "Sewing machine (motorised)",
                     "Capital expenditure", "Document checklist",
                     "nsfdc.micro_credit", "Caste certificate"]:
        assert expected in html


def test_html_carries_the_estimate_caveat_into_the_document():
    # The same honesty flag as the JSON response. A bank officer reading only
    # the PDF must see it too.
    html = render_html(_sample_report())
    assert "unverified estimates" in html
    assert "KVIC" in html


def test_html_does_not_claim_to_match_an_official_format():
    html = render_html(_sample_report())
    assert "Not verified against the" in html
    # Must never assert conformance to a real government format.
    assert "matches the PMEGP" not in html
    assert "official format" not in html


def test_html_preserves_devanagari_conjuncts_before_rendering():
    # Cheap guard that autoescaping/templating does not mangle the text on the
    # way in. Says nothing about glyph shaping -- that needs a real render.
    html = render_html(_sample_report(narrative="स्वास्थ्य और शिक्षा"))
    assert "स्वास्थ्य" in html


def test_localised_title_is_used_for_hindi():
    html = render_html(_sample_report(), language="hi")
    assert "सिलाई" in html


# ------------------------------------------------------- PDF (native deps) --
@requires_weasyprint
def test_generate_pdf_returns_valid_pdf_bytes():
    pdf = generate_pdf(_sample_report())
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
    assert pdf.startswith(b"%PDF-")
    assert b"%%EOF" in pdf[-2048:]


@requires_weasyprint
def test_pdf_text_can_be_read_back():
    import io

    import pdfplumber

    pdf = generate_pdf(_sample_report())
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
    assert "Tailoring unit (2 machines)" in text
    assert "Sewing machine (motorised)" in text
    assert "unverified estimates" in text


@requires_weasyprint
@pytest.mark.parametrize("conjunct", CONJUNCTS)
def test_devanagari_conjunct_survives_end_to_end(conjunct):
    """THE conjunct test, through the real generate_pdf(), not a side script.

    Extracts text back out of the rendered PDF and asserts the conjunct
    survived as the same codepoint sequence. Caveat: this proves the text
    layer is intact. It does NOT prove the glyphs are visually correct -- a
    font can emit a .notdef box while keeping the underlying text. Visual
    confirmation needs a human looking at the rasterised page.

    Whitespace is normalised out of both sides before comparing. Reason,
    measured rather than assumed: the first three entries match exactly, but
    the fourth (the ARCHITECTURE.md:229 string) extracts with a spurious
    double space at the KA+vocalic-R | SHA+i boundary -- every codepoint
    present and in correct logical order, just with extra whitespace. That
    boundary is exactly where the pre-base matra is physically drawn to the
    LEFT of its consonant, which disrupts pdfplumber's position-based
    reconstruction of reading order. It is an artefact of text EXTRACTION
    from a complex script, not of rendering: the rasterised page was
    inspected by a human and the matra sits correctly before its consonant.

    Normalising whitespace therefore costs this test nothing it was actually
    measuring -- it never asserted anything about spacing -- and is what lets
    a pre-base-matra string be checked at all. It still says nothing
    whatsoever about glyph position.
    """
    import io

    import pdfplumber

    pdf = generate_pdf(_sample_report(narrative=f"परीक्षण {conjunct} पाठ"))
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        text = "\n".join(page.extract_text() or "" for page in doc.pages)
    squashed = "".join(text.split())
    expected = "".join(conjunct.split())
    assert expected in squashed, (
        f"Conjunct {conjunct!r} did not survive the round trip. "
        f"Extracted text was: {text[:400]!r}"
    )


@requires_weasyprint
def test_mixed_script_document_renders():
    # English + Devanagari + Kannada in one document must not break layout or
    # error out.
    pdf = generate_pdf(_sample_report(
        narrative="Tailoring unit. सिलाई इकाई. ಹೊಲಿಗೆ ಘಟಕ."))
    assert pdf.startswith(b"%PDF-")


# --------------------------------------------------- unavailable-deps path --
def test_pdf_unavailable_is_raised_not_swallowed_when_deps_missing():
    # Documents the contract the router relies on: a missing native stack
    # surfaces as PdfUnavailable, which generate() catches to leave pdf_url
    # null rather than failing the whole report.
    if pdf_available():
        pytest.skip("WeasyPrint is available here; nothing to assert.")
    with pytest.raises(PdfUnavailable):
        generate_pdf(_sample_report())


# ---------------------------------------------- hardening pass edge cases --
def test_report_with_no_capex_items_still_renders():
    # Degenerate but well-formed: the table should collapse to just the total
    # row rather than raising.
    report = _sample_report()
    report.capex_items = []
    report.total_project_cost = 0
    html = render_html(report)
    assert "Total project cost" in html
    assert "Capital expenditure" in html


def test_missing_template_directory_raises_rather_than_rendering_a_blank():
    # The router catches this and leaves pdf_url null. What must NOT happen is
    # a silently empty document going out as a bank submission.
    from pathlib import Path

    from jinja2 import TemplateNotFound

    from app.services import pdf_generator as pg

    original = pg.TEMPLATE_DIR
    pg.TEMPLATE_DIR = Path("/nonexistent/templates")
    try:
        with pytest.raises(TemplateNotFound):
            render_html(_sample_report())
    finally:
        pg.TEMPLATE_DIR = original


# ------------------------------------------- required review label (FMT-03) --
REVIEW_LABEL_PHRASES = ["first draft for human review", "not an approval"]


def test_html_carries_the_first_draft_for_human_review_label():
    """docs/ARCHITECTURE.md:235 requires the output be labelled 'first draft for
    human review', not an approval. The mirror of
    test_html_does_not_claim_to_match_an_official_format: that one asserts an
    absence, this one asserts a presence."""
    html = render_html(_sample_report()).lower()
    for phrase in REVIEW_LABEL_PHRASES:
        assert phrase in html, f"required review label missing: {phrase!r}"


def test_review_label_is_prominent_not_buried_in_the_fine_print():
    """It must not be tucked into the existing amber estimates caveat. Assert it
    appears before section 1, i.e. above the body of the report."""
    html = render_html(_sample_report())
    label_at = html.lower().index("first draft for human review")
    summary_at = html.index("1. Summary")
    assert label_at < summary_at, "review label appears below the report body"
    assert "draft-banner" in html, "review label is not using the prominent banner style"


@requires_weasyprint
def test_review_label_survives_into_the_rendered_pdf_text():
    """Present in the HTML is not enough -- it has to reach the actual PDF."""
    import io

    import pdfplumber

    pdf = generate_pdf(_sample_report())
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        pages = [(page.extract_text() or "").lower() for page in doc.pages]
    text = "\n".join(pages)
    for phrase in REVIEW_LABEL_PHRASES:
        assert phrase in text, f"required review label missing from rendered PDF: {phrase!r}"
    # The running footer repeats it, so it must appear on every page -- a reader
    # holding only page 2 still sees that this is a draft.
    for i, page_text in enumerate(pages, 1):
        assert "first draft for human review" in page_text, f"label missing from page {i}"
