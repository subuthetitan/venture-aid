const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export { BASE };

/**
 * Error carrying the parsed response body.
 *
 * req() used to throw `new Error("<status> <path>")` and DISCARD the body,
 * which is why SanctionReady.jsx grew its own duplicate fetch: the backend's
 * activity errors carry a `supported_activities` list the UI renders as
 * recovery chips, and that was unreachable through api.js. Now every caller
 * gets `status` and `detail`, so pages do not have to bypass this module.
 */
export class ApiError extends Error {
  constructor(status, path, detail) {
    super(`${status} ${path}`);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
    // FastAPI's error body is {"detail": ...}. `detail` is an OBJECT for our
    // hand-raised HTTPExceptions and an ARRAY for FastAPI's own validation
    // errors, so callers must check which they got before reading fields.
    this.detail = detail;
  }
}

/** True when `detail` is one of our structured errors rather than a FastAPI
 *  validation array. Keyed off the shape, so a new error code with the same
 *  shape still renders usefully. */
export const isStructuredDetail = (detail) =>
  Boolean(detail) && !Array.isArray(detail) && typeof detail === "object";

async function req(path, opts = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
  } catch (cause) {
    // Network failure, CORS, server unreachable. status 0 distinguishes this
    // from an HTTP error so the UI can say "cannot reach the server".
    const err = new ApiError(0, path, null);
    err.cause = cause;
    throw err;
  }

  if (!res.ok) {
    let detail = null;
    try {
      detail = (await res.json())?.detail ?? null;
    } catch {
      // Non-JSON error body (proxy error page, gateway timeout).
    }
    throw new ApiError(res.status, path, detail);
  }
  return res.json();
}

export const api = {
  recommend: (profile) =>
    req("/api/recommend", { method: "POST", body: JSON.stringify(profile) }),
  contradictions: () => req("/api/truth/contradictions"),
  schemes: () => req("/api/calculate/schemes"),
  calculate: (body) =>
    req("/api/calculate", { method: "POST", body: JSON.stringify(body) }),
  readiness: (body) =>
    req("/api/readiness", { method: "POST", body: JSON.stringify(body) }),
  // encodeURIComponent: a district code with a '&' or '#' in it silently
  // truncated or corrupted the query string before this.
  channels: (district) =>
    req(`/api/locator/channels?district_code=${encodeURIComponent(district ?? "")}`),
  reachability: () => req("/api/locator/reachability"),
  ledger: () => req("/api/ledger"),
  // Pair C's route lookup. to_channel_id is encoded for the same reason
  // district_code above is: channel ids come from the database, and an
  // unencoded '&' or '#' in one silently truncates the query string. The
  // coordinates are encoded too so a NaN or undefined cannot inject a bare
  // '&' into the URL.
  route: ({ from_lat, from_lon, to_channel_id }) =>
    req(
      `/api/locator/route?from_lat=${encodeURIComponent(from_lat)}` +
        `&from_lon=${encodeURIComponent(from_lon)}` +
        `&to_channel_id=${encodeURIComponent(to_channel_id)}`,
    ),
};
