/**
 * PAIR A's screen. Built by Pair B during integration at the team's request;
 * Pair A owns this file from here on.
 *
 * Renders /api/truth/contradictions -- the live_contradiction grouping over
 * rule_version. Every position that is currently live is shown side by side.
 *
 * THE RULE THIS SCREEN EXISTS TO ENFORCE (README, "Rules that are not
 * negotiable"): never silently resolve a contradiction. When two government
 * sources disagree, show both values, both URLs, both dates. There is
 * deliberately no "recommended value", no majority vote, and no sort that
 * implies one source outranks another.
 */
import { useEffect, useState } from "react";

import { isoDate } from "../components/ProvenanceChips";
import { api, isStructuredDetail } from "../lib/api";

/** rule_version.value is JSONB. Today every seeded row is {"amount": n} or
 *  {"allowed": [...]}, but the column is free-form, so render defensively
 *  rather than assuming a shape. */
function formatValue(value) {
  if (value == null) return "—";
  if (typeof value !== "object") return String(value);
  if (typeof value.amount === "number") {
    return `Rs ${value.amount.toLocaleString("en-IN")}`;
  }
  if (Array.isArray(value.allowed)) return value.allowed.join(", ");
  return JSON.stringify(value);
}

/** 'family_income_ceiling' -> 'Family income ceiling' */
const humanField = (f) =>
  String(f).replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

function Contradiction({ c }) {
  const positions = Array.isArray(c.positions) ? c.positions : [];
  // Distinct values is the point: 3 sources can hold 2 positions.
  const distinct = new Set(positions.map((p) => JSON.stringify(p.value))).size;

  return (
    <div className="rounded-lg border border-amber-400 bg-white p-6 ring-1 ring-amber-200">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-semibold">
            {c.scheme_name ?? c.scheme_id}
          </h3>
          <p className="text-xs text-stone-500">
            {humanField(c.field)} · {c.scheme_id}
          </p>
        </div>
        <span className="rounded-full border border-amber-400 bg-amber-100 px-2.5 py-0.5
                         text-xs font-medium text-amber-900">
          {distinct} different values live
        </span>
      </div>

      <p className="mt-3 text-sm text-stone-700">
        These pages are all currently published by the Government of India and
        they do not agree. We show every one of them rather than picking a
        winner.
      </p>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[36rem] text-sm">
          <thead>
            <tr className="border-b text-left text-stone-500">
              <th className="py-1 pr-3 font-medium">Value</th>
              <th className="py-1 pr-3 font-medium">Authority</th>
              <th className="py-1 pr-3 font-medium">Source</th>
              <th className="py-1 pr-3 font-medium">Fetched</th>
              <th className="py-1 font-medium">Effective from</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p, i) => (
              <tr key={`${p.source}-${i}`} className="border-b border-stone-100 align-top">
                <td className="py-2 pr-3 font-semibold text-stone-900">
                  {formatValue(p.value)}
                </td>
                <td className="py-2 pr-3 text-stone-600">{p.authority}</td>
                <td className="py-2 pr-3">
                  {/* Clickable on purpose: the demo hands a judge a phone and
                      lets them open these. */}
                  <a
                    href={p.source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="break-all text-stone-700 underline decoration-stone-400
                               underline-offset-2 hover:text-stone-900"
                  >
                    {p.source}
                  </a>
                </td>
                <td className="py-2 pr-3 whitespace-nowrap text-stone-600">
                  {isoDate(p.observed_at) ?? "—"}
                </td>
                <td className="py-2 whitespace-nowrap text-stone-600">
                  {p.effective_from ? isoDate(p.effective_from) : "not stated"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function TruthLayer() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    api
      .contradictions()
      .then((d) => live && setData(Array.isArray(d) ? d : []))
      .catch((e) => {
        if (!live) return;
        const detail = e?.detail;
        setError(
          isStructuredDetail(detail) && detail.message
            ? detail.message
            : e?.status === 0
              ? "Could not reach the API. Is the backend running?"
              : (e?.message ?? "unknown error"),
        );
      });
    return () => {
      live = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border bg-white p-8">
        <p className="text-xs uppercase tracking-wide text-stone-400">Pair A</p>
        <h2 className="mt-1 text-xl font-semibold">Scheme Truth Layer</h2>
        <p className="mt-2 text-sm text-stone-600">
          Every scheme rule is stored append-only with the page it came from and
          the date we read it. Supersession is scoped to a single URL, so when
          two <em>different</em> official pages publish different values, both
          stay live — and that is what this screen lists.
        </p>
        <p className="mt-2 text-xs text-stone-500">
          A contradiction here is a normal state of the data, not an error in
          our pipeline.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-6">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {!data && !error && (
        <p className="text-sm text-stone-500">Loading…</p>
      )}

      {data?.length === 0 && (
        <div className="rounded-lg border border-dashed bg-white p-8">
          <p className="text-sm text-stone-600">
            No live contradictions in the current rule set.
          </p>
          <p className="mt-1 text-xs text-stone-500">
            If you expected one, the Truth Layer seed may not have run — check
            the API logs for the seed warning.
          </p>
        </div>
      )}

      {data?.length > 0 && (
        <div className="space-y-4">
          {data.map((c) => (
            <Contradiction key={`${c.scheme_id}-${c.field}`} c={c} />
          ))}
        </div>
      )}

      <p className="rounded-md border border-stone-300 bg-stone-50 p-3 text-xs text-stone-600">
        Prototype data: these rows were entered by hand from the pages linked
        above, each with its real URL and real fetch date. The schema is
        designed to re-crawl and version; the crawler is not built yet.
      </p>
    </div>
  );
}
