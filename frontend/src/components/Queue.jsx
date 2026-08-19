/**
 * The application queue.
 *
 * Each row carries the evidence ticks, so an underwriter scanning the list sees
 * at a glance which applicants a conventional lender would have had nothing to
 * work with -- before opening a single file.
 */

import { fmt } from "../api.js";
import EvidenceBar from "./EvidenceBar.jsx";

export default function Queue({
  items,
  selectedId,
  onSelect,
  filters,
  onFilterChange,
  loading,
  error,
}) {
  return (
    <div className="pane">
      <div className="pane-head">
        <h2>Queue</h2>
        <span className="spacer" />
        <div className="filters">
          <select
            aria-label="Filter by outcome"
            value={filters.outcome}
            onChange={(event) =>
              onFilterChange({ ...filters, outcome: event.target.value })
            }
          >
            <option value="">All outcomes</option>
            <option value="APPROVE">Approved</option>
            <option value="REFER">Referred</option>
            <option value="DECLINE">Declined</option>
          </select>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={filters.thinFileOnly}
              onChange={(event) =>
                onFilterChange({ ...filters, thinFileOnly: event.target.checked })
              }
            />
            Thin file
          </label>
        </div>
      </div>

      <div className="pane-body">
        {error && <div className="banner error" style={{ margin: 12 }}>{error}</div>}

        {loading && items.length === 0 && (
          <div className="empty">Loading applications…</div>
        )}

        {!loading && items.length === 0 && !error && (
          <div className="empty">
            <strong>Nothing in the queue yet</strong>
            Score an application to see it here.
          </div>
        )}

        {items.map((item) => (
          <button
            key={item.decision_id}
            className="queue-row"
            aria-current={item.decision_id === selectedId}
            onClick={() => onSelect(item.decision_id)}
          >
            <span className="queue-row-top">
              <span className="queue-name">{item.applicant_name}</span>
              <span className={`verdict ${item.outcome}`}>{item.outcome}</span>
            </span>
            <span className="queue-meta">
              <span className="mono">{fmt.currency(item.requested_amount)}</span>
              <span className="mono">
                PD {fmt.percent(item.probability_of_default, 1)}
              </span>
              {item.is_thin_file && <span className="thin-tag">Thin file</span>}
              {item.fraud_verdict !== "PASS" && (
                <span className={`verdict ${item.fraud_verdict}`}>
                  {item.fraud_verdict}
                </span>
              )}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
