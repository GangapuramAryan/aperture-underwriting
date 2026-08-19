"""Feature groups and applicant segmentation for the Aperture underwriting engine.

The central claim of this project is that alternative data carries incremental
predictive signal for applicants with little or no bureau history. Proving that
claim requires two things to be defined precisely and in one place:

1. Which features are "traditional" (available to a conventional underwriter)
   versus "alternative" (requiring consented, non-bureau data).
2. What counts as a "thin-file" applicant.

Both definitions live here so that the baseline and enhanced models cannot
accidentally leak features across the boundary.
"""

from __future__ import annotations

import pandas as pd

# ---------------------------------------------------------------------------
# Feature groups
# ---------------------------------------------------------------------------

# Modality 1: application form + credit bureau.
# This is the information set available to a conventional underwriting model.
TRADITIONAL_FEATURES: list[str] = [
    "income_annual",
    "employment_years",
    "debt_to_income",
    "age_years",
    "loan_amount",
    "loan_term_months",
    "bureau_score",
    "ext_source_1",
    "ext_source_3",
    "bureau_active_accounts",
    "bureau_closed_accounts",
    "bureau_max_days_overdue",
    "bureau_total_debt",
    "credit_history_months",
]

# Modality 2: consented alternative financial data.
# In production these are derived from Account Aggregator bank-statement feeds,
# telecom/utility billing records, and merchant transaction history.
ALTERNATIVE_FEATURES: list[str] = [
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
]

# Modality 4: in-session behavioural telemetry, used by the fraud model only.
# Deliberately excluded from the credit model: behavioural signals are evidence
# of misrepresentation, not of ability to repay. Conflating the two is how
# underwriting models acquire indefensible proxies.
BEHAVIOURAL_FEATURES: list[str] = [
    "form_correction_count",
    "pan_field_pasted",
    "session_duration_seconds",
    "applications_per_device_30d",
    "hour_of_day",
    "geo_velocity_kmh",
]

# Features that must never enter the credit model, with the reason recorded.
# This list is a deliverable in its own right: it is the artefact a model-risk
# reviewer asks for first.
EXCLUDED_FEATURES: dict[str, str] = {
    "gender": "ECOA / Reg B prohibited basis",
    "marital_status": "ECOA / Reg B prohibited basis",
    "religion": "Prohibited basis; DPDP sensitive personal data",
    "caste_category": "Prohibited basis under Indian constitutional protections",
    "pin_code": "Geographic proxy for protected class (redlining risk)",
    "applicant_photo": "Enables inference of protected attributes",
    "contact_list_size": "No causal link to repayment; RBI DLG restricts access",
}

BASELINE_FEATURES = TRADITIONAL_FEATURES
ENHANCED_FEATURES = TRADITIONAL_FEATURES + ALTERNATIVE_FEATURES


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

# An applicant is thin-file if they have almost no reportable credit history.
# Both conditions matter: an applicant may hold one account for years (shallow
# breadth) or several accounts for one month (shallow depth). Either leaves a
# conventional model with too little to score.
THIN_FILE_MAX_HISTORY_MONTHS = 12
THIN_FILE_MAX_ACCOUNTS = 1


def is_thin_file(df: pd.DataFrame) -> pd.Series:
    """Return a boolean Series flagging thin-file / new-to-credit applicants.

    Missing bureau history is treated as thin-file rather than dropped: a null
    bureau score is the defining characteristic of the population this project
    exists to serve, not a data-quality problem to be cleaned away.
    """
    total_accounts = (
        df["bureau_active_accounts"].fillna(0) + df["bureau_closed_accounts"].fillna(0)
    )
    history = df["credit_history_months"].fillna(0)

    no_bureau_score = df["bureau_score"].isna()
    shallow_history = history < THIN_FILE_MAX_HISTORY_MONTHS
    few_accounts = total_accounts <= THIN_FILE_MAX_ACCOUNTS

    return (no_bureau_score | shallow_history | few_accounts).rename("is_thin_file")


def segment_summary(df: pd.DataFrame, target: str = "default") -> pd.DataFrame:
    """Population and base default rate by segment. Slide 3 input."""
    thin = is_thin_file(df)
    rows = []
    for label, mask in (("Thin-file / NTC", thin), ("Thick-file", ~thin)):
        subset = df[mask]
        rows.append(
            {
                "segment": label,
                "applicants": len(subset),
                "share_of_population": len(subset) / len(df) if len(df) else 0.0,
                "base_default_rate": subset[target].mean() if len(subset) else float("nan"),
            }
        )
    return pd.DataFrame(rows)
