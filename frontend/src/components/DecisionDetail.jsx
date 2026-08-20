/**
 * One decision, in full.
 *
 * The order of the page is the order an underwriter reasons in: what was
 * decided, on what evidence, for what stated reasons, with what fraud signal,
 * and then -- last -- the control to disagree with it.
 *
 * The override form demands a written justification because an override with no
 * recorded rationale is indistinguishable from an unexplained deviation when
 * the file is reviewed a year later.
 */

import { useState } from "react";

import { api, fmt } from "../api.js";
import Attribution from "./Attribution.jsx";
import EvidenceBar from "./EvidenceBar.jsx";
import Precedents from "./Precedents.jsx";

const MIN_JUSTIFICATION = 15;

function OverrideForm({ decision, onDone }) {
  const [outcome, setOutcome] = useState(
    decision.outcome === "APPROVE" ? "DECLINE" : "APPROVE"
  );
  const [underwriter, setUnderwriter] = useState("");
  const [justification, setJustification] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const ready =
    underwriter.trim().length > 0 &&
    justification.trim().length >= MIN_JUSTIFICATION;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.override(decision.decision_id, {
        underwriter: underwriter.trim(),
        new_outcome: outcome,
        justification: justification.trim(),
      });
      setJustification("");
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {error && <div className="banner error">{error}</div>}

      <div className="field">
        <label htmlFor="ov-underwriter">Underwriter</label>
        <input
          id="ov-underwriter"
          value={underwriter}
          onChange={(event) => setUnderwriter(event.target.value)}
          placeholder="Your name"
        />
      </div>

      <div className="field">
        <label htmlFor="ov-outcome">Change outcome to</label>
        <select
          id="ov-outcome"
          value={outcome}
          onChange={(event) => setOutcome(event.target.value)}
        >
          <option value="APPROVE">Approve</option>
          <option value="REFER">Refer</option>
          <option value="DECLINE">Decline</option>
        </select>
      </div>

      <div className="field">
        <label htmlFor="ov-why">
          Justification — recorded permanently against this file
        </label>
        <textarea
          id="ov-why"
          rows={3}
          value={justification}
          onChange={(event) => setJustification(event.target.value)}
          placeholder="What evidence supports departing from the model's decision?"
        />
        <span className="section-note">
          {justification.trim().length < MIN_JUSTIFICATION
            ? `${MIN_JUSTIFICATION - justification.trim().length} more characters needed`
            : "Ready to record"}
        </span>
      </div>

      <button className="btn" onClick={submit} disabled={!ready || busy}>
        {busy ? "Recording…" : "Record override"}
      </button>
    </div>
  );
}

