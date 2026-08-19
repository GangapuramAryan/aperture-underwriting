"""Synthetic applicant generator for development and testing.

Purpose and honesty note
------------------------
This module exists so the pipeline, API, and UI can be built and tested before
(or without) the real Home Credit Default Risk dataset. It is NOT a source of
findings. Any figure produced from synthetic data is a smoke test, and every
chart derived from it must be labelled "synthetic" in the deck.

Generative structure
--------------------
The generator encodes the causal story the project argues for:

  * A latent creditworthiness score drives repayment.
  * That latent score is observable through two channels: bureau history and
    cashflow behaviour.
  * For thick-file applicants the bureau channel is a clean, low-noise view.
  * For thin-file applicants the bureau channel is largely absent or noise --
    but the cashflow channel is undisturbed.

The consequence is that a bureau-only model degrades sharply on the thin-file
segment while a model with alternative data does not. This mirrors the real
mechanism, so a pipeline that measures lift correctly here will measure it
correctly on Home Credit.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_SEED = 42


def generate_applicants(n: int = 30_000, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """Generate a synthetic applicant table with a binary `default` target."""
    rng = np.random.default_rng(seed)

    # ---- Latent creditworthiness -----------------------------------------
    # Higher is safer. Unobservable in production; used here to generate both
    # the observable channels and the outcome.
    latent = rng.normal(0.0, 1.0, n)

    # ---- Who is thin-file ------------------------------------------------
    # Thin-file status is driven by life stage, not by risk. This is important:
    # if thin-file status correlated with the latent score, the dataset would
    # bake in the very bias the project claims to remove.
    age_years = np.clip(rng.gamma(shape=4.0, scale=3.4, size=n) + 21, 21, 70).round()
    p_thin = 1 / (1 + np.exp((age_years - 31) / 3.5))
    thin_mask = rng.random(n) < p_thin

    # ---- Traditional / bureau channel ------------------------------------
    credit_history_months = np.where(
        thin_mask,
        rng.integers(0, 14, n),
        rng.integers(18, 240, n),
    )
    bureau_active_accounts = np.where(
        thin_mask, rng.integers(0, 2, n), rng.integers(1, 9, n)
    )
    bureau_closed_accounts = np.where(
        thin_mask, rng.integers(0, 2, n), rng.integers(0, 12, n)
    )

    # Bureau score is a clean read on latent risk for thick files and a noisy
    # one for thin files, then withheld entirely where history is absent.
    bureau_noise = np.where(thin_mask, 1.6, 0.35)
    bureau_score_raw = 650 + 90 * latent + rng.normal(0, 1, n) * 90 * bureau_noise
    bureau_score = np.clip(bureau_score_raw, 300, 900)
    bureau_score = np.where(credit_history_months < 6, np.nan, bureau_score)

    bureau_max_days_overdue = np.where(
        credit_history_months < 6,
        np.nan,
        np.clip(rng.gamma(1.4, 12, n) - 22 * latent, 0, 180).round(),
    )
    bureau_total_debt = np.clip(
        rng.lognormal(11.2, 0.9, n) * (1 + 0.12 * bureau_active_accounts), 0, None
    ).round(-2)

    # ---- Application form ------------------------------------------------
    income_annual = np.clip(
        rng.lognormal(12.7, 0.55, n) * (1 + 0.18 * latent), 120_000, None
    ).round(-3)
    employment_years = np.clip(
        rng.gamma(2.0, 2.2, n) + 0.9 * latent + (age_years - 21) * 0.05, 0, 40
    ).round(1)
    loan_amount = np.clip(income_annual * rng.uniform(0.15, 0.85, n), 20_000, None).round(-3)
    loan_term_months = rng.choice([12, 18, 24, 36, 48, 60], n, p=[0.1, 0.15, 0.3, 0.25, 0.12, 0.08])
    debt_to_income = np.clip(
        (bureau_total_debt + loan_amount) / income_annual - 0.25 * latent, 0.02, 6.0
    ).round(3)

    # ---- Alternative channel ---------------------------------------------
    # Undisturbed by file thickness: this is the point of the whole exercise.
    alt_noise = 0.55
    def alt_signal(scale: float) -> np.ndarray:
        return latent + rng.normal(0, alt_noise, n) * scale

    cashflow_inflow_regularity = np.clip(0.62 + 0.14 * alt_signal(1.0), 0.0, 1.0).round(3)
    salary_credit_consistency = np.clip(0.58 + 0.16 * alt_signal(1.0), 0.0, 1.0).round(3)
    cashflow_volatility = np.clip(0.45 - 0.11 * alt_signal(1.1), 0.01, 2.0).round(3)
    avg_monthly_balance = np.clip(
        rng.lognormal(9.6, 0.8, n) * (1 + 0.3 * alt_signal(1.0)), 100, None
    ).round(-1)
    balance_trend_90d = (0.01 + 0.05 * alt_signal(1.2)).round(4)
    utility_ontime_ratio = np.clip(0.80 + 0.12 * alt_signal(1.0), 0.0, 1.0).round(3)
    rent_ontime_ratio = np.clip(0.78 + 0.13 * alt_signal(1.0), 0.0, 1.0).round(3)
    telecom_recharge_cadence_days = np.clip(
        30 - 4.0 * alt_signal(1.3), 1, 120
    ).round(1)
    ecom_txn_count_90d = np.clip(
        rng.poisson(np.clip(14 + 5 * alt_signal(1.0), 0.5, None)), 0, None
    )
    device_tenure_days = np.clip(
        rng.gamma(2.2, 200, n) + 90 * alt_signal(1.0), 1, None
    ).round()

    # ---- Behavioural / fraud channel -------------------------------------
    # Fraud propensity is independent of credit risk by construction.
    fraud_latent = rng.normal(0, 1, n)
    is_fraud = (rng.random(n) < 1 / (1 + np.exp(-(fraud_latent * 1.5 - 4.15)))).astype(int)

    form_correction_count = np.clip(
        rng.poisson(2.5 + 3.5 * is_fraud, n), 0, None
    )
    pan_field_pasted = (rng.random(n) < (0.08 + 0.42 * is_fraud)).astype(int)
    session_duration_seconds = np.clip(
        rng.gamma(3.0, 90, n) * (1 - 0.45 * is_fraud), 20, None
    ).round()
    applications_per_device_30d = np.clip(
        rng.poisson(1.0 + 3.2 * is_fraud, n), 1, None
    )
    hour_of_day = np.where(
        is_fraud == 1,
        rng.choice(np.r_[0:6, 22:24], n),
        rng.integers(7, 23, n),
    )
    geo_velocity_kmh = np.clip(
        rng.gamma(1.3, 25, n) + 380 * is_fraud, 0, None
    ).round(1)

    # ---- Outcome ---------------------------------------------------------
    # Repayment depends on latent creditworthiness and leverage only.
    logit = -3.35 - 1.42 * latent + 0.38 * debt_to_income
    default = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)

    df = pd.DataFrame(
        {
            "application_id": [f"SYN{i:07d}" for i in range(n)],
            # traditional
            "income_annual": income_annual,
            "employment_years": employment_years,
            "debt_to_income": debt_to_income,
            "age_years": age_years,
            "loan_amount": loan_amount,
            "loan_term_months": loan_term_months,
            "bureau_score": bureau_score,
            "bureau_active_accounts": bureau_active_accounts,
            "bureau_closed_accounts": bureau_closed_accounts,
            "bureau_max_days_overdue": bureau_max_days_overdue,
            "bureau_total_debt": bureau_total_debt,
            "credit_history_months": credit_history_months,
            # alternative
            "cashflow_inflow_regularity": cashflow_inflow_regularity,
            "cashflow_volatility": cashflow_volatility,
            "salary_credit_consistency": salary_credit_consistency,
            "avg_monthly_balance": avg_monthly_balance,
            "balance_trend_90d": balance_trend_90d,
            "utility_ontime_ratio": utility_ontime_ratio,
            "rent_ontime_ratio": rent_ontime_ratio,
            "telecom_recharge_cadence_days": telecom_recharge_cadence_days,
            "ecom_txn_count_90d": ecom_txn_count_90d,
            "device_tenure_days": device_tenure_days,
            # behavioural
            "form_correction_count": form_correction_count,
            "pan_field_pasted": pan_field_pasted,
            "session_duration_seconds": session_duration_seconds,
            "applications_per_device_30d": applications_per_device_30d,
            "hour_of_day": hour_of_day,
            "geo_velocity_kmh": geo_velocity_kmh,
            # targets
            "default": default,
            "is_fraud": is_fraud,
        }
    )
    return df


if __name__ == "__main__":
    frame = generate_applicants(5_000)
    print(frame.shape)
    print(frame[["default", "is_fraud"]].mean().round(4).to_string())
