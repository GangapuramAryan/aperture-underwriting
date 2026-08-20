/**
 * Comparable applicants, retrieved by vector similarity.
 *
 * A referred file arrives at a human as a probability and four reason codes,
 * which is hard to reason from. Five comparable applicants and how each was
 * decided is not. This is the instinct a senior underwriter builds over years,
 * made available on the first day.
 *
 * The wording is careful: these are how similar applicants were *decided*, not
 * how they went on to repay. Repayment is known months later. Labelling
 * decisions as outcomes would overstate what the panel shows, so the caption
 * says exactly what it is.
 */

import { fmt } from "../api.js";

export default function Precedents({ precedents, summary }) {
  if (!precedents || precedents.length === 0) {
    return (
      <p className="section-note">
        No sufficiently comparable applicants on file yet. Precedents appear
        once similar profiles have been decided.
      </p>
    );
  }

  return (
    <div>
      <p className="section-note" style={{ marginTop: 0, marginBottom: 12 }}>
        Of {summary.count} comparable {summary.count === 1 ? "file" : "files"}:{" "}
        {summary.approved} approved, {summary.referred} referred,{" "}
        {summary.declined} declined · mean risk{" "}
        {fmt.percent(summary.mean_probability, 1)}
      </p>

      <table>
        <thead>
          <tr>
            <th>Applicant</th>
            <th>Match</th>
            <th>Requested</th>
            <th>Risk</th>
            <th>Decided</th>
          </tr>
        </thead>
        <tbody>
          {precedents.map((item) => (
            <tr key={item.decision_id}>
              <td>
                {item.applicant_name}
                {item.is_thin_file && (
                  <span className="thin-tag" style={{ marginLeft: 7 }}>
                    Thin file
                  </span>
                )}
              </td>
              <td className="mono">{fmt.percent(item.similarity, 1)}</td>
              <td className="mono">{fmt.currency(item.requested_amount)}</td>
              <td className="mono">
                {fmt.percent(item.probability_of_default, 1)}
              </td>
              <td>
                <span className={`verdict ${item.outcome}`}>{item.outcome}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
