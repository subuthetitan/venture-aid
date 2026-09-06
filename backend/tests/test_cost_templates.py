"""
PAIR B. Structural tests for the cost templates.

These check SHAPE and INTERNAL CONSISTENCY only. They deliberately do NOT
assert that any figure is correct, because no figure in cost_templates.py has
been checked against a real KVIC/NABARD source yet. A test that asserted
`unit_cost == 18000` would only be testing that we typed our own guess twice.
"""
from app.services.cost_templates import (COST_TEMPLATES, capex_total,
                                         get_template, opex_total)

EXPECTED_IDS = {
    "tailoring_unit", "dairy_unit", "kirana_store", "flour_mill",
    "beauty_parlour", "tea_stall", "photocopy_shop", "goat_rearing",
}


def test_all_eight_activities_are_present():
    assert {t["id"] for t in COST_TEMPLATES} == EXPECTED_IDS


def test_ids_are_unique():
    ids = [t["id"] for t in COST_TEMPLATES]
    assert len(ids) == len(set(ids))


def test_every_template_has_labels_in_english_hindi_and_kannada():
    for t in COST_TEMPLATES:
        assert t["label_en"].strip(), f"{t['id']} missing label_en"
        assert t["label_local"]["hi"].strip(), f"{t['id']} missing hi label"
        assert t["label_local"]["kn"].strip(), f"{t['id']} missing kn label"


def test_every_template_has_capex_items_with_the_right_shape():
    for t in COST_TEMPLATES:
        assert t["capex_items"], f"{t['id']} has no capex_items"
        assert 2 <= len(t["capex_items"]) <= 5, f"{t['id']} capex count out of range"
        for item in t["capex_items"]:
            assert set(item) == {"item", "qty", "unit_cost"}
            assert item["item"].strip()
            assert item["qty"] > 0
            assert item["unit_cost"] > 0


def test_every_template_has_opex_items_with_the_right_shape():
    for t in COST_TEMPLATES:
        assert t["monthly_opex"], f"{t['id']} has no monthly_opex"
        for item in t["monthly_opex"]:
            assert set(item) == {"item", "monthly_cost"}
            assert item["item"].strip()
            assert item["monthly_cost"] > 0


def test_capex_total_sums_qty_times_unit_cost():
    for t in COST_TEMPLATES:
        expected = sum(i["qty"] * i["unit_cost"] for i in t["capex_items"])
        assert capex_total(t) == expected


def test_opex_total_sums_monthly_costs():
    for t in COST_TEMPLATES:
        expected = sum(i["monthly_cost"] for i in t["monthly_opex"])
        assert opex_total(t) == expected


def test_every_unit_generates_an_operating_surplus():
    # Not a claim that the numbers are right -- only that our placeholders are
    # not internally absurd. A template whose opex exceeds its revenue would
    # produce a negative break-even and a nonsense report.
    for t in COST_TEMPLATES:
        assert t["monthly_revenue_estimate"] > opex_total(t), f"{t['id']} loses money"


def test_source_url_is_empty_rather_than_invented():
    # Load-bearing honesty check, same spirit as provenance='computed' in
    # finance.py. If someone fills these in, they must be REAL URLs -- this
    # test failing means either a real source was added (good, update this
    # test) or a plausible-looking URL was invented (bad, revert it).
    for t in COST_TEMPLATES:
        assert t["source_url"] == "", (
            f"{t['id']} has a source_url. Confirm it is a real, checkable "
            f"published document and not a plausible-looking guess."
        )


def test_get_template_returns_the_matching_template():
    t = get_template("tailoring_unit")
    assert t is not None
    assert t["id"] == "tailoring_unit"


def test_get_template_returns_none_for_unknown_id():
    # Must be None, never a fallback template.
    assert get_template("nonexistent_activity") is None
    assert get_template("") is None
