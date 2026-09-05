import { useState } from "react";

import { api } from "../lib/api";

// Same NaN guard as SanctionReady.jsx. A malformed number must never render as
// a literal "NaN" -- that reads as a real figure on a document someone takes to
// a bank. An em dash says "we do not have this number".
const rupees = (n) =>
  typeof n === "number" ? (Number.isFinite(n) ? n.toLocaleString("en-IN") : "—") : "—";

// Two decimals for per-row money, same guard.
const rupees2 = (n) =>
  typeof n === "number" && Number.isFinite(n)
    ? n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : "—";

const percent = (n) =>
  typeof n === "number" && Number.isFinite(n) ? `${n}% per annum` : "—";

// Mirrors SCHEME_TERMS in backend/app/services/finance.py.
//
// DISPLAY NAMES: only 'Suvidha Loan' is sourced -- it appears in Pair A's
// fixtures/recommend.json. The other three labels are transliterations of the
// scheme ids and are NOT taken from any published NSFDC page.
// TODO(pair-b): confirm all four official scheme names alongside the
// SCHEME_TERMS source URLs. The raw scheme_id is shown next to each label in
// the dropdown so an operator can always see exactly what is being sent.
//
// womenOnly mirrors WOMEN_ONLY_SCHEMES in backend/app/routers/readiness.py.
// DUPLICATED CONSTANT: the backend does not expose that set over the API, so
// this list can silently drift out of sync with the gate that actually governs
// eligibility. It is display-only here -- it gates nothing -- but if a scheme
// is added there it must be added here too.
const SCHEMES = [
  { id: "nsfdc.suvidha", label: "Suvidha Loan", womenOnly: false },
  { id: "nsfdc.micro_credit", label: "Micro Credit Finance", womenOnly: false },
  { id: "nsfdc.mahila_samriddhi", label: "Mahila Samriddhi Yojana", womenOnly: true },
  { id: "nsfdc.laghu_vyavsay", label: "Laghu Vyavsay Yojana", womenOnly: false },
];

const FIELDS = [
  { key: "project_cost", label: "Project cost (Rs)", required: true },
  { key: "own_contribution", label: "Own contribution (Rs)" },
  { key: "subsidy_amount", label: "Subsidy amount (Rs)" },
  { key: "subsidy_delay_months", label: "Subsidy delay (months)" },
];

