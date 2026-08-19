/**
 * The audit ledger.
 *
 * Append-only, newest first. Every row carries the model version, the hash of
 * the feature set, and the hash of the exact inputs, so a decision can be
 * verified years later against the record of how it was made -- and any
 * tampering with the stored inputs shows up as a hash that no longer matches.
 */

import { fmt } from "../api.js";

export default function Ledger({ entries, loading, error }) {
  return (
    <div className="pane">
      <div className="pane-head">
        <h2>Decision ledger</h2>
        <span className="spacer" />
        <span className="section-note">
          Append-only · {entries.length} record{entries.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="pane-body">
        {error && <div className="banner error" style={{ margin: 12 }}>{error}</div>}
        {loading && entries.length === 0 && (
          <div className="empty">Loading ledger…</div>
        )}
        {!loading && entries.length === 0 && !error && (
          <div className="empty">
            <strong>The ledger is empty</strong>
            Every decision writes a permanent record here.
          </div>
        )}

        {entries.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Recorded</th>
                <th>Outcome</th>
                <th>PD</th>
                <th>Thresholds</th>
                <th>Model</th>
                <th>Input hash</th>
                <th>Reasons</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry, index) => (
                <tr key={`${entry.decision_id}-${index}`}>
                  <td className="mono">{fmt.time(entry.recorded_at)}</td>
                  <td>
                    <span className={`verdict ${entry.outcome.replace("OVERRIDE:", "")}`}>
                      {entry.outcome}
                    </span>
                  </td>
                  <td className="mono">
                    {fmt.percent(entry.probability_of_default, 2)}
                  </td>
                  <td className="mono">
                    {fmt.percent(entry.approve_threshold, 0)} /{" "}
                    {fmt.percent(entry.refer_threshold, 0)}
                  </td>
                  <td className="mono" title={entry.model_version}>
                    {entry.feature_set_hash}
                  </td>
                  <td className="mono" title={entry.input_hash}>
                    {entry.input_hash?.slice(0, 12)}…
                  </td>
                  <td className="mono">
                    {(entry.reason_codes || [])
                      .map((reason) => reason.code)
                      .join(" ") || "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
