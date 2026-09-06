/**
 * PAIR A's screen. Built by Pair B during integration at the team's request --
 * the backend was real and had no UI, so demo beats 1 and 2 could not be
 * performed. Pair A owns this file from here on.
 *
 * Renders /api/recommend exactly as the API returns it. Two rules from
 * MVP_BUILD_PLAN.md are load-bearing here and must not be "tidied away":
 *
 *   1. Never silently resolve a contradiction. CONTRADICTORY_SOURCES shows
 *      BOTH values, BOTH source URLs, BOTH dates.
 *   2. INSUFFICIENT_DATA is used honestly -- "not published" rather than an
 *      invented threshold.
 */
import { useState } from "react";

import ProvenanceChips from "../components/ProvenanceChips";
import { api, isStructuredDetail } from "../lib/api";

// Verdicts are a closed set from schemas.Verdict. Colour and copy per verdict,
// so the reveal reads differently from a plain rejection.
const VERDICT = {
  ELIGIBLE: {
    label: "Eligible",
    chip: "bg-emerald-100 text-emerald-900 border-emerald-300",
    card: "border-emerald-300",
  },
  CONTRADICTORY_SOURCES: {
    label: "Sources disagree",
    chip: "bg-amber-100 text-amber-900 border-amber-400",
    card: "border-amber-400 ring-1 ring-amber-200",
  },
  INSUFFICIENT_DATA: {
    label: "Not published",
    chip: "bg-stone-100 text-stone-700 border-stone-300",
    card: "border-stone-300",
  },
  NOT_ELIGIBLE: {
    label: "Not eligible",
    chip: "bg-red-100 text-red-900 border-red-300",
    card: "border-stone-300",
  },
};

const FIELDS = [
  { key: "family_income", label: "Annual family income (Rs)", required: true },
  { key: "age", label: "Age (optional)" },
  { key: "amount_needed", label: "Amount needed (Rs, optional)" },
];

const toIntOrNull = (v) => {
  if (v === "" || v == null) return null;
  const n = Number.parseInt(v, 10);
  return Number.isFinite(n) && n >= 0 ? n : null;
};

// The demo value. MVP_BUILD_PLAN.md beat 2: enter 4,20,000 and the
// contradiction fires.
const REVEAL_INCOME = "420000";

function ConditionRow({ c }) {
  // passed === null means INSUFFICIENT_DATA for this leaf, which is a third
  // state -- not a failure. Rendering it as a cross would be a lie.
  const mark =
    c.passed === true ? "✓" : c.passed === false ? "✗" : "?";
  const markClass =
    c.passed === true
      ? "text-emerald-700"
      : c.passed === false
        ? "text-red-700"
        : "text-stone-400";

  return (
    <li className="border-t border-stone-100 py-3 first:border-t-0">
      <div className="flex items-start gap-2">
        <span className={`mt-0.5 font-bold ${markClass}`} aria-hidden="true">
          {mark}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm text-stone-800">{c.human_text}</p>

          {(c.actual || c.threshold) && (
            <p className="mt-0.5 text-xs text-stone-500">
              {c.actual ? `You: ${c.actual}` : null}
              {c.actual && c.threshold ? " · " : null}
              {c.threshold ? `Rule: ${c.threshold}` : null}
            </p>
          )}

          {c.counterfactual && (
            <p className="mt-1 text-xs italic text-stone-600">{c.counterfactual}</p>
          )}

          {/* No provenance at all is itself the honest signal for
              INSUFFICIENT_DATA: there is no page we could cite. */}
          {c.provenance?.length ? (
            <ProvenanceChips provenance={c.provenance} />
          ) : (
            <p className="mt-1 text-xs text-stone-400">
              No published source found for this rule.
            </p>
          )}
        </div>
      </div>
    </li>
  );
}

function MatchCard({ m }) {
  const v = VERDICT[m.verdict] ?? VERDICT.NOT_ELIGIBLE;
  return (
    <div className={`rounded-lg border bg-white p-6 ${v.card}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold">{m.scheme_name}</h3>
          <p className="text-xs text-stone-500">{m.scheme_id}</p>
        </div>
        <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${v.chip}`}>
          {v.label}
        </span>
      </div>

      {(m.max_loan != null || m.interest_rate != null) && (
        <p className="mt-2 text-sm text-stone-600">
          {m.max_loan != null && `Up to Rs ${m.max_loan.toLocaleString("en-IN")}`}
          {m.max_loan != null && m.interest_rate != null && " · "}
          {m.interest_rate != null && `${m.interest_rate}% per annum`}
        </p>
      )}

      {/* THE REVEAL. Never collapse this into one number. */}
      {m.disagreement_note && (
        <p className="mt-3 rounded-md border border-amber-400 bg-amber-50 p-3 text-sm text-amber-900">
          {m.disagreement_note}
        </p>
      )}

      <ul className="mt-3">
        {(m.conditions ?? []).map((c, i) => (
          <ConditionRow key={`${c.condition_id}-${i}`} c={c} />
        ))}
      </ul>
    </div>
  );
}

