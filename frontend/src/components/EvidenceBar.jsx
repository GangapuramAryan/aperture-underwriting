/**
 * Evidence ticks.
 *
 * The point of the product, drawn in about forty pixels: two rows of marks
 * standing for the evidence available in an applicant's file. The bureau row
 * counts traditional fields that are actually populated; the behavioural row
 * counts alternative-data fields.
 *
 * For a thin-file applicant the bureau row is nearly empty while the
 * behavioural row is full. A conventional lender reads only the top row and
 * declines. This system reads both.
 */

const BUREAU_FIELDS = [
  "bureau_score",
  "ext_source_1",
  "ext_source_3",
  "bureau_active_accounts",
  "bureau_closed_accounts",
  "bureau_max_days_overdue",
  "bureau_total_debt",
  "credit_history_months",
];

const BEHAVIOURAL_FIELDS = [
  "cashflow_inflow_regularity",
  "cashflow_volatility",
  "salary_credit_consistency",
  "avg_monthly_balance",
  "balance_trend_90d",
  "utility_ontime_ratio",
  "rent_ontime_ratio",
  "telecom_recharge_cadence_days",
  "ecom_txn_count_90d",
  "device_tenure_days",
];

/**
 * A field counts as evidence only if it carries a real value. Null, undefined
 * and NaN are absences. Zero counts -- "zero accounts on file" is a fact about
 * the applicant, not a gap in the record.
 */
function countPresent(features, fields) {
  return fields.filter((field) => {
    const value = features?.[field];
    return value !== null && value !== undefined && !Number.isNaN(value);
  }).length;
}

function TickRow({ label, filled, total, variant }) {
  return (
    <div className="evidence-line">
      <span className="evidence-label">{label}</span>
      <span className="ticks" role="img" aria-label={`${filled} of ${total} present`}>
        {Array.from({ length: total }, (_, index) => (
          <span
            key={index}
            className={
              index < filled ? `tick filled ${variant}` : "tick"
            }
          />
        ))}
      </span>
      <span className="evidence-count">
        {filled}/{total}
      </span>
    </div>
  );
}

export default function EvidenceBar({ features }) {
  const bureau = countPresent(features, BUREAU_FIELDS);
  const behavioural = countPresent(features, BEHAVIOURAL_FIELDS);

  return (
    <div className="evidence">
      <TickRow
        label="Bureau"
        filled={bureau}
        total={BUREAU_FIELDS.length}
        variant="bureau"
      />
      <TickRow
        label="Behavioural"
        filled={behavioural}
        total={BEHAVIOURAL_FIELDS.length}
        variant="behavioural"
      />
    </div>
  );
}
