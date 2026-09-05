"""
PAIR B. Fallback-chain tests for speech-to-text.

NOTHING HERE TOUCHES THE NETWORK. Every provider call is monkeypatched, and one
test actively fails if any HTTP client is constructed at all. These tests must
pass on a laptop with no credentials, no internet, and no vendor account.
"""
import httpx
import pytest

from app.services import transcription
from app.services.transcription import FIXTURE_TRANSCRIPT, TranscriptionResult

AUDIO = b"RIFF....fake wav bytes for testing...."


@pytest.fixture(autouse=True)
def _no_keys(monkeypatch):
    """Default every test to the real-world state today: no credentials set."""
    monkeypatch.setattr(transcription.settings, "ulca_user_id", "", raising=False)
    monkeypatch.setattr(transcription.settings, "ulca_api_key", "", raising=False)
    monkeypatch.setattr(transcription.settings, "ulca_pipeline_id", "", raising=False)
    monkeypatch.setattr(transcription.settings, "sarvam_api_key", "", raising=False)
    monkeypatch.setattr(transcription.settings, "offline_mode", False, raising=False)


def _forbid_http(monkeypatch):
    """Make constructing an HTTP client an immediate, loud failure."""
    def boom(*args, **kwargs):
        raise AssertionError("a real HTTP client was constructed - no call should have been made")
    monkeypatch.setattr(httpx, "Client", boom)


# ------------------------------------------------- no credentials configured --
def test_no_keys_returns_fixture_without_attempting_any_request(monkeypatch):
    """The state of the repo today. Must not burn a 6s timeout on a doomed call."""
    _forbid_http(monkeypatch)
    result = transcription.transcribe(AUDIO, "hi")
    assert result == TranscriptionResult(FIXTURE_TRANSCRIPT, "fixture")


def test_partial_bhashini_credentials_still_skip_bhashini(monkeypatch):
    # user id + key but no pipeline id: the config call cannot be built, so skip.
    monkeypatch.setattr(transcription.settings, "ulca_user_id", "u", raising=False)
    monkeypatch.setattr(transcription.settings, "ulca_api_key", "k", raising=False)
    _forbid_http(monkeypatch)
    assert transcription.transcribe(AUDIO, "hi").provider == "fixture"


def test_offline_mode_short_circuits_everything(monkeypatch):
    monkeypatch.setattr(transcription.settings, "offline_mode", True, raising=False)
    _forbid_http(monkeypatch)
    assert transcription.transcribe(AUDIO, "hi") == TranscriptionResult(FIXTURE_TRANSCRIPT, "fixture")


# ------------------------------------------------------------ happy paths --
def test_bhashini_success_returns_bhashini_and_never_calls_sarvam(monkeypatch):
    called = {"sarvam": False}
    monkeypatch.setattr(transcription, "_call_bhashini", lambda a, l: "बहशिनी का उत्तर")

    def sarvam(*args, **kwargs):
        called["sarvam"] = True
        return "should not be reached"

    monkeypatch.setattr(transcription, "_call_sarvam", sarvam)

    result = transcription.transcribe(AUDIO, "hi")
    assert result == TranscriptionResult("बहशिनी का उत्तर", "bhashini")
    assert called["sarvam"] is False, "Sarvam was called even though Bhashini succeeded"


def test_sarvam_used_when_bhashini_returns_nothing(monkeypatch):
    monkeypatch.setattr(transcription, "_call_bhashini", lambda a, l: None)
    monkeypatch.setattr(transcription, "_call_sarvam", lambda a, l, f, c: "सर्वम का उत्तर")
    assert transcription.transcribe(AUDIO, "hi") == TranscriptionResult("सर्वम का उत्तर", "sarvam")


# ------------------------------------------------- failure modes fall through --
@pytest.mark.parametrize("exc", [
    httpx.TimeoutException("timed out"),
    httpx.ConnectError("dns failure"),
    httpx.HTTPStatusError("500", request=None, response=None),
    ValueError("malformed json"),
    KeyError("pipelineResponse"),
    IndexError("empty output list"),
])
def test_any_bhashini_failure_falls_through_to_sarvam(monkeypatch, exc):
    def boom(*args, **kwargs):
        raise exc

    monkeypatch.setattr(transcription, "_call_bhashini", boom)
    monkeypatch.setattr(transcription, "_call_sarvam", lambda a, l, f, c: "sarvam rescued it")
    result = transcription.transcribe(AUDIO, "hi")
    assert result == TranscriptionResult("sarvam rescued it", "sarvam")


def test_both_providers_failing_falls_through_to_fixture(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(transcription, "_call_bhashini", boom)
    monkeypatch.setattr(transcription, "_call_sarvam", boom)
    assert transcription.transcribe(AUDIO, "hi") == TranscriptionResult(FIXTURE_TRANSCRIPT, "fixture")


def test_both_providers_returning_empty_falls_through_to_fixture(monkeypatch):
    monkeypatch.setattr(transcription, "_call_bhashini", lambda a, l: None)
    monkeypatch.setattr(transcription, "_call_sarvam", lambda a, l, f, c: "   ")
    assert transcription.transcribe(AUDIO, "hi").provider == "fixture"


def test_transcribe_never_raises_even_on_an_unexpected_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("something nobody anticipated")

    monkeypatch.setattr(transcription, "_call_bhashini", boom)
    monkeypatch.setattr(transcription, "_call_sarvam", boom)
    assert transcription.transcribe(AUDIO, "hi").provider == "fixture"


# ------------------------------------------------------------- small units --
@pytest.mark.parametrize("given,expected", [
    ("hi", "hi-IN"), ("kn", "kn-IN"), ("en", "en-IN"),
    ("hi-IN", "hi-IN"), ("", "unknown"),
])
def test_sarvam_language_code_mapping(given, expected):
    # Sarvam wants BCP-47 (hi-IN); Bhashini wants the bare code (hi).
    assert transcription._sarvam_language(given) == expected


def test_provider_names_match_the_frontend_contract():
    # SanctionReady renders this value verbatim; only these three are valid.
    monkeyless = transcription.transcribe(AUDIO, "hi")
    assert monkeyless.provider in {"bhashini", "sarvam", "fixture"}


# ----------------------------------------------------------- route contract --
def test_transcribe_route_returns_fixture_shape_with_no_keys():
    from fastapi.testclient import TestClient

    from app.main import app

    r = TestClient(app).post("/api/readiness/transcribe",
                             files={"audio": ("a.wav", AUDIO, "audio/wav")},
                             params={"language": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"transcript", "provider"}
    assert body == {"transcript": FIXTURE_TRANSCRIPT, "provider": "fixture"}