export default function DecisionDetail({ decision, onRefresh }) {
  if (!decision) {
    return (
      <div className="pane">
        <div className="pane-head">
          <h2>Decision</h2>
        </div>
        <div className="empty">
          <strong>No application selected</strong>
          Choose an application from the queue, or score a new one.
        </div>
      </div>
    );
  }

  const reasons = decision.reasons || [];
  const overrides = decision.overrides || [];
  const features = decision.features || {};
  const bureauScoreAbsent =
    features.bureau_score === null || features.bureau_score === undefined;

  return (
    <div className="pane">
      <div className="pane-head">
        <h2>Decision</h2>
        <span className="spacer" />
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-faint)" }}>
          {decision.decision_id?.slice(0, 8)}
        </span>
      </div>

      <div className="pane-body">
        <div className="headline">
          <div className="headline-main">
            <h3>{decision.applicant_name}</h3>
            <div className="headline-sub">
              Requested {fmt.currency(decision.requested_amount)} ·{" "}
              {fmt.time(decision.decided_at)}
            </div>
            <div style={{ marginTop: 10, maxWidth: 320 }}>
              <EvidenceBar features={features} />
            </div>
          </div>
          <span className="spacer" />
          <div className="outcome-block">
            <div className={`outcome-word ${decision.outcome}`}>
              {decision.outcome}
            </div>
            {decision.is_thin_file && (
              <span className="thin-tag">Thin file</span>
            )}
          </div>
        </div>

        <div className="stat-strip">
          <div className="stat">
            <div className="stat-label">Default probability</div>
            <div className="stat-value">
              {fmt.percent(decision.probability_of_default, 2)}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Approved line</div>
            <div className="stat-value">
              {fmt.currency(decision.approved_line)}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Bureau score</div>
            <div className={`stat-value ${bureauScoreAbsent ? "absent" : ""}`}>
              {bureauScoreAbsent
                ? "none on file"
                : fmt.number(features.bureau_score, 0)}
            </div>
          </div>
          <div className="stat">
            <div className="stat-label">Decided in</div>
            <div className="stat-value">{fmt.number(decision.latency_ms, 1)} ms</div>
          </div>
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Principal reasons</h4>
            <span className="section-note">
              Disclosable under ECOA / Reg B · derived from SHAP attribution
            </span>
          </div>
          {reasons.length === 0 ? (
            <p className="section-note">
              No adverse factors carried material weight in this decision.
            </p>
          ) : (
            reasons.map((reason, index) => (
              <div className="reason" key={`${reason.code}-${index}`}>
                <span className="reason-code">{reason.code}</span>
                <span>
                  <div className="reason-statement">{reason.statement}</div>
                  <div className="reason-improvement">{reason.improvement}</div>
                  <div className="reason-evidence">
                    {reason.feature}
                    {reason.feature_value === null ||
                    reason.feature_value === undefined
                      ? " · not on file"
                      : ` = ${fmt.number(reason.feature_value, 3)}`}
                  </div>
                </span>
                <span className="reason-share">
                  {fmt.percent(reason.contribution_share, 0)}
                </span>
              </div>
            ))
          )}
        </div>

        <div className="section">
          <div className="section-head">
            <h4>What moved this decision</h4>
            <span className="section-note">Per-applicant SHAP contribution</span>
          </div>
          <Attribution attribution={decision.shap_attribution} />
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Comparable files</h4>
            <span className="section-note">
              Nearest applicants by vector similarity · pgvector
            </span>
          </div>
          <Precedents
            precedents={decision.precedents}
            summary={decision.precedent_summary || {}}
          />
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Fraud screen</h4>
            <span className={`verdict ${decision.fraud_verdict}`}>
              {decision.fraud_verdict}
            </span>
            <span className="section-note">
              score {fmt.number(decision.fraud_score, 2)}
            </span>
          </div>
          {decision.fraud_signals?.length ? (
            <ul className="signal-list">
              {decision.fraud_signals.map((signal) => (
                <li key={signal}>{signal}</li>
              ))}
            </ul>
          ) : (
            <p className="section-note">
              No behavioural fraud signals triggered.
            </p>
          )}
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Underwriter override</h4>
            <span className="section-note">
              The model's original decision is never overwritten
            </span>
          </div>

          {overrides.length > 0 && (
            <div style={{ marginBottom: 14 }}>
              {overrides.map((override, index) => (
                <div className="override-log" key={index}>
                  <strong>{override.underwriter}</strong> changed{" "}
                  <span className="mono">{override.original_outcome}</span> →{" "}
                  <span className="mono">{override.new_outcome}</span>
                  <div style={{ color: "var(--ink-muted)", marginTop: 3 }}>
                    {override.justification}
                  </div>
                  <div
                    className="mono"
                    style={{ fontSize: 11, color: "var(--ink-faint)", marginTop: 2 }}
                  >
                    {fmt.time(override.created_at)}
                  </div>
                </div>
              ))}
            </div>
          )}

          <OverrideForm decision={decision} onDone={onRefresh} />
        </div>

        <div className="section">
          <div className="section-head">
            <h4>Provenance</h4>
          </div>
          <div className="mono" style={{ fontSize: 11.5, color: "var(--ink-muted)" }}>
            {decision.model_version}
          </div>
        </div>
      </div>
    </div>
  );
}
