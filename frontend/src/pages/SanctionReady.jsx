import { useEffect, useRef, useState } from "react";

// The duplicate fetch that used to live here is gone. api.js's req() now
// throws an ApiError carrying the parsed body, so api.readiness() can surface
// the backend's supported_activities list -- which was the only reason this
// page bypassed the shared helper. BASE is still needed for the PDF link.
import { api, BASE, isStructuredDetail } from "../lib/api";

// Guards the unvalidated boundary: ProjectReport.capex_items is typed
// list[dict], so nothing in the schema stops an item arriving without
// qty/unit_cost/total. Our backend always sends them, but an unguarded
// arithmetic fallback rendered a literal "NaN" in the Amount column, which
// reads as a real figure on a report someone submits to a bank. An em dash
// says "we do not have this number" instead.
// Matches Calculator.jsx: anything that is not a finite number renders as an
// em dash. Returning the raw value here let a string from the API render as if
// it were a rupee figure.
const rupees = (n) =>
  typeof n === "number" && Number.isFinite(n) ? n.toLocaleString("en-IN") : "—";

// Turns 'tailoring_unit' into 'Tailoring unit' for display only. The id sent
// back to the API is always the raw string from the response.
const prettify = (id) =>
  id.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

// Languages the ASR chain is wired for. Sent to /api/readiness/transcribe as
// the bare code; transcription.py maps it to Sarvam's BCP-47 form.
const LANGUAGES = [
  { code: "hi", label: "हिन्दी / Hindi" },
  { code: "kn", label: "ಕನ್ನಡ / Kannada" },
  { code: "mr", label: "मराठी / Marathi" },
  { code: "ta", label: "தமிழ் / Tamil" },
  { code: "bn", label: "বাংলা / Bengali" },
  { code: "en", label: "English" },
];

// Mirrors MAX_AUDIO_BYTES in backend/app/routers/readiness.py. Checked here so
// an over-long recording fails fast with a clear message instead of a 413
// after a slow upload.
const MAX_AUDIO_BYTES = 20 * 1024 * 1024;

