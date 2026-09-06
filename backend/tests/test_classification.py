"""
PAIR B. Classifier tests. Deterministic in, deterministic out.

Note on language coverage: the English and Hindi cases below are ones we are
reasonably confident in. The Kannada cases test the keywords AS WRITTEN in
classification.py -- they will pass whether or not the Kannada spelling is
correct, because the test and the source share the same string. They prove the
matching machinery works for Kannada input; they do NOT prove our Kannada is
right. Only a native speaker can do that.
"""
import pytest

from app.services.classification import UNRECOGNIZED, classify_activity


# -------------------------------------------------- one clear match each --
@pytest.mark.parametrize("transcript,expected", [
    ("I want to start a tailoring business", "tailoring_unit"),
    ("planning to open a dairy with two buffaloes", "dairy_unit"),
    ("I want to run a kirana store in my village", "kirana_store"),
    ("thinking of setting up a flour mill", "flour_mill"),
    ("I want to open a beauty parlour", "beauty_parlour"),
    ("planning a tea stall near the bus stand", "tea_stall"),
    ("want to start a photocopy and stationery shop", "photocopy_shop"),
    ("I would like to do goat rearing", "goat_rearing"),
])
def test_english_clear_match(transcript, expected):
    assert classify_activity(transcript, "en") == expected


@pytest.mark.parametrize("transcript,expected", [
    ("मुझे सिलाई का काम शुरू करना है", "tailoring_unit"),
    ("मैं डेयरी का काम करना चाहता हूँ", "dairy_unit"),
    ("मुझे किराना दुकान खोलनी है", "kirana_store"),
    ("आटा चक्की लगाना चाहता हूँ", "flour_mill"),
    ("मुझे ब्यूटी पार्लर खोलना है", "beauty_parlour"),
    ("चाय की दुकान शुरू करनी है", "tea_stall"),
    ("फोटोकॉपी की दुकान खोलनी है", "photocopy_shop"),
    ("बकरी पालन करना चाहता हूँ", "goat_rearing"),
])
def test_hindi_clear_match(transcript, expected):
    assert classify_activity(transcript, "hi") == expected


# ------------------------------------------------------------- fallback --
def test_unrelated_text_is_unrecognized():
    # Must NOT guess. Silently picking a template here would put a wrong cost
    # sheet in front of a bank.
    assert classify_activity("I want to buy a motorcycle", "en") == UNRECOGNIZED


def test_empty_and_whitespace_transcripts_are_unrecognized():
    assert classify_activity("", "hi") == UNRECOGNIZED
    assert classify_activity("   \n  ", "hi") == UNRECOGNIZED


# ------------------------------------------------------- mixed language --
def test_mixed_script_transcript_matches():
    # Hindi sentence frame with an English trade word -- the common real-world
    # ASR output. Confirms we do not filter keywords by the `language` param.
    assert classify_activity("मुझे tailoring का काम करना है", "hi") == "tailoring_unit"


def test_language_param_does_not_restrict_matching():
    # Same English transcript classified while claiming Kannada: keywords from
    # all languages stay live, so the result must be identical.
    assert classify_activity("I want to open a tea stall", "kn") == "tea_stall"


# ------------------------------------------------------------ mechanics --
def test_matching_is_case_insensitive():
    assert classify_activity("TAILORING UNIT", "en") == "tailoring_unit"


def test_classification_is_deterministic():
    text = "I want to start a dairy and also some tailoring"
    assert len({classify_activity(text, "en") for _ in range(20)}) == 1


def test_more_keyword_hits_wins():
    # 'goat' + 'goat rearing' outscores a single passing mention of tea.
    assert classify_activity(
        "goat rearing, ten goats, maybe tea later", "en"
    ) == "goat_rearing"


# ---------------------------------------------- hardening pass edge cases --
def test_all_absent_transcript_forms_behave_identically():
    # The router calls classify_activity(req.transcript or "", ...), but the
    # function must be safe if handed None directly too. All three forms are
    # the same user situation: nothing was said.
    assert classify_activity("", "hi") == UNRECOGNIZED
    assert classify_activity("   \t\n  ", "hi") == UNRECOGNIZED
    assert classify_activity(None, "hi") == UNRECOGNIZED


# ------------------------------------------------- bug-fix regression pass --
@pytest.mark.parametrize("transcript", [
    # 'chai' inside 'chairs'
    "I want to sell chairs in my shop",
    # 'tea' inside 'instead'
    "Please tell me instead what to do",
    # 'tea' inside 'steam'
    "I want to open a steam laundry",
    # 'cow' inside 'cowardly'; 'tea' inside 'team'
    "our team is not cowardly about this",
])
def test_latin_keywords_do_not_match_inside_other_words(transcript):
    """REGRESSION: substring matching classified unrelated text as a tea stall.

    Every string above returned tea_stall before the word-boundary fix. The
    downstream artefact is a costed project report submitted to a bank, so a
    confident wrong classification is worse than UNRECOGNIZED.
    """
    assert classify_activity(transcript, "en") == UNRECOGNIZED


@pytest.mark.parametrize("transcript,expected", [
    ("I want to rear goats", "goat_rearing"),
    ("I want to buy two buffaloes", "dairy_unit"),
    ("we will need sewing machines", "tailoring_unit"),
    ("thinking about beauty parlours", "beauty_parlour"),
])
def test_word_boundaries_still_allow_plurals(transcript, expected):
    """The boundary rule allows a trailing -s / -es, so the fix does not trade
    false positives for missed real matches."""
    assert classify_activity(transcript, "en") == expected


def test_non_latin_keywords_still_match_agglutinated_forms():
    # Devanagari attaches case markers to the noun, so those keywords stay on
    # substring matching. A boundary rule would break these.
    assert classify_activity("सिलाईका काम", "hi") == "tailoring_unit"
    assert classify_activity("बकरीपालन शुरू करना है", "hi") == "goat_rearing"