const toInt = (value) => {
  const n = Number.parseInt(value, 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
};

export default function Calculator() {
  const [schemeId, setSchemeId] = useState(SCHEMES[0].id);
  const [values, setValues] = useState({
    project_cost: "",
    own_contribution: "",
    subsidy_amount: "",
    subsidy_delay_months: "",
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showSchedule, setShowSchedule] = useState(true);

  const selected = SCHEMES.find((s) => s.id === schemeId);
  const canSubmit = !loading && toInt(values.project_cost) > 0;

  async function submit() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await api.calculate({
          scheme_id: schemeId,
          project_cost: toInt(values.project_cost),
          own_contribution: toInt(values.own_contribution),
          subsidy_amount: toInt(values.subsidy_amount),
          subsidy_delay_months: toInt(values.subsidy_delay_months),
        }),
      );
    } catch (e) {
      // api.js throws `new Error("<status> <path>")` and discards the response
      // body, so there is no structured detail to surface here.
      setError(e?.message ?? "unknown error");
    } finally {
      setLoading(false);
    }
  }

  // A zero loan is a VALID result, not an error: it means own_contribution
  // already covers the project cost (the backend clamps at zero rather than
  // returning a negative loan).
  const fullySelfFunded = result && result.sanctionable_amount === 0;
  const rawSchedule = Array.isArray(result?.schedule) ? result.schedule : [];
  // A zero loan still comes back with a full set of rows, every figure 0.00
  // (the backend generates one row per repayment month regardless of
  // principal). Listing 54 rows of zeros directly under "there is nothing to
  // repay" contradicts itself, so treat that as the empty state. Rows are only
  // suppressed when the loan itself is zero -- never filtered out of a real
  // schedule.
  const schedule = fullySelfFunded ? [] : rawSchedule;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border bg-white p-8">
        <p className="text-xs uppercase tracking-wide text-stone-400">Pair B</p>
        <h2 className="mt-1 text-xl font-semibold">Financial Calculator</h2>

        <label htmlFor="scheme" className="mt-4 block text-sm font-medium text-stone-700">
          Scheme
        </label>
        <select
          id="scheme"
          value={schemeId}
          onChange={(e) => setSchemeId(e.target.value)}
          className="mt-1 w-full max-w-lg rounded-md border border-stone-300 p-2 text-sm
                     focus:border-stone-500 focus:outline-none"
        >
          {SCHEMES.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label} ({s.id}){s.womenOnly ? " — women applicants only" : ""}
            </option>
          ))}
        </select>
        {/* Surfaced, not gated. This calculator collects no applicant gender,
            so it cannot make an eligibility determination -- it just must not
            let someone quote an EMI without knowing the restriction exists. */}
        {selected?.womenOnly && (
          <p className="mt-1 text-xs text-amber-800">
            Mahila Samriddhi Yojana is restricted to women applicants. This
            calculator will still model it for comparison, but confirm
            eligibility before quoting these figures to an applicant.
          </p>
        )}

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FIELDS.map((f) => (
            <div key={f.key}>
              <label htmlFor={f.key} className="block text-sm font-medium text-stone-700">
                {f.label}
              </label>
              <input
                id={f.key}
                type="number"
                min="0"
                inputMode="numeric"
                value={values[f.key]}
                onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
                placeholder="0"
                className="mt-1 w-full rounded-md border border-stone-300 p-2 text-sm
                           focus:border-stone-500 focus:outline-none"
              />
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            type="button"
            onClick={submit}
            disabled={!canSubmit}
            className="rounded-md bg-stone-800 px-4 py-2 text-sm font-medium text-white
                       hover:bg-stone-700 disabled:cursor-not-allowed disabled:bg-stone-300"
          >
            {loading ? "Calculating…" : "Calculate"}
          </button>
          <p className="text-xs text-stone-500">
            Project cost is required. Everything else defaults to zero.
          </p>
        </div>
      </div>

      {/* ------------------------------------------------------------ error -- */}
      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-6">
          <p className="text-sm text-red-800">
            Something went wrong calculating the schedule ({error}). Please try
            again.
          </p>
        </div>
      )}

      {/* ----------------------------------------------------------- result -- */}
      {result && (
        <div className="rounded-lg border bg-white p-8">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="text-lg font-semibold">Repayment</h3>
            {/* Load-bearing honesty flag, straight from the API. */}
            <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
              provenance: {result.provenance ?? "—"}
            </span>
          </div>

          {fullySelfFunded && (
            <p className="mt-3 rounded-md border border-stone-300 bg-stone-50 p-3 text-sm text-stone-700">
              No loan is required. The own contribution entered covers the whole
              project cost, so the sanctionable amount is Rs 0 and there is
              nothing to repay.
            </p>
          )}

          <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            <dt className="text-stone-500">Sanctionable amount</dt>
            <dd>Rs {rupees(result.sanctionable_amount)}</dd>
            <dt className="text-stone-500">Interest rate</dt>
            <dd>{percent(result.interest_rate)}</dd>
            <dt className="text-stone-500">Monthly instalment (EMI)</dt>
            <dd>Rs {rupees2(result.emi)}</dd>
            <dt className="text-stone-500">Tenure</dt>
            <dd>
              {Number.isFinite(result.tenure_months) ? result.tenure_months : "—"} months,
              incl.{" "}
              {Number.isFinite(result.moratorium_months) ? result.moratorium_months : "—"}
              -month moratorium
            </dd>
            <dt className="text-stone-500">Total interest</dt>
            <dd>Rs {rupees2(result.total_interest)}</dd>
            <dt className="text-stone-500">Total repayment</dt>
            <dd>Rs {rupees2(result.total_repayment)}</dd>
          </dl>

          {/* Only rendered when the API actually sent one. */}
          {result.subsidy_note && (
            <p className="mt-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              {result.subsidy_note}
            </p>
          )}

          <div className="mt-6 flex items-center justify-between">
            <h4 className="text-sm font-semibold">
              Repayment schedule
              {schedule.length > 0 && (
                <span className="ml-2 font-normal text-stone-500">
                  ({schedule.length} months)
                </span>
              )}
            </h4>
            {schedule.length > 0 && (
              <button
                type="button"
                onClick={() => setShowSchedule((v) => !v)}
                className="text-sm text-stone-600 underline hover:text-stone-900"
              >
                {showSchedule ? "Hide" : "Show"}
              </button>
            )}
          </div>

          {schedule.length === 0 ? (
            <p className="mt-2 rounded-md border border-dashed border-stone-300 p-4 text-sm text-stone-500">
              No repayment schedule — there is nothing to repay on this loan.
              {fullySelfFunded && rawSchedule.length > 0 && (
                <span className="mt-1 block text-xs text-stone-400">
                  ({rawSchedule.length} zero-value rows returned by the API are
                  not shown.)
                </span>
              )}
            </p>
          ) : (
            showSchedule && (
              // Up to 66 rows (laghu_vyavsay: 72-month tenure less a 6-month
              // moratorium). Capped height with a sticky header beats dumping
              // every row into the page flow.
              <div className="mt-2 max-h-96 overflow-y-auto rounded-md border">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-stone-100">
                    <tr className="text-left text-stone-600">
                      <th className="px-2 py-1 font-medium">Month</th>
                      <th className="px-2 py-1 text-right font-medium">Opening</th>
                      <th className="px-2 py-1 text-right font-medium">Interest</th>
                      <th className="px-2 py-1 text-right font-medium">Principal</th>
                      <th className="px-2 py-1 text-right font-medium">EMI</th>
                      <th className="px-2 py-1 text-right font-medium">Closing</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.map((row, i) => (
                      <tr
                        key={row?.month ?? i}
                        className="border-t border-stone-100"
                      >
                        <td className="px-2 py-1">
                          {Number.isFinite(row?.month) ? row.month : "—"}
                        </td>
                        <td className="px-2 py-1 text-right">{rupees2(row?.opening_balance)}</td>
                        <td className="px-2 py-1 text-right">{rupees2(row?.interest)}</td>
                        <td className="px-2 py-1 text-right">{rupees2(row?.principal)}</td>
                        <td className="px-2 py-1 text-right">{rupees2(row?.emi)}</td>
                        <td className="px-2 py-1 text-right">{rupees2(row?.closing_balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          <p className="mt-6 rounded-md border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
            Figures are computed arithmetically from the scheme terms; no number
            here was produced by a language model. Scheme rates and ceilings are
            pending confirmation against published NSFDC sources.
          </p>
        </div>
      )}
    </div>
  );
}