export default function SanctionReady() {
  const [transcript, setTranscript] = useState("");
  const [gender, setGender] = useState("");
  const [language, setLanguage] = useState("hi");
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // -- voice ---------------------------------------------------------------
  // MVP_BUILD_PLAN.md: "Always keep a 'type it instead' path visible. ASR
  // failing live must be a shrug, not a dead demo." So every failure below
  // lands in `voiceNote` and leaves the textarea untouched and usable.
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceNote, setVoiceNote] = useState(null); // {kind:'info'|'error', text}
  const [provider, setProvider] = useState(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);

  // Release the microphone if the user navigates away mid-recording.
  useEffect(() => {
    return () => {
      try {
        recorderRef.current?.state === "recording" && recorderRef.current.stop();
      } catch {
        /* already stopped */
      }
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const micSupported =
    typeof window !== "undefined" &&
    typeof window.MediaRecorder !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia;

  async function startRecording() {
    setVoiceNote(null);
    setProvider(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const rec = new MediaRecorder(stream);
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = () => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        const blob = new Blob(chunksRef.current, {
          type: rec.mimeType || "audio/webm",
        });
        sendAudio(blob);
      };
      recorderRef.current = rec;
      rec.start();
      setRecording(true);
    } catch {
      // Permission denied, no device, or insecure origin (getUserMedia needs
      // https or localhost).
      setVoiceNote({
        kind: "error",
        text:
          "Could not start the microphone — permission denied, no input device, " +
          "or the page is not on https/localhost. Type the description instead.",
      });
    }
  }

  function stopRecording() {
    setRecording(false);
    try {
      recorderRef.current?.stop();
    } catch {
      /* nothing recorded */
    }
  }

  async function sendAudio(blob) {
    if (!blob || blob.size === 0) {
      setVoiceNote({ kind: "error", text: "Nothing was recorded. Try again, or type it instead." });
      return;
    }
    if (blob.size > MAX_AUDIO_BYTES) {
      setVoiceNote({
        kind: "error",
        text: `Recording is too long (${(blob.size / 1048576).toFixed(1)} MB, limit 20 MB). Record a shorter clip.`,
      });
      return;
    }

    setTranscribing(true);
    setVoiceNote(null);
    try {
      const res = await api.transcribe(blob, language);
      if (res?.transcript) {
        setTranscript(res.transcript);
        setProvider(res.provider ?? null);
        // Labelled fallback, per the README rule on never shipping an
        // unlabelled mock: 'fixture' means no provider answered and this is a
        // cached demo response, not a transcription of what was just said.
        setVoiceNote(
          res.provider === "fixture"
            ? {
                kind: "info",
                text:
                  "No speech provider was reachable, so this is a cached demo " +
                  "transcript — not a transcription of what you just said. " +
                  "Edit it, or type your own.",
              }
            : { kind: "info", text: `Transcribed by ${res.provider}. Check it before generating.` },
        );
      } else {
        setVoiceNote({ kind: "error", text: "No transcript came back. Type it instead." });
      }
    } catch (e) {
      const detail = e?.detail;
      setVoiceNote({
        kind: "error",
        text:
          (isStructuredDetail(detail) && detail.message) ||
          (e?.status === 0
            ? "Could not reach the API. Type the description instead."
            : `Transcription failed (${e?.status ?? "?"}). Type the description instead.`),
      });
    } finally {
      setTranscribing(false);
    }
  }

  // `override` lets the supported-activity chips re-submit as an explicit
  // activity_id instead of relying on the classifier a second time.
  async function submit(override = null) {
    setLoading(true);
    setError(null);
    setReport(null);

    const body = {
      // Drives both the classifier hint and which localised activity label
      // heads the generated PDF (pdf_generator._titles).
      language,
      profile: {
        family_income: 0,
        state_code: "KA",
        district_code: "",
        ...(gender ? { gender } : {}),
      },
      ...(override ? { activity_id: override } : { transcript }),
    };

    try {
      setReport(await api.readiness(body));
    } catch (e) {
      const detail = e?.detail;

      // The backend's activity errors (UNRECOGNIZED_ACTIVITY and
      // NO_COST_TEMPLATE) both carry a supported_activities array. Keying off
      // the array rather than the error code means a new code with the same
      // shape still renders usefully. FastAPI's own validation 422s have an
      // ARRAY detail, so isStructuredDetail() is false there and they
      // correctly fall through to the generic message.
      if (
        e?.status === 422 &&
        isStructuredDetail(detail) &&
        Array.isArray(detail.supported_activities)
      ) {
        setError({
          kind: "activity",
          code: detail.error,
          message: detail.message,
          supported: detail.supported_activities,
        });
      } else {
        // status 0 is a network failure / CORS / server unreachable.
        setError({ kind: "generic", status: e?.status || null });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border bg-white p-8">
        <p className="text-xs uppercase tracking-wide text-stone-400">Pair B</p>
        <h2 className="mt-1 text-xl font-semibold">Sanction-Ready</h2>

        {/* ------------------------------------------------------- voice -- */}
        <div className="mt-4 rounded-md border border-stone-200 bg-stone-50 p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="asr-lang" className="block text-sm font-medium text-stone-700">
                Spoken language
              </label>
              <select
                id="asr-lang"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={recording || transcribing}
                className="mt-1 rounded-md border border-stone-300 p-2 text-sm
                           focus:border-stone-500 focus:outline-none
                           disabled:cursor-not-allowed disabled:bg-stone-100"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>{l.label}</option>
                ))}
              </select>
            </div>

            {!recording ? (
              <button
                type="button"
                onClick={startRecording}
                disabled={!micSupported || transcribing || loading}
                className="rounded-md bg-stone-800 px-4 py-2 text-sm font-medium text-white
                           hover:bg-stone-700 disabled:cursor-not-allowed disabled:bg-stone-300"
              >
                {transcribing ? "Transcribing…" : "● Record"}
              </button>
            ) : (
              <button
                type="button"
                onClick={stopRecording}
                className="rounded-md bg-red-700 px-4 py-2 text-sm font-medium text-white
                           hover:bg-red-800"
              >
                ■ Stop
              </button>
            )}

            {recording && (
              <span className="flex items-center gap-2 text-sm text-red-700">
                <span className="inline-block h-2.5 w-2.5 animate-pulse rounded-full bg-red-600" />
                Recording…
              </span>
            )}
            {provider && !recording && !transcribing && (
              <span className="rounded-full bg-stone-200 px-2 py-0.5 text-xs text-stone-700">
                provider: {provider}
              </span>
            )}
          </div>

          {!micSupported && (
            <p className="mt-2 text-xs text-stone-500">
              This browser cannot record audio. Type the description below —
              everything else works the same.
            </p>
          )}

          {voiceNote && (
            <p
              className={`mt-2 rounded-md border p-2 text-xs ${
                voiceNote.kind === "error"
                  ? "border-amber-300 bg-amber-50 text-amber-900"
                  : "border-stone-300 bg-white text-stone-700"
              }`}
            >
              {voiceNote.text}
            </p>
          )}

          <p className="mt-2 text-xs text-stone-500">
            Speech goes to Bhashini first, then Sarvam, then a cached fixture.
            Whichever answered is named above, and a cached response is always
            labelled as one.
          </p>
        </div>

        <label
          htmlFor="transcript"
          className="mt-4 block text-sm font-medium text-stone-700"
        >
          Describe the business, or type it instead of speaking
        </label>
        <textarea
          id="transcript"
          rows={3}
          value={transcript}
          onChange={(e) => setTranscript(e.target.value)}
          placeholder="मुझे सिलाई का काम शुरू करना है"
          className="mt-1 w-full rounded-md border border-stone-300 p-2 text-sm
                     focus:border-stone-500 focus:outline-none"
        />

        <div className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label
              htmlFor="gender"
              className="block text-sm font-medium text-stone-700"
            >
              Applicant gender
            </label>
            <select
              id="gender"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="mt-1 rounded-md border border-stone-300 p-2 text-sm
                         focus:border-stone-500 focus:outline-none"
            >
              <option value="">Not specified</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
            <p className="mt-1 text-xs text-stone-500">
              Women-only schemes are offered only when this is set to Female.
            </p>
          </div>

          <button
            type="button"
            onClick={() => submit()}
            disabled={loading || !transcript.trim()}
            className="rounded-md bg-stone-800 px-4 py-2 text-sm font-medium text-white
                       hover:bg-stone-700 disabled:cursor-not-allowed disabled:bg-stone-300"
          >
            {loading ? "Generating…" : "Generate report"}
          </button>
        </div>
      </div>

      {/* ---------------------------------------------- unrecognized activity -- */}
      {error?.kind === "activity" && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-6">
          <h3 className="text-sm font-semibold text-amber-900">
            We could not identify the activity
          </h3>
          <p className="mt-1 text-sm text-amber-800">{error.message}</p>
          <p className="mt-4 text-sm font-medium text-amber-900">
            Activities we can cost today:
          </p>
          {/* Rendered from the API response, never a hardcoded list, so the
              frontend cannot drift out of sync with the backend's templates. */}
          <div className="mt-2 flex flex-wrap gap-2">
            {error.supported.map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => submit(id)}
                disabled={loading}
                className="rounded-full border border-amber-400 bg-white px-3 py-1
                           text-sm text-amber-900 hover:bg-amber-100
                           disabled:cursor-not-allowed disabled:opacity-50"
              >
                {prettify(id)}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* -------------------------------------------------- generic fallback -- */}
      {error?.kind === "generic" && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-6">
          <p className="text-sm text-red-800">
            Something went wrong generating the report
            {error.status ? ` (${error.status})` : ""}. Please try again.
          </p>
        </div>
      )}

      {/* ---------------------------------------------------------- report -- */}
      {report && (
        <div className="rounded-lg border bg-white p-8">
          <h3 className="text-lg font-semibold">{report.activity_label}</h3>
          <p className="mt-2 text-sm text-stone-600">{report.narrative}</p>

          <h4 className="mt-6 text-sm font-semibold">Capital expenditure</h4>
          <table className="mt-2 w-full text-sm">
            <thead>
              <tr className="border-b text-left text-stone-500">
                <th className="py-1 font-medium">Item</th>
                <th className="py-1 text-right font-medium">Qty</th>
                <th className="py-1 text-right font-medium">Amount (Rs)</th>
              </tr>
            </thead>
            <tbody>
              {/* Index in the key: capex_items is list[dict], so nothing in
                  the schema stops two rows sharing an item name, and a
                  duplicate React key drops one of them from the table. */}
              {report.capex_items.map((item, i) => (
                <tr key={`${item.item}-${i}`} className="border-b border-stone-100">
                  <td className="py-1">{item.item}</td>
                  <td className="py-1 text-right">{item.qty}</td>
                  <td className="py-1 text-right">
                    {rupees(item.total ?? item.qty * item.unit_cost)}
                  </td>
                </tr>
              ))}
              <tr className="font-semibold">
                <td className="py-1" colSpan={2}>
                  Total project cost
                </td>
                <td className="py-1 text-right">
                  {rupees(report.total_project_cost)}
                </td>
              </tr>
            </tbody>
          </table>

          <h4 className="mt-6 text-sm font-semibold">Proposed financing</h4>
          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-stone-500">Scheme</dt>
            <dd>{report.recommended_scheme_id}</dd>
            <dt className="text-stone-500">Interest rate</dt>
            <dd>{report.finance.interest_rate}% per annum</dd>
            <dt className="text-stone-500">Monthly instalment (EMI)</dt>
            <dd>Rs {rupees(report.finance.emi)}</dd>
            <dt className="text-stone-500">Tenure</dt>
            <dd>
              {report.finance.tenure_months} months, incl.{" "}
              {report.finance.moratorium_months}-month moratorium
            </dd>
            <dt className="text-stone-500">Estimated break-even</dt>
            <dd>
              {report.break_even_months > 0
                ? `${report.break_even_months} months`
                : "Not established"}
            </dd>
          </dl>

          <h4 className="mt-6 text-sm font-semibold">Document checklist</h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-stone-600">
            {report.document_checklist.map((doc) => (
              <li key={doc}>{doc}</li>
            ))}
          </ul>

          <p className="mt-6 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
            Cost figures are unverified estimates pending KVIC/NABARD sourcing.
            Financing figures are computed arithmetically; no figure here was
            produced by a language model.
          </p>

          <div className="mt-6">
            {report.pdf_url ? (
              <a
                href={`${BASE}${report.pdf_url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block rounded-md bg-stone-800 px-4 py-2 text-sm
                           font-medium text-white hover:bg-stone-700"
              >
                Download PDF
              </a>
            ) : (
              /* Backend fails open: the JSON report still returns when PDF
                 generation is unavailable, leaving pdf_url null. */
              <button
                type="button"
                disabled
                title="PDF generation is unavailable on the server right now. The report above is still complete."
                className="cursor-not-allowed rounded-md bg-stone-200 px-4 py-2
                           text-sm font-medium text-stone-500"
              >
                Download PDF
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
