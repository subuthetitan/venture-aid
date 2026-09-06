"""
PAIR B. Speech-to-text with a provider fallback chain.

    Bhashini (ULCA/Dhruva)  ->  Sarvam Saaras  ->  committed fixture

Per MVP_BUILD_PLAN.md: "Bhashini primary, Sarvam fallback, 6s timeout." Bhashini
is primary deliberately -- ARCHITECTURE.md line 184 makes the unused-government-
stack gap the novelty claim, so a Sarvam-only build throws that away.

No provider is ever allowed to break the endpoint. Every failure mode (missing
credentials, DNS, timeout, 4xx/5xx, malformed JSON, unexpected shape) falls
through to the next provider and finally to the fixture. The frontend also has
a "type it instead" path, so this is not the last line of defence.

=============================================================================
VERIFIED API CONTRACTS  (checked 2026-09-05 against live vendor docs)
=============================================================================
BHASHINI -- two calls, documented at https://bhashini.gitbook.io/bhashini-apis

 1. Pipeline Config
    POST https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline
    headers: userID, ulcaApiKey        (from ULCA "My Profile")
    body:   {"pipelineTasks":[{"taskType":"asr",
                               "config":{"language":{"sourceLanguage":"hi"}}}],
             "pipelineRequestConfig":{"pipelineId":"..."}}
    -> response carries:
       pipelineInferenceAPIEndPoint.callbackUrl
         e.g. "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
       pipelineInferenceAPIEndPoint.inferenceApiKey.name   e.g. "Authorization"
       pipelineInferenceAPIEndPoint.inferenceApiKey.value  (the token)
       pipelineResponseConfig[].config[].serviceId

 2. Pipeline Compute
    POST <callbackUrl>
    headers: {<inferenceApiKey.name>: <inferenceApiKey.value>}
    body:   {"pipelineTasks":[{"taskType":"asr",
              "config":{"language":{"sourceLanguage":"hi"},
                        "serviceId":"...","audioFormat":"wav","samplingRate":16000}}],
             "inputData":{"audio":[{"audioContent":"<base64>"}]}}
    -> transcript at pipelineResponse[0].output[0].source

SARVAM -- one call, documented at
https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe
    POST https://api.sarvam.ai/speech-to-text
    header:   api-subscription-key: <key>      (raw value, no "Bearer" prefix)
    body:     multipart/form-data, file field named "file"
    fields:   model=saaras:v3 (default; saaras:v4 is latest),
              language_code=hi-IN | kn-IN | en-IN | ...
    -> transcript at response["transcript"]

NAMING CORRECTION: the build plan says "Sarvam Saaras/Bulbul". Bulbul is
Sarvam's TEXT-TO-SPEECH model -- the wrong direction for this endpoint. Saaras
is the speech-to-text model and is what we call. (Saarika was the older ASR
model; the docs now route transcription through saaras with mode=transcribe.)
=============================================================================
"""
import base64
import logging
import time
from typing import NamedTuple

import httpx

from app.config import settings

log = logging.getLogger(__name__)

BHASHINI_CONFIG_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_MODEL = "saaras:v3"

# Same string the endpoint has always returned. Kept so that a keyless or
# offline deployment behaves exactly as it did before this module existed.
FIXTURE_TRANSCRIPT = "मुझे सिलाई का काम शुरू करना है"


class TranscriptionResult(NamedTuple):
    transcript: str
    provider: str          # 'bhashini' | 'sarvam' | 'fixture'


def _timeout() -> float:
    return float(getattr(settings, "transcription_timeout_seconds", 6.0))


def _sarvam_language(language: str) -> str:
    """'hi' -> 'hi-IN'. Sarvam wants BCP-47; Bhashini wants the bare code."""
    if not language:
        return "unknown"
    return language if "-" in language else f"{language}-IN"


