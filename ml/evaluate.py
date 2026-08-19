"""Evaluation metrics for the Aperture underwriting models.

The distinction that matters here is between a statistical metric and a business
metric. AUC tells you whether the model ranks applicants correctly. It does not
tell you whether the lender can approve more people. The metric a credit officer
actually cares about is:

    at a fixed tolerated loss rate, what fraction of applicants can I approve?

`approval_rate_at_loss` answers that, and the difference in its value between
the baseline and enhanced models on the thin-file segment is the single number
this entire project is built to produce.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

# Portfolio loss tolerance used for the headline comparison. Expressed as the
# realised default rate within the approved population.
DEFAULT_TARGET_LOSS_RATE = 0.03


def approval_rate_at_loss(
    y_true: np.ndarray,
    y_score: np.ndarray,
    target_loss_rate: float = DEFAULT_TARGET_LOSS_RATE,
) -> float:
    """Largest approvable share of applicants whose realised default rate stays
    within `target_loss_rate`.

    Applicants are ranked from safest to riskiest by predicted probability of
    default, then approved cumulatively. The returned figure is the largest
    cumulative share for which the observed default rate among the approved
    population does not exceed the tolerance.

    A better-ranking model pushes defaulters further down the queue, so more
    applicants clear the bar before the tolerance is breached. That is the
    mechanism by which model quality converts into credit access.

    Returns 0.0 when no non-empty approved set satisfies the tolerance.
    """
    if len(y_true) == 0:
        return float("nan")

    order = np.argsort(y_score, kind="mergesort")
    ranked_outcomes = np.asarray(y_true)[order]

    cumulative_defaults = np.cumsum(ranked_outcomes)
    counts = np.arange(1, len(ranked_outcomes) + 1)
    cumulative_loss_rate = cumulative_defaults / counts

    within_tolerance = np.flatnonzero(cumulative_loss_rate <= target_loss_rate)
    if within_tolerance.size == 0:
        return 0.0

    return float((within_tolerance[-1] + 1) / len(ranked_outcomes))


def safe_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """ROC AUC that returns NaN rather than raising on a single-class slice."""
    y_true = np.asarray(y_true)
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, y_score))


def evaluate_segment(
    y_true: np.ndarray,
    y_score: np.ndarray,
    target_loss_rate: float = DEFAULT_TARGET_LOSS_RATE,
) -> dict[str, float]:
    """Full metric bundle for one population slice."""
    return {
        "n": int(len(y_true)),
        "base_default_rate": float(np.mean(y_true)) if len(y_true) else float("nan"),
        "auc": safe_auc(y_true, y_score),
        "approval_rate": approval_rate_at_loss(y_true, y_score, target_loss_rate),
    }


def comparison_table(
    y_true: np.ndarray,
    baseline_scores: np.ndarray,
    enhanced_scores: np.ndarray,
    thin_file_mask: np.ndarray,
    target_loss_rate: float = DEFAULT_TARGET_LOSS_RATE,
) -> pd.DataFrame:
    """Build the headline baseline-vs-enhanced table, by segment.

    This is the direct input to slide 3 of the deck.
    """
    y_true = np.asarray(y_true)
    thin_file_mask = np.asarray(thin_file_mask)

    segments = {
        "Thin-file / NTC": thin_file_mask,
        "Thick-file": ~thin_file_mask,
        "Overall": np.ones_like(thin_file_mask, dtype=bool),
    }

    rows = []
    for segment_name, mask in segments.items():
        baseline = evaluate_segment(y_true[mask], baseline_scores[mask], target_loss_rate)
        enhanced = evaluate_segment(y_true[mask], enhanced_scores[mask], target_loss_rate)
        rows.append(
            {
                "segment": segment_name,
                "applicants": baseline["n"],
                "base_default_rate": round(baseline["base_default_rate"], 4),
                "auc_baseline": round(baseline["auc"], 4),
                "auc_enhanced": round(enhanced["auc"], 4),
                "auc_lift": round(enhanced["auc"] - baseline["auc"], 4),
                "approval_baseline": round(baseline["approval_rate"], 4),
                "approval_enhanced": round(enhanced["approval_rate"], 4),
                "approval_lift_pp": round(
                    100 * (enhanced["approval_rate"] - baseline["approval_rate"]), 2
                ),
            }
        )
    return pd.DataFrame(rows)


def adverse_impact_ratio(
    approved: np.ndarray, group: np.ndarray, reference_group: str | int | None = None
) -> pd.DataFrame:
    """Approval rate by group, and each group's ratio to the reference group.

    The conventional fairness screen in lending: a ratio below 0.80 for any
    group is the threshold at which US regulators historically treat disparate
    impact as warranting investigation. Reported here as a diagnostic, not as a
    pass/fail certificate -- a passing ratio is not proof of a fair model.
    """
    frame = pd.DataFrame({"approved": np.asarray(approved), "group": np.asarray(group)})
    rates = frame.groupby("group")["approved"].agg(["mean", "size"])
    rates.columns = ["approval_rate", "n"]

    if reference_group is None:
        reference_rate = rates["approval_rate"].max()
    else:
        reference_rate = rates.loc[reference_group, "approval_rate"]

    rates["impact_ratio"] = (rates["approval_rate"] / reference_rate).round(4)
    rates["flag"] = np.where(rates["impact_ratio"] < 0.80, "REVIEW", "ok")
    return rates.reset_index()
