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

  // Home Credit anonymises the provenance of its external scores, so calling
  // them "bureau score" would claim more than the data supports. Applicants
  // with no bureau file can still carry one.
  featureName: (key) =>
    ({
      bureau_score: "External Score 2",
      ext_source_1: "External Score 1",
      ext_source_3: "External Score 3",
      ecom_txn_count_90d: "Card Transactions (90d)",
      telecom_recharge_cadence_days: "Payment Timing (days late)",
    })[key] ||
    key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase()),
};
