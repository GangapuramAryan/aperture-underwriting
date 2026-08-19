"""Adverse action reason codes derived from SHAP attributions.

Why this module exists
----------------------
A lender may not decline an application and cite "the model". Under ECOA /
Regulation B a declined applicant is entitled to the specific principal reasons
for the decision, and the CFPB's 2023 circular made explicit that the complexity
of an algorithm is not a defence against that obligation. India's RBI Digital
Lending Guidelines impose a comparable disclosure duty.

So a probability of default is not a deliverable. A decision plus its principal
reasons is.

Design
------
The pipeline is deliberately deterministic end to end:

    features -> model -> SHAP attribution -> ranked adverse factors -> codes

SHAP assigns each feature a signed contribution to this particular applicant's
score. Positive contributions push toward decline. The largest positive
contributions are, by construction, the principal reasons -- and they are
specific to the individual, not global feature importances dressed up as
personal explanation.

Codes are drawn from a fixed vocabulary. The same inputs always produce the same
codes, which is what makes the output auditable and testable. No language model
participates in this step; one is used later only to render these codes into
prose, and never to choose them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

import numpy as np
import pandas as pd
import shap

# ---------------------------------------------------------------------------
# Reason code vocabulary
# ---------------------------------------------------------------------------
# `statement` is applicant-facing and must be intelligible to a layperson.
# `improvement` gives the applicant an actionable route, which is the difference
# between a disclosure that satisfies a lawyer and one that helps a person.

@dataclass(frozen=True)
class ReasonCode:
    code: str
    statement: str
    improvement: str


REASON_CODES: dict[str, ReasonCode] = {
    "debt_to_income": ReasonCode(
        "AA01",
        "Existing debt is high relative to your income",
        "Reducing outstanding balances or applying for a smaller amount may help.",
    ),
    "income_annual": ReasonCode(
        "AA02",
        "Reported income is low relative to the amount requested",
        "Applying for a smaller amount, or adding a co-applicant, may help.",
    ),
    "employment_years": ReasonCode(
        "AA03",
        "Length of employment is shorter than we typically require",
        "Reapplying after a longer period in stable employment may help.",
    ),
    "credit_history_months": ReasonCode(
        "AA04",
        "Your credit history is shorter than we typically require",
        "This improves on its own as your accounts age.",
    ),
    "bureau_score": ReasonCode(
        "AA05",
        "Your credit bureau score is below our current threshold",
        "On-time payments on existing accounts raise this over time.",
    ),
    "ext_source_1": ReasonCode(
        "AA05",
        "Your credit bureau score is below our current threshold",
        "On-time payments on existing accounts raise this over time.",
    ),
    "ext_source_3": ReasonCode(
        "AA05",
        "Your credit bureau score is below our current threshold",
        "On-time payments on existing accounts raise this over time.",
    ),
    "bureau_max_days_overdue": ReasonCode(
        "AA06",
        "Records show a past account fell significantly behind on payments",
        "The impact of past arrears lessens as time passes without recurrence.",
    ),
    "bureau_total_debt": ReasonCode(
        "AA07",
        "Total outstanding debt across your accounts is high",
        "Paying down existing balances may help.",
    ),
    "bureau_active_accounts": ReasonCode(
        "AA08",
        "You are currently servicing a large number of active accounts",
        "Closing accounts you no longer use may help.",
    ),
    "bureau_closed_accounts": ReasonCode(
        "AA04",
        "Your credit history is shorter than we typically require",
        "This improves on its own as your accounts age.",
    ),
    "loan_amount": ReasonCode(
        "AA09",
        "The amount requested is large relative to your financial profile",
        "Requesting a smaller amount may lead to a different outcome.",
    ),
    "loan_term_months": ReasonCode(
        "AA10",
        "The requested repayment term does not fit our lending criteria",
        "A different repayment term may lead to a different outcome.",
    ),
    "utility_ontime_ratio": ReasonCode(
        "AA11",
        "Your record shows recurring payments were often made after the due date",
        "A sustained period of on-time payments will improve this.",
    ),
    "rent_ontime_ratio": ReasonCode(
        "AA11",
        "Your record shows recurring payments were often made after the due date",
        "A sustained period of on-time payments will improve this.",
    ),
    "telecom_recharge_cadence_days": ReasonCode(
        "AA12",
        "Payments were typically made later than the scheduled date",
        "Paying on or before the due date will improve this.",
    ),
    "salary_credit_consistency": ReasonCode(
        "AA13",
        "The timing of your payments has been irregular",
        "Consistent payment timing, even by standing instruction, will improve this.",
    ),
    "cashflow_inflow_regularity": ReasonCode(
        "AA14",
        "Scheduled payments were often only partially met",
        "Meeting scheduled amounts in full will improve this.",
    ),
    "cashflow_volatility": ReasonCode(
        "AA15",
        "The amounts you pay vary substantially from month to month",
        "More predictable payment amounts will improve this.",
    ),
    "avg_monthly_balance": ReasonCode(
        "AA16",
        "Average account balance is low relative to the amount requested",
        "Maintaining a higher balance over time may help.",
    ),
    "balance_trend_90d": ReasonCode(
        "AA17",
        "Your account balance has been rising over recent months",
        "A stable or falling balance is viewed more favourably.",
    ),
    "ecom_txn_count_90d": ReasonCode(
        "AA18",
        "Recent account activity is limited",
        "Regular use of your existing accounts builds a fuller picture.",
    ),
    "device_tenure_days": ReasonCode(
        "AA19",
        "We have limited history associated with your contact details",
        "This strengthens naturally as your details remain stable.",
    ),
    "age_years": ReasonCode(
        "AA20",
        "Profile characteristics did not meet our current lending criteria",
        "Criteria are reviewed periodically; you may reapply in future.",
    ),
}

# Regulation B requires disclosure of the *principal* reasons. Four is the
# convention: enough to be genuinely informative, few enough to stay meaningful.
MAX_PRINCIPAL_REASONS = 4

# Attributions below this share of total adverse contribution are noise rather
# than a principal reason, and are not disclosed.
MIN_CONTRIBUTION_SHARE = 0.05


@dataclass(frozen=True)
class AttributedReason:
    """One disclosed reason, with the evidence that produced it."""

    code: str
    statement: str
    improvement: str
    feature: str
    feature_value: float | None
    contribution: float
    contribution_share: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReasonCodeEngine:
    """Turns a fitted tree model into per-applicant adverse action reasons."""

    def __init__(self, model: Any, feature_names: list[str]) -> None:
        self.model = model
        self.feature_names = list(feature_names)
        self.explainer = shap.TreeExplainer(model)

    def shap_values(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """SHAP contributions toward the positive (default) class.

        Returns shape (n_samples, n_features). Positive values push the
        applicant toward decline.
        """
        if isinstance(X, pd.DataFrame):
            X = X[self.feature_names].to_numpy(dtype=float)

        values = self.explainer.shap_values(X)

        # SHAP returns either (n, f) or (n, f, 2) for binary classifiers
        # depending on the estimator. Normalise to the positive class.
        values = np.asarray(values)
        if values.ndim == 3:
            values = values[:, :, 1]
        return values

    def explain_one(
        self, row: pd.Series | np.ndarray, shap_row: np.ndarray | None = None
    ) -> list[AttributedReason]:
        """Principal adverse reasons for a single applicant, ranked."""
        if shap_row is None:
            frame = (
                row.to_frame().T
                if isinstance(row, pd.Series)
                else pd.DataFrame([row], columns=self.feature_names)
            )
            shap_row = self.shap_values(frame)[0]

        values = (
            row[self.feature_names].to_numpy(dtype=float)
            if isinstance(row, pd.Series)
            else np.asarray(row, dtype=float)
        )

        # Only risk-increasing contributions are adverse. Factors that helped
        # the applicant are not reasons for declining them.
        adverse = [
            (name, float(contribution), float(value))
            for name, contribution, value in zip(self.feature_names, shap_row, values)
            if contribution > 0
        ]
        if not adverse:
            return []

        total = sum(contribution for _, contribution, _ in adverse)
        adverse.sort(key=lambda item: item[1], reverse=True)

        # Several features can legitimately map to the same disclosure -- the
        # three external scores all mean "bureau score is low". Listing that
        # reason three times would consume the principal-reason slots without
        # telling the applicant anything more, so each code is disclosed once
        # and the freed slots go to the next distinct reason. Contribution
        # shares are summed across the features backing a code, so the reported
        # weight still reflects the full influence of that factor.
        reasons: list[AttributedReason] = []
        seen: dict[str, int] = {}

        for name, contribution, value in adverse:
            if len(reasons) >= MAX_PRINCIPAL_REASONS and name not in seen:
                break

            share = contribution / total if total else 0.0

            code = REASON_CODES.get(name)
            if code is None:
                code = ReasonCode(
                    "AA99",
                    f"Profile characteristic did not meet our criteria ({name})",
                    "Contact us for further detail on this factor.",
                )

            if code.code in seen:
                index = seen[code.code]
                existing = reasons[index]
                reasons[index] = replace(
                    existing,
                    contribution=round(existing.contribution + contribution, 6),
                    contribution_share=round(existing.contribution_share + share, 4),
                )
                continue

            if share < MIN_CONTRIBUTION_SHARE:
                break

            seen[code.code] = len(reasons)
            reasons.append(
                AttributedReason(
                    code=code.code,
                    statement=code.statement,
                    improvement=code.improvement,
                    feature=name,
                    feature_value=None if np.isnan(value) else round(value, 4),
                    contribution=round(contribution, 6),
                    contribution_share=round(share, 4),
                )
            )
        return reasons

    def explain_batch(self, X: pd.DataFrame) -> list[list[AttributedReason]]:
        """Principal adverse reasons for each row of a batch."""
        matrix = self.shap_values(X)
        return [
            self.explain_one(X.iloc[i], shap_row=matrix[i]) for i in range(len(X))
        ]

    def unmapped_features(self) -> list[str]:
        """Features with no reason code. Should be empty; asserted in tests."""
        return [name for name in self.feature_names if name not in REASON_CODES]
