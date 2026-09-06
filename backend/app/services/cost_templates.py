"""
PAIR B. Cost templates for Sanction-Ready. Pure data + lookup, no DB, no LLM.

=============================================================================
READ THIS BEFORE QUOTING ANY NUMBER IN THIS FILE ON STAGE
=============================================================================
EVERY numeric figure below is an UNSOURCED ESTIMATE. Not one of them has been
checked against a published KVIC or NABARD model profile. They are placeholders
chosen to be the right order of magnitude so the pipeline can be demonstrated
end to end -- they are NOT verified costs.

`source_url` is deliberately the empty string on every template. An invented
URL is worse than a missing one: a fake citation gets repeated as fact. Fill
these in from real KVIC/NABARD model profiles before demo day, and correct the
figures to match whatever those documents actually say.

This is the opposite of the situation in finance.py: there, SCHEME_TERMS
carries real scheme parameters and the arithmetic is exact. Here, the
arithmetic is exact but the INPUTS are guesses. A Sanction-Ready report is
therefore only as trustworthy as this file, which today is: not very.

TODO(pair-b): replace all figures + source_url before demo. Owner: ______
=============================================================================

TRANSLATION CONFIDENCE
- Hindi (hi): commonly used trade terms, moderate confidence, still wants a
  native-speaker pass for register/spelling.
- Kannada (kn): LOW CONFIDENCE. Written from recall, not verified. Every kn
  string below needs a native Kannada speaker to review before it is shown to
  a user. Flagged individually as KN-REVIEW.
"""

# Shape mirrors models.CostTemplate so this can move to a DB seed unchanged:
#   id, label_en, label_local, capex_items, monthly_opex,
#   monthly_revenue_estimate, source_url
#
# capex_items:  [{"item": str, "qty": int, "unit_cost": int}]
# monthly_opex: [{"item": str, "monthly_cost": int}]

_ESTIMATE = ""  # every source_url: intentionally empty, see module docstring

