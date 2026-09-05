import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { loadDistricts } from "../lib/districts";

export default function Ledger() {
  const [data, setData] = useState(null);
  const [districts, setDistricts] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDistricts().then(setDistricts).catch(() => setDistricts(null));
    api.ledger().then(setData).catch((e) => setError(e.message));
  }, []);

  const cells = data?.cells ?? [];

  return (
    <div className="max-w-3xl">
      <h2 className="text-xl font-semibold">Transparency Ledger</h2>

      <div className="mt-3 p-3 rounded border-2 border-amber-600 bg-amber-50">
        <p className="text-sm font-semibold text-amber-800">
          Prototype data - synthetic
        </p>
        <p className="text-sm mt-1 text-stone-800">
          {data?.caveat ?? "Prototype data. Self-reported and self-selected."}{" "}
          These records are generated, not observed. No Indian government credit
          scheme we could find publishes an application-to-sanction funnel - there
          is no denominator anywhere, including for the government itself. This is
          what it would look like if there were.
        </p>
      </div>

      {error && <p className="mt-6 text-sm text-red-700">Could not load: {error}</p>}
      {!data && !error && <p className="mt-6 text-sm text-stone-500">Loading...</p>}

      {data && (
        <>
          <table className="mt-6 w-full text-sm">
            <thead>
              <tr className="border-b border-stone-300 text-left text-stone-500">
                <th className="py-2 font-medium">District</th>
                <th className="py-2 font-medium">Applications logged</th>
                <th className="py-2 font-medium">Median days to sanction</th>
              </tr>
            </thead>
            <tbody>
              {cells.map((c) => (
                <tr key={c.district_code} className="border-b border-stone-200">
                  <td className="py-2">
                    {districts?.districtName(c.district_code) ?? c.district_code}
                  </td>
                  {c.suppressed ? (
                    <td colSpan={2} className="py-2 italic text-stone-400">
                      Suppressed - fewer than 5 records
                    </td>
                  ) : (
                    <>
                      <td className="py-2">{c.applications}</td>
                      <td className="py-2">{c.median_days_to_sanction ?? "-"}</td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>

          <p className="mt-4 text-xs text-stone-500">
            Districts with fewer than five records are suppressed entirely
            (k-anonymity), rather than shown with a small-sample figure. No
            rejection rate is published here: the generator produces rejected
            applications so the pipeline terminates, but there is no ground truth
            anywhere in India to validate such a figure against.
          </p>
        </>
      )}
    </div>
  );
}