# ------------------------------------------------------------- providers --
def _call_bhashini(audio: bytes, language: str) -> str | None:
    """Config call then compute call. Returns the transcript, or None."""
    if not (settings.ulca_user_id and settings.ulca_api_key
            and getattr(settings, "ulca_pipeline_id", "")):
        return None

    budget = _timeout()
    deadline = time.monotonic() + budget

    with httpx.Client(timeout=budget) as client:
        cfg = client.post(
            BHASHINI_CONFIG_URL,
            headers={"userID": settings.ulca_user_id, "ulcaApiKey": settings.ulca_api_key},
            json={"pipelineTasks": [{"taskType": "asr",
                                     "config": {"language": {"sourceLanguage": language}}}],
                  "pipelineRequestConfig": {"pipelineId": settings.ulca_pipeline_id}},
        )
        cfg.raise_for_status()
        cfg_body = cfg.json()

        endpoint = cfg_body["pipelineInferenceAPIEndPoint"]
        callback_url = endpoint["callbackUrl"]
        key = endpoint["inferenceApiKey"]
        # serviceId lives under the per-task response config.
        service_id = cfg_body["pipelineResponseConfig"][0]["config"][0]["serviceId"]

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise httpx.TimeoutException("Bhashini budget exhausted after config call")

        compute = client.post(
            callback_url,
            headers={key["name"]: key["value"]},
            json={"pipelineTasks": [{"taskType": "asr",
                                     "config": {"language": {"sourceLanguage": language},
                                                "serviceId": service_id,
                                                "audioFormat": "wav",
                                                "samplingRate": 16000}}],
                  "inputData": {"audio": [{"audioContent": base64.b64encode(audio).decode()}]}},
            timeout=remaining,
        )
        compute.raise_for_status()
        text = compute.json()["pipelineResponse"][0]["output"][0]["source"]

    text = (text or "").strip()
    return text or None


def _call_sarvam(audio: bytes, language: str, filename: str, content_type: str) -> str | None:
    """Single multipart POST. Returns the transcript, or None."""
    if not settings.sarvam_api_key:
        return None

    with httpx.Client(timeout=_timeout()) as client:
        res = client.post(
            SARVAM_STT_URL,
            headers={"api-subscription-key": settings.sarvam_api_key},
            files={"file": (filename or "audio.wav", audio,
                            content_type or "audio/wav")},
            data={"model": SARVAM_MODEL, "language_code": _sarvam_language(language)},
        )
        res.raise_for_status()
        text = res.json()["transcript"]

    text = (text or "").strip()
    return text or None


# ------------------------------------------------------------ the chain --
def transcribe(audio: bytes, language: str = "hi", filename: str = "audio.wav",
               content_type: str = "audio/wav") -> TranscriptionResult:
    """Bhashini -> Sarvam -> fixture. Never raises."""
    if settings.offline_mode:
        # Documented escape hatch: all external calls return committed fixtures.
        return TranscriptionResult(FIXTURE_TRANSCRIPT, "fixture")

    providers = (
        ("bhashini", lambda: _call_bhashini(audio, language)),
        ("sarvam", lambda: _call_sarvam(audio, language, filename, content_type)),
    )
    for name, call in providers:
        try:
            text = call()
        except Exception as exc:
            # Timeout, connection error, 4xx/5xx, bad JSON, unexpected shape --
            # all identical from here: try the next provider.
            log.warning("transcription provider %s failed (%s: %s); falling through",
                        name, type(exc).__name__, exc)
            continue
        # Strip here as well as in the provider functions: a whitespace-only
        # transcript is not a successful transcription, and returning one would
        # show the applicant a blank result labelled as a real ASR success.
        if text and text.strip():
            return TranscriptionResult(text.strip(), name)
        # None/blank means "not configured" or "empty result" -- neither is an error.
        log.info("transcription provider %s unavailable or returned nothing", name)

    return TranscriptionResult(FIXTURE_TRANSCRIPT, "fixture")
