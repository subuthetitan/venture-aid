"""
PAIR B. Deterministic keyword activity classifier. No LLM, no network.

Same reasoning as finance.py: this has to be defensible on stage as COMPUTED,
not generated. A keyword table is auditable -- you can point at the exact line
that produced a match. A model call is not.

Matching is deliberately dumb:
  - case-folded substring match against a per-activity keyword list
  - the activity with the most distinct keyword hits wins
  - ties are broken by the order activities appear in _KEYWORDS (stable, so
    the classifier is fully deterministic for a given input)
  - zero hits returns UNRECOGNIZED, never a guess

=============================================================================
KEYWORD COVERAGE IS NOT VERIFIED
=============================================================================
Hindi terms: moderate confidence, common trade words. Wants a native-speaker
pass for spelling variants and regional synonyms.

Kannada terms: LOW CONFIDENCE, written from recall. Every Kannada keyword
below needs a native speaker to confirm before we rely on it. They are marked
KN-REVIEW. If a Kannada string here is misspelled the failure is SILENT -- it
simply never matches, and the user falls through to UNRECOGNIZED. That is the
safe direction to fail, but it still means Kannada coverage may be far worse
in practice than this table makes it look.

We also do no transliteration (Romanised Hindi like "silai" is handled only
where explicitly listed) and no stemming or fuzzy matching. Real transcripts
from an ASR system will contain spellings this table does not have.

TODO(pair-b): native-speaker review of hi + kn keywords before demo day.
=============================================================================
"""

UNRECOGNIZED = "UNRECOGNIZED_ACTIVITY"

# activity_id -> keywords. Keys must match ids in cost_templates.COST_TEMPLATES.
# Order matters: it is the tie-break order when two activities score equally.
_KEYWORDS: dict[str, list[str]] = {
    "tailoring_unit": [
        # en
        "tailoring", "tailor", "stitching", "stitch", "sewing", "boutique",
        # hi
        "सिलाई", "सिलने", "दर्जी", "टेलरिंग", "कपड़े सिलना",
        # romanised hi
        "silai", "darzi",
        # kn  # KN-REVIEW
        "ಹೊಲಿಗೆ", "ಟೈಲರಿಂಗ್", "ದರ್ಜಿ",
    ],
    "dairy_unit": [
        # en
        "dairy", "milk", "buffalo", "cow", "milch", "cattle",
        # hi
        "डेयरी", "दूध", "भैंस", "गाय", "पशुपालन",
        # romanised hi
        "doodh", "bhains",
        # kn  # KN-REVIEW
        "ಹೈನುಗಾರಿಕೆ", "ಹಾಲು", "ಎಮ್ಮೆ", "ಹಸು",
    ],
    "kirana_store": [
        # en
        "kirana", "grocery", "provision store", "general store", "grocer",
        # hi
        "किराना", "परचून", "राशन की दुकान", "जनरल स्टोर",
        # kn  # KN-REVIEW
        "ಕಿರಾಣಿ", "ದಿನಸಿ", "ಅಂಗಡಿ",
    ],
    "flour_mill": [
        # en
        "flour mill", "flour", "atta chakki", "chakki", "grinding", "grain mill",
        # hi
        "आटा चक्की", "चक्की", "आटा", "पिसाई",
        # kn  # KN-REVIEW
        "ಹಿಟ್ಟಿನ ಗಿರಣಿ", "ಗಿರಣಿ", "ಹಿಟ್ಟು",
    ],
    "beauty_parlour": [
        # en
        "beauty parlour", "beauty parlor", "beautician", "salon", "parlour",
        "parlor", "makeup",
        # hi
        "ब्यूटी पार्लर", "पार्लर", "सौंदर्य", "मेकअप",
        # kn  # KN-REVIEW
        "ಬ್ಯೂಟಿ ಪಾರ್ಲರ್", "ಪಾರ್ಲರ್", "ಸೌಂದರ್ಯ",
    ],
    "tea_stall": [
        # en
        "tea stall", "tea shop", "chai", "canteen", "snack stall", "tea",
        # hi
        "चाय", "चाय की दुकान", "चाय का ठेला", "नाश्ता",
        # kn  # KN-REVIEW
        "ಟೀ ಅಂಗಡಿ", "ಚಹಾ", "ಟೀ",
    ],
    "photocopy_shop": [
        # en
        "photocopy", "xerox", "stationery", "printing", "print shop",
        "browsing centre", "browsing center",
        # hi
        "फोटोकॉपी", "जेरॉक्स", "स्टेशनरी", "छपाई", "प्रिंटिंग",
        # kn  # KN-REVIEW
        "ಫೋಟೋಕಾಪಿ", "ಜೆರಾಕ್ಸ್", "ಮುದ್ರಣ",
    ],
    "goat_rearing": [
        # en
        "goat", "goatery", "goat rearing", "sheep", "livestock rearing",
        # hi
        "बकरी", "बकरी पालन", "भेड़",
        # romanised hi
        "bakri",
        # kn  # KN-REVIEW
        "ಮೇಕೆ", "ಆಡು", "ಕುರಿ",
    ],
}


def _score(transcript: str) -> dict[str, int]:
    """Distinct keyword hits per activity. Case-folded substring matching."""
    text = transcript.casefold()
    return {
        activity_id: sum(1 for kw in keywords if kw.casefold() in text)
        for activity_id, keywords in _KEYWORDS.items()
    }


def classify_activity(transcript: str, language: str = "hi") -> str:
    """Return an activity_id, or UNRECOGNIZED_ACTIVITY when nothing matches.

    `language` is accepted to match the ReadinessRequest shape but is NOT used
    to filter keywords: transcripts routinely mix scripts (Hindi speech with
    English trade names), so every language's keywords are always live. Kept in
    the signature so the caller does not have to special-case it.

    Never guesses. An unrecognised transcript must surface to the user, because
    the downstream artefact is a costed report submitted to a bank.
    """
    if not transcript or not transcript.strip():
        return UNRECOGNIZED

    scores = _score(transcript)
    best = max(scores, key=lambda a: scores[a])  # dict order breaks ties
    return best if scores[best] > 0 else UNRECOGNIZED