export default function Recommender() {
  const [values, setValues] = useState({
    family_income: "",
    age: "",
    amount_needed: "",
  });
  const [caste, setCaste] = useState("SC");
  const [gender, setGender] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const canSubmit = !loading && toIntOrNull(values.family_income) !== null;

  async function submit(overrideIncome = null) {
    const income = toIntOrNull(overrideIncome ?? values.family_income);
    if (income === null) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await api.recommend({
          family_income: income,
          caste_category: caste,
          // The backend requires these; the seeded rules are national, so the
          // values do not change the verdict today. Sent honestly rather than
          // faked as a specific district.
          state_code: "KA",
          district_code: "29",
          ...(toIntOrNull(values.age) !== null ? { age: toIntOrNull(values.age) } : {}),
          ...(toIntOrNull(values.amount_needed) !== null
            ? { amount_needed: toIntOrNull(values.amount_needed) }
            : {}),
          ...(gender ? { gender } : {}),
        }),
      );
    } catch (e) {
      const detail = e?.detail;
      setError(
        isStructuredDetail(detail) && detail.message
          ? detail.message
          : e?.status === 0
            ? "Could not reach the API. Is the backend running?"
            : (e?.message ?? "unknown error"),
      );
    } finally {
      setLoading(false);
    }
  }

  function runReveal() {
    setValues((v) => ({ ...v, family_income: REVEAL_INCOME }));
    submit(REVEAL_INCOME);
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border bg-white p-8">
        <p className="text-xs uppercase tracking-wide text-stone-400">Pair A</p>
        <h2 className="mt-1 text-xl font-semibold">Smart Scheme Recommender</h2>
        <p className="mt-1 text-sm text-stone-600">
          Every condition below is evaluated separately and carries the page it
          came from, the authority that published it, and the date we fetched it.
        </p>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
                placeholder={f.key === "family_income" ? "420000" : "—"}
                className="mt-1 w-full rounded-md border border-stone-300 p-2 text-sm
                           focus:border-stone-500 focus:outline-none"
              />
            </div>
          ))}

          <div>
            <label htmlFor="caste" className="block text-sm font-medium text-stone-700">
              Caste category
            </label>
            <select
              id="caste"
              value={caste}
              onChange={(e) => setCaste(e.target.value)}
              className="mt-1 w-full rounded-md border border-stone-300 p-2 text-sm
                         focus:border-stone-500 focus:outline-none"
            >
              <option value="SC">SC</option>
              <option value="ST">ST</option>
              <option value="OBC">OBC</option>
              <option value="GEN">General</option>
            </select>
          </div>

          <div>
            <label htmlFor="gender-r" className="block text-sm font-medium text-stone-700">
              Gender (optional)
            </label>
            <select
              id="gender-r"
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="mt-1 w-full rounded-md border border-stone-300 p-2 text-sm
                         focus:border-stone-500 focus:outline-none"
            >
              <option value="">Not specified</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => submit()}
            disabled={!canSubmit}
            className="rounded-md bg-stone-800 px-4 py-2 text-sm font-medium text-white
                       hover:bg-stone-700 disabled:cursor-not-allowed disabled:bg-stone-300"
          >
            {loading ? "Matching…" : "Find schemes"}
          </button>
          {/* Demo affordance: one click to the beat-2 reveal, so nobody has to
              type six digits correctly on stage. */}
          <button
            type="button"
            onClick={runReveal}
            disabled={loading}
            className="rounded-md border border-amber-400 bg-amber-50 px-3 py-2 text-sm
                       font-medium text-amber-900 hover:bg-amber-100
                       disabled:cursor-not-allowed disabled:opacity-50"
          >
            Use Rs 4,20,000
          </button>
          <p className="text-xs text-stone-500">
            At Rs 4,20,000 the government sources disagree with each other.
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-6">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {result && (
        <>
          {/* Honesty flag straight from the API. */}
          {result.seeded && (
            <p className="rounded-md border border-stone-300 bg-stone-50 p-3 text-xs text-stone-600">
              Prototype data: these scheme rules were entered by hand from the
              published pages linked on each condition, not crawled
              automatically. The schema is designed to re-crawl and version.
            </p>
          )}

          {result.matches?.length === 0 ? (
            <div className="rounded-lg border border-dashed bg-white p-8 text-sm text-stone-500">
              No schemes matched this profile.
            </div>
          ) : (
            <div className="space-y-4">
              {result.matches.map((m) => (
                <MatchCard key={m.scheme_id} m={m} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