COST_TEMPLATES: list[dict] = [
    {
        "id": "tailoring_unit",
        "label_en": "Tailoring unit (2 machines)",
        "label_local": {
            "hi": "सिलाई इकाई (2 मशीन)",
            "kn": "ಹೊಲಿಗೆ ಘಟಕ (2 ಯಂತ್ರಗಳು)",  # KN-REVIEW
        },
        "capex_items": [
            {"item": "Sewing machine (motorised)", "qty": 2, "unit_cost": 18000},   # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Overlock machine", "qty": 1, "unit_cost": 22000},             # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Cutting table and furniture", "qty": 1, "unit_cost": 12000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Initial fabric and accessories", "qty": 1, "unit_cost": 15000},  # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_opex": [
            {"item": "Raw material (fabric, thread)", "monthly_cost": 8000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Shop rent", "monthly_cost": 3000},                      # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Power and sundries", "monthly_cost": 1000},             # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_revenue_estimate": 25000,  # ESTIMATE - needs real KVIC/NABARD source before demo
        "source_url": _ESTIMATE,
    },
    {
        "id": "dairy_unit",
        "label_en": "Dairy unit (2 buffaloes)",
        "label_local": {
            "hi": "डेयरी इकाई (2 भैंस)",
            "kn": "ಹೈನುಗಾರಿಕೆ ಘಟಕ (2 ಎಮ್ಮೆಗಳು)",  # KN-REVIEW
        },
        "capex_items": [
            {"item": "Milch buffalo", "qty": 2, "unit_cost": 70000},          # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Shed construction", "qty": 1, "unit_cost": 40000},      # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Chaff cutter and utensils", "qty": 1, "unit_cost": 18000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Initial feed stock", "qty": 1, "unit_cost": 12000},     # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_opex": [
            {"item": "Green and dry fodder", "monthly_cost": 9000},   # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Concentrate feed", "monthly_cost": 4000},       # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Veterinary and insurance", "monthly_cost": 1200},  # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_revenue_estimate": 30000,  # ESTIMATE - needs real KVIC/NABARD source before demo
        "source_url": _ESTIMATE,
    },
    {
        "id": "kirana_store",
        "label_en": "Kirana (grocery) store",
        "label_local": {
            "hi": "किराना दुकान",
            "kn": "ಕಿರಾಣಿ ಅಂಗಡಿ",  # KN-REVIEW
        },
        "capex_items": [
            {"item": "Opening stock", "qty": 1, "unit_cost": 60000},          # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Shelving and counter", "qty": 1, "unit_cost": 25000},   # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Weighing scale (electronic)", "qty": 1, "unit_cost": 6000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Refrigerator (small)", "qty": 1, "unit_cost": 18000},   # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_opex": [
            {"item": "Stock replenishment", "monthly_cost": 35000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Shop rent", "monthly_cost": 4000},             # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Power and sundries", "monthly_cost": 1500},    # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_revenue_estimate": 52000,  # ESTIMATE - needs real KVIC/NABARD source before demo
        "source_url": _ESTIMATE,
    },
    {
        "id": "flour_mill",
        "label_en": "Flour mill (atta chakki)",
        "label_local": {
            "hi": "आटा चक्की",
            "kn": "ಹಿಟ್ಟಿನ ಗಿರಣಿ",  # KN-REVIEW
        },
        "capex_items": [
            {"item": "Flour mill machine with motor", "qty": 1, "unit_cost": 55000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Electrical fitting and starter", "qty": 1, "unit_cost": 12000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Platform and civil work", "qty": 1, "unit_cost": 15000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Weighing scale and drums", "qty": 1, "unit_cost": 8000},  # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_opex": [
            {"item": "Electricity", "monthly_cost": 4500},         # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Maintenance and spares", "monthly_cost": 1500},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Shop rent", "monthly_cost": 3000},           # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_revenue_estimate": 22000,  # ESTIMATE - needs real KVIC/NABARD source before demo
        "source_url": _ESTIMATE,
    },
    {
        "id": "beauty_parlour",
        "label_en": "Beauty parlour",
        "label_local": {
            "hi": "ब्यूटी पार्लर",
            "kn": "ಬ್ಯೂಟಿ ಪಾರ್ಲರ್",  # KN-REVIEW
        },
        "capex_items": [
            {"item": "Parlour chair and mirror station", "qty": 2, "unit_cost": 14000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Steamer, dryer, styling equipment", "qty": 1, "unit_cost": 25000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Interior and lighting", "qty": 1, "unit_cost": 20000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Initial consumables stock", "qty": 1, "unit_cost": 12000},  # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_opex": [
            {"item": "Consumables (cosmetics)", "monthly_cost": 7000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Shop rent", "monthly_cost": 6000},                # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Power and water", "monthly_cost": 1500},          # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_revenue_estimate": 28000,  # ESTIMATE - needs real KVIC/NABARD source before demo
        "source_url": _ESTIMATE,
    },
    {
        "id": "tea_stall",
        "label_en": "Tea stall",
        "label_local": {
            "hi": "चाय की दुकान",
            "kn": "ಟೀ ಅಂಗಡಿ",  # KN-REVIEW
        },
        "capex_items": [
            {"item": "Stall structure / cart", "qty": 1, "unit_cost": 25000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Gas stove, cylinder, utensils", "qty": 1, "unit_cost": 12000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Refrigerator (small)", "qty": 1, "unit_cost": 15000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Seating and initial stock", "qty": 1, "unit_cost": 8000},  # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_opex": [
            {"item": "Milk, tea, snacks stock", "monthly_cost": 14000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Gas refill", "monthly_cost": 2000},                # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Pitch rent and sundries", "monthly_cost": 2500},   # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_revenue_estimate": 26000,  # ESTIMATE - needs real KVIC/NABARD source before demo
        "source_url": _ESTIMATE,
    },
    {
        "id": "photocopy_shop",
        "label_en": "Photocopy and stationery shop",
        "label_local": {
            "hi": "फोटोकॉपी और स्टेशनरी की दुकान",
            "kn": "ಫೋಟೋಕಾಪಿ ಮತ್ತು ಲೇಖನ ಸಾಮಗ್ರಿ ಅಂಗಡಿ",  # KN-REVIEW
        },
        "capex_items": [
            {"item": "Photocopier machine", "qty": 1, "unit_cost": 60000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Computer and printer", "qty": 1, "unit_cost": 35000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Furniture and shelving", "qty": 1, "unit_cost": 12000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Initial stationery stock", "qty": 1, "unit_cost": 10000},  # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_opex": [
            {"item": "Paper, toner, cartridges", "monthly_cost": 9000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Shop rent", "monthly_cost": 4500},                 # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Power and internet", "monthly_cost": 2000},        # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_revenue_estimate": 24000,  # ESTIMATE - needs real KVIC/NABARD source before demo
        "source_url": _ESTIMATE,
    },
    {
        "id": "goat_rearing",
        "label_en": "Goat rearing (10+1 unit)",
        "label_local": {
            "hi": "बकरी पालन (10+1 इकाई)",
            "kn": "ಮೇಕೆ ಸಾಕಾಣಿಕೆ (10+1 ಘಟಕ)",  # KN-REVIEW
        },
        "capex_items": [
            {"item": "Female goats", "qty": 10, "unit_cost": 7000},   # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Breeding buck", "qty": 1, "unit_cost": 10000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Shed and fencing", "qty": 1, "unit_cost": 35000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Feed and equipment (initial)", "qty": 1, "unit_cost": 10000},  # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_opex": [
            {"item": "Feed and fodder", "monthly_cost": 6000},        # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Veterinary and vaccination", "monthly_cost": 1000},  # ESTIMATE - needs real KVIC/NABARD source before demo
            {"item": "Labour and sundries", "monthly_cost": 2000},    # ESTIMATE - needs real KVIC/NABARD source before demo
        ],
        "monthly_revenue_estimate": 18000,  # ESTIMATE - needs real KVIC/NABARD source before demo
        "source_url": _ESTIMATE,
    },
]

_BY_ID: dict[str, dict] = {t["id"]: t for t in COST_TEMPLATES}


def get_template(activity_id: str) -> dict | None:
    """Look up one template by id. Returns None when the id is unknown.

    Callers must handle None explicitly -- never fall back to an arbitrary
    template. A wrong cost sheet on a bank submission is worse than no report.
    """
    return _BY_ID.get(activity_id)


def capex_total(template: dict) -> int:
    """Sum of qty * unit_cost across capex_items. Integer rupees."""
    return sum(item["qty"] * item["unit_cost"] for item in template["capex_items"])


def opex_total(template: dict) -> int:
    """Sum of monthly_cost across monthly_opex. Integer rupees per month."""
    return sum(item["monthly_cost"] for item in template["monthly_opex"])
