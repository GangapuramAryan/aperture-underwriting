/**
 * Applicant notice.
 *
 * The badge under the letter is the point of this panel: it states whether the
 * text was generated or composed from the template, and whether it passed
 * validation. A reviewer should never have to guess which path produced a
 * disclosure that goes to a consumer.
 */

import { useState } from "react";

export default function Letter({ decisionId }) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/v1/decisions/${decisionId}/letter`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (!response.ok) throw new Error(`${response.status}`);
      setResult(await response.json());
    } catch (err) {
      setError(`Could not produce the notice — ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {error && <div className="banner error">{error}</div>}

      {!result && (
        <button className="btn ghost small" onClick={generate} disabled={busy}>
          {busy ? "Composing…" : "Produce applicant notice"}
        </button>
      )}

      {result && (
        <>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              fontFamily: "var(--font-ui)",
              fontSize: 13,
              lineHeight: 1.6,
              background: "var(--surface-sunk)",
              border: "1px solid var(--rule)",
              borderRadius: "var(--radius)",
              padding: 14,
              margin: 0,
            }}
          >
            {result.letter}
          </pre>

          <div className="attrib-legend" style={{ marginTop: 10 }}>
            <span>
              <span
                className="swatch"
                style={{
                  background:
                    result.source === "llm" ? "var(--accent)" : "var(--ink-faint)",
                }}
              />
              {result.source === "llm"
                ? `Generated via ${result.provider}, validated against the decision record`
                : "Composed from the decision record — no generated text"}
            </span>
          </div>

          {result.rejection_reason && (
            <div className="banner error" style={{ marginTop: 10 }}>
              Generated text was discarded: {result.rejection_reason}. The
              template was used instead.
            </div>
          )}
        </>
      )}
    </div>
  );
}
