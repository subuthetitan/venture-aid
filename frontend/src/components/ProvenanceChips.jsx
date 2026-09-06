/**
 * Provenance display, shared by Recommender and TruthLayer.
 *
 * MVP_BUILD_PLAN.md: "Every condition renders a provenance chip: source ·
 * authority · fetched on". The URL is a real anchor on purpose -- the demo
 * hands a judge a phone and lets them open both sources, so these must be
 * clickable, not decorative text.
 */

/** 'https://nsfdc.nic.in/en/how-to-apply' -> 'nsfdc.nic.in/en/how-to-apply' */
function prettyUrl(url) {
  try {
    const u = new URL(url);
    return `${u.hostname}${u.pathname}`.replace(/\/$/, "");
  } catch {
    return url;
  }
}

/** '2026-09-03T00:00:00' and '2026-09-03' both -> '2026-09-03'. */
export function isoDate(value) {
  if (typeof value !== "string") return null;
  const d = value.split("T")[0];
  return /^\d{4}-\d{2}-\d{2}$/.test(d) ? d : value;
}

export default function ProvenanceChips({ provenance }) {
  if (!Array.isArray(provenance) || provenance.length === 0) return null;

  return (
    <ul className="mt-2 flex flex-wrap gap-2">
      {provenance.map((p, i) => (
        <li
          key={`${p.source_url}-${i}`}
          className="rounded border border-stone-200 bg-stone-50 px-2 py-1 text-xs"
        >
          <a
            href={p.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-stone-700 underline decoration-stone-400
                       underline-offset-2 hover:text-stone-900"
          >
            {prettyUrl(p.source_url)}
          </a>
          <span className="text-stone-500">
            {" · "}
            {p.source_authority}
            {" · fetched "}
            {isoDate(p.observed_at)}
            {p.effective_from ? ` · effective ${isoDate(p.effective_from)}` : ""}
          </span>
        </li>
      ))}
    </ul>
  );
}
