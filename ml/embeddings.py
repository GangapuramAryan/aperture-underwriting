"""Applicant embeddings for precedent retrieval.

Why a feature vector rather than a text model
---------------------------------------------
Credit attributes are numeric. Rendering them into a sentence and pushing that
through a sentence transformer would discard the ordering and magnitude that
make them meaningful, and would produce a vector whose dimensions mean nothing
in particular. A normalised feature vector keeps every dimension interpretable:
dimension 4 is always employment tenure, and two applicants are close because
their finances are close, not because their descriptions read alike.

Text embeddings are used elsewhere in this system -- over the reason-code
library, which really is natural language. Each instrument is applied to the
data it suits.

Normalisation
-------------
Each feature is scaled to roughly [0, 1] using bounds drawn from the domain
rather than from the sample, so an embedding computed today is comparable with
one computed after the population shifts. Missing values map to a neutral 0.5
and are flagged in a companion presence vector, so "no bureau score" is itself
a coordinate rather than an invented value: two applicants who both lack a
bureau file are genuinely similar in a way that matters.
"""

from __future__ import annotations

import numpy as np

# (feature, low, high, invert)
# `invert` marks features where a higher raw value means lower risk, so the
# normalised space runs consistently from safer to riskier on every axis.
EMBEDDING_SPEC: list[tuple[str, float, float, bool]] = [
    ("income_annual", 0.0, 2_000_000.0, True),
    ("employment_years", 0.0, 25.0, True),
    ("debt_to_income", 0.0, 8.0, False),
    ("age_years", 18.0, 70.0, False),
    ("loan_amount", 0.0, 2_000_000.0, False),
    ("loan_term_months", 0.0, 84.0, False),
    ("bureau_score", 300.0, 900.0, True),
    ("ext_source_1", 0.0, 1.0, True),
    ("ext_source_3", 0.0, 1.0, True),
    ("bureau_active_accounts", 0.0, 10.0, False),
    ("bureau_closed_accounts", 0.0, 12.0, True),
    ("bureau_max_days_overdue", 0.0, 180.0, False),
    ("bureau_total_debt", 0.0, 3_000_000.0, False),
    ("credit_history_months", 0.0, 240.0, True),
    ("cashflow_inflow_regularity", 0.0, 1.5, True),
    ("cashflow_volatility", 0.0, 1.5, False),
    ("salary_credit_consistency", 0.0, 1.0, True),
    ("avg_monthly_balance", 0.0, 500_000.0, True),
    ("balance_trend_90d", -2.0, 2.0, False),
    ("utility_ontime_ratio", 0.0, 1.0, True),
    ("rent_ontime_ratio", 0.0, 1.0, True),
    ("telecom_recharge_cadence_days", -30.0, 60.0, False),
    ("ecom_txn_count_90d", 0.0, 60.0, True),
    ("device_tenure_days", 0.0, 2_000.0, True),
]

# Value half of the vector, then presence half.
EMBEDDING_DIM = len(EMBEDDING_SPEC) * 2

NEUTRAL = 0.5


def embed_applicant(features: dict) -> list[float]:
    """Normalised embedding for one applicant.

    The first half carries scaled feature values; the second half is a binary
    presence mask. Two applicants who are both missing the same fields sit
    close together in the second half, which is what makes thin-file applicants
    retrieve other thin-file applicants rather than being scattered among
    whichever thick-file records happen to share an income band.
    """
    values: list[float] = []
    presence: list[float] = []

    for name, low, high, invert in EMBEDDING_SPEC:
        raw = features.get(name)

        if raw is None or (isinstance(raw, float) and np.isnan(raw)):
            values.append(NEUTRAL)
            presence.append(0.0)
            continue

        span = high - low or 1.0
        scaled = (float(raw) - low) / span
        scaled = min(max(scaled, 0.0), 1.0)
        values.append(1.0 - scaled if invert else scaled)
        presence.append(1.0)

    return values + presence


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    """Similarity in [-1, 1] between two embeddings."""
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator else 0.0


def describe_dimension(index: int) -> str:
    """Human label for one coordinate. Used when explaining a match."""
    if index < len(EMBEDDING_SPEC):
        return EMBEDDING_SPEC[index][0]
    return f"{EMBEDDING_SPEC[index - len(EMBEDDING_SPEC)][0]} (on file)"
