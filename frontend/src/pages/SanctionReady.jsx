import { useState } from "react";

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

export default function SanctionReady() {
  const [transcript, setTranscript] = useState("");
  const [gender, setGender] = useState("");
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // `override` lets the supported-activity chips re-submit as an explicit
  // activity_id instead of relying on the classifier a second time.
  async function submit(override = null) {
    setLoading(true);
    setError(null);
    setReport(null);

    const body = {
      language: "hi",
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
