/**
 * District lookup. The API returns census codes only, so every district name
 * shown in the UI resolves through here.
 *
 * Join key is `censuscode` from the DataMeet Census 2011 boundaries. We join on
 * the number, not the name, because the shapefile says Bangalore/Belgaum/Mysore
 * while the UI says Bengaluru/Belagavi/Mysuru.
 */
let cache = null;

export async function loadDistricts() {
  if (cache) return cache;

  const res = await fetch("/district_codes.json");
  if (!res.ok) throw new Error(`district_codes.json ${res.status}`);
  const data = await res.json();

  cache = {
    raw: data,
    byCode: Object.fromEntries(data.districts.map((d) => [d.district_code, d])),
    stateName: (code) => data.states[code]?.name ?? "Unknown",
    districtName: (code) =>
      data.districts.find((d) => d.district_code === code)?.name ?? `District ${code}`,
  };
  return cache;
}