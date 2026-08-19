/**
 * SHAP attribution, drawn as a diverging bar chart around a centre axis.
 *
 * Hand-built rather than pulled from a charting library: the chart has one job
 * and needs exact control of the axis position, so a dependency would add
 * weight without adding capability.
 *
 * Bars to the right of the axis pushed this applicant toward decline; bars to
 * the left counted in their favour. Only the factors that actually moved the
 * decision are shown -- a full list of twenty-four near-zero contributions
 * would bury the four that matter.
 */

import { fmt } from "../api.js";

const VISIBLE_ROWS = 10;

export default function Attribution({ attribution }) {
  const entries = Object.entries(attribution || {});
  if (entries.length === 0) {
    return <p className="section-note">No attribution recorded for this decision.</p>;
  }

  const ranked = entries
    .map(([feature, value]) => ({ feature, value: Number(value) }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, VISIBLE_ROWS);

  // Scale to the largest magnitude on show, so the widest bar always fills its
  // half of the track and small differences stay legible.
  const scale = Math.max(...ranked.map((row) => Math.abs(row.value))) || 1;

  return (
    <div>
      {ranked.map(({ feature, value }) => {
        const width = (Math.abs(value) / scale) * 50;
        const increasesRisk = value > 0;

        return (
          <div className="attrib-row" key={feature}>
            <span className="attrib-name" title={fmt.featureName(feature)}>
              {fmt.featureName(feature)}
            </span>
            <span className="attrib-track">
              <span className="attrib-axis" style={{ left: "50%" }} />
              <span
                className={`attrib-bar ${increasesRisk ? "risk" : "safe"}`}
                style={
                  increasesRisk
                    ? { left: "50%", width: `${width}%` }
                    : { right: "50%", width: `${width}%` }
                }
              />
            </span>
            <span className="attrib-value">
              {value > 0 ? "+" : ""}
              {value.toFixed(3)}
            </span>
          </div>
        );
      })}

      <div className="attrib-legend">
        <span>
          <span className="swatch" style={{ background: "var(--approve)" }} />
          Counted in favour
        </span>
        <span>
          <span className="swatch" style={{ background: "var(--decline)" }} />
          Increased risk
        </span>
      </div>
    </div>
  );
}
