const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

export const api = {
  recommend: (profile) =>
    req("/api/recommend", { method: "POST", body: JSON.stringify(profile) }),
  contradictions: () => req("/api/truth/contradictions"),
  calculate: (body) =>
    req("/api/calculate", { method: "POST", body: JSON.stringify(body) }),
  readiness: (body) =>
    req("/api/readiness", { method: "POST", body: JSON.stringify(body) }),
  channels: (district) => req(`/api/locator/channels?district_code=${district}`),
  reachability: () => req("/api/locator/reachability"),
  ledger: () => req("/api/ledger"),
};
