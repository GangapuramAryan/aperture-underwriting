/**
 * Score a new application.
 *
 * The three presets are the argument of the product, made clickable. They are
 * not decoration: the first is the case a conventional lender gets wrong, the
 * second is the case it gets right, and the third is the case where good credit
 * behaviour must not be allowed to outweigh a fraud signal.
 *
 * Editing is limited to the fields that carry the story. Sending the full
 * twenty-four-field payload through a form would take longer to fill than it
 * takes to explain, and the preset already establishes a coherent applicant.
 */

import { useState } from "react";

import { api, fmt } from "../api.js";

const PRESETS = {
  thin: {
    label: "Thin file, strong behaviour",
    note: "No bureau record. Rent, utilities and cashflow all excellent. A conventional model has nothing to score and declines.",
    payload: {
      applicant_name: "Priya Sharma",
      requested_amount: 150000,
      income_annual: 420000,
      employment_years: 1.5,
      debt_to_income: 1.8,
      age_years: 24,
      loan_amount: 150000,
      loan_term_months: 24,
      credit_history_months: 4,
      bureau_active_accounts: 0,
      bureau_closed_accounts: 0,
      utility_ontime_ratio: 0.96,
      rent_ontime_ratio: 0.98,
      salary_credit_consistency: 0.88,
      cashflow_inflow_regularity: 0.99,
      cashflow_volatility: 0.12,
      avg_monthly_balance: 38000,
      balance_trend_90d: -0.05,
      telecom_recharge_cadence_days: -2,
      ecom_txn_count_90d: 22,
      device_tenure_days: 900,
      form_correction_count: 2,
      pan_field_pasted: false,
      session_duration_seconds: 310,
      applications_per_device_30d: 1,
      hour_of_day: 14,
      geo_velocity_kmh: 12,
    },
  },
  thick: {
    label: "Established file, weakening",
    note: "Long bureau history, but arrears on record, rising balances and irregular payments.",
    payload: {
      applicant_name: "Rakesh Menon",
      requested_amount: 400000,
      income_annual: 900000,
      employment_years: 11,
      debt_to_income: 3.4,
      age_years: 43,
      loan_amount: 400000,
      loan_term_months: 48,
      bureau_score: 612,
      ext_source_1: 0.24,
      ext_source_3: 0.29,
      bureau_active_accounts: 6,
      bureau_closed_accounts: 5,
      bureau_max_days_overdue: 74,
      bureau_total_debt: 2100000,
      credit_history_months: 168,
      utility_ontime_ratio: 0.61,
      rent_ontime_ratio: 0.58,
      salary_credit_consistency: 0.31,
      cashflow_inflow_regularity: 0.72,
      cashflow_volatility: 0.94,
      avg_monthly_balance: 21000,
      balance_trend_90d: 1.4,
      telecom_recharge_cadence_days: 19,
      ecom_txn_count_90d: 9,
      device_tenure_days: 210,
      form_correction_count: 3,
      pan_field_pasted: false,
      session_duration_seconds: 280,
      applications_per_device_30d: 1,
      hour_of_day: 11,
      geo_velocity_kmh: 30,
    },
  },
  fraud: {
    label: "Good credit, fraud signals",
    note: "The credit profile looks fine. The session does not: seven applications from one device, implausible travel, identity number pasted.",
    payload: {
      applicant_name: "Unverified Applicant",
      requested_amount: 250000,
      income_annual: 800000,
      employment_years: 6,
      debt_to_income: 1.1,
      age_years: 33,
      loan_amount: 250000,
      loan_term_months: 36,
      bureau_score: 742,
      ext_source_1: 0.71,
      ext_source_3: 0.68,
      bureau_active_accounts: 3,
      bureau_closed_accounts: 2,
      bureau_max_days_overdue: 0,
      bureau_total_debt: 380000,
      credit_history_months: 96,
      utility_ontime_ratio: 0.99,
      rent_ontime_ratio: 0.99,
      salary_credit_consistency: 0.93,
      cashflow_inflow_regularity: 1.0,
      cashflow_volatility: 0.08,
      avg_monthly_balance: 96000,
      balance_trend_90d: -0.1,
      telecom_recharge_cadence_days: -3,
      ecom_txn_count_90d: 31,
      device_tenure_days: 1400,
      form_correction_count: 14,
      pan_field_pasted: true,
      session_duration_seconds: 19,
      applications_per_device_30d: 7,
      hour_of_day: 3,
      geo_velocity_kmh: 820,
    },
  },
};

const EDITABLE = [
  { key: "applicant_name", label: "Applicant name", type: "text" },
  { key: "requested_amount", label: "Requested amount (₹)", type: "number" },
  { key: "income_annual", label: "Annual income (₹)", type: "number" },
  { key: "credit_history_months", label: "Credit history (months)", type: "number" },
  { key: "bureau_score", label: "Bureau score (blank if none)", type: "number" },
  { key: "utility_ontime_ratio", label: "Utility bills paid on time (0–1)", type: "number" },
  { key: "rent_ontime_ratio", label: "Rent paid on time (0–1)", type: "number" },
  { key: "applications_per_device_30d", label: "Applications from device (30d)", type: "number" },
];

export default function NewApplication({ onScored }) {
  const [presetKey, setPresetKey] = useState("thin");
  const [form, setForm] = useState(PRESETS.thin.payload);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  function choosePreset(key) {
    setPresetKey(key);
    setForm(PRESETS[key].payload);
    setResult(null);
    setError(null);
  }

  function update(key, rawValue, type) {
    setForm((current) => {
      const next = { ...current };
      if (type === "number") {
        // An empty box means "not on file", which is a distinct state from
        // zero and must be sent as an absence, not a value.
        if (rawValue === "") delete next[key];
        else next[key] = Number(rawValue);
      } else {
        next[key] = rawValue;
      }
      return next;
    });
  }

  async function score() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const decision = await api.decide(form);
      setResult(decision);
      onScored?.(decision.decision_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="pane">
      <div className="pane-head">
        <h2>Score an application</h2>
      </div>

      <div className="pane-body pad">
        <div className="section-head">
          <h4>Scenario</h4>
        </div>
        <div style={{ display: "grid", gap: 6, marginBottom: 16 }}>
          {Object.entries(PRESETS).map(([key, preset]) => (
            <button
              key={key}
              className={`btn ${presetKey === key ? "" : "ghost"} small`}
              style={{ textAlign: "left", padding: "8px 11px" }}
              onClick={() => choosePreset(key)}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <p className="section-note" style={{ marginTop: 0, marginBottom: 18 }}>
          {PRESETS[presetKey].note}
        </p>

        {EDITABLE.map((field) => (
          <div className="field" key={field.key}>
            <label htmlFor={`f-${field.key}`}>{field.label}</label>
            <input
              id={`f-${field.key}`}
              type={field.type}
              step="any"
              value={form[field.key] ?? ""}
              onChange={(event) =>
                update(field.key, event.target.value, field.type)
              }
            />
          </div>
        ))}

        {error && <div className="banner error">{error}</div>}

        <button className="btn" onClick={score} disabled={busy}>
          {busy ? "Scoring…" : "Score application"}
        </button>

        {result && (
          <div className="banner info" style={{ marginTop: 14 }}>
            <strong className="mono">{result.outcome}</strong> · PD{" "}
            {fmt.percent(result.probability_of_default, 2)} ·{" "}
            {result.approved_line
              ? `line ${fmt.currency(result.approved_line)}`
              : "no line offered"}{" "}
            · {fmt.number(result.latency_ms, 1)} ms
          </div>
        )}
      </div>
    </div>
  );
}
