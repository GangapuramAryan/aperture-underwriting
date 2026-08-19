/**
 * Single point of contact with the decision API.
 *
 * Vite proxies /v1 and /health to the backend in development, so the browser
 * stays on one origin and no CORS preflight is involved. Every call funnels
 * through `request` so error handling is uniform: FastAPI returns validation
 * failures as a `detail` array, which is flattened into one readable message
 * rather than surfacing "[object Object]" to the underwriter.
 */

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (Array.isArray(body.detail)) {
        message = body.detail
          .map((item) => `${(item.loc || []).slice(-1)[0]}: ${item.msg}`)
          .join("; ");
      } else if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Response carried no JSON body; the status line is the best we have.
    }
    throw new Error(message);
  }
  return response.json();
}

export const api = {
  health: () => request("/health"),

  queue: ({ outcome = "", thinFileOnly = false, limit = 50 } = {}) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (outcome) params.set("outcome", outcome);
    if (thinFileOnly) params.set("thin_file_only", "true");
    return request(`/v1/queue?${params}`);
  },

  decision: (id) => request(`/v1/decisions/${id}`),

  decide: (payload) =>
    request("/v1/decisions", { method: "POST", body: JSON.stringify(payload) }),

  override: (id, payload) =>
    request(`/v1/decisions/${id}/override`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  ledger: ({ limit = 100 } = {}) => request(`/v1/ledger?limit=${limit}`),
};

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------
// Absent values are rendered as an explicit em dash rather than 0. A blank
// bureau score means "unknown", and showing zero would assert something false
// about the applicant -- the same principle the model follows internally.

export const fmt = {
  currency: (value) =>
    value === null || value === undefined
      ? "—"
      : `₹${Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`,

  percent: (value, digits = 1) =>
    value === null || value === undefined
      ? "—"
      : `${(Number(value) * 100).toFixed(digits)}%`,

  number: (value, digits = 2) =>
    value === null || value === undefined
      ? "—"
      : Number(value).toLocaleString("en-IN", { maximumFractionDigits: digits }),

  time: (value) =>
    value
      ? new Date(value).toLocaleString("en-IN", {
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "—",

  featureName: (key) =>
    key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()),
};
