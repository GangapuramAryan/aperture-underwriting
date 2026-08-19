"""Request and response contracts.

Validation lives at the boundary. Every numeric field carries bounds, so a
negative income or an impossible age is rejected before it reaches the model
rather than being scored into a confident, meaningless answer. This is the
"input validation" control, implemented where it is actually enforceable.

Optionality is meaningful here: almost every credit field is optional because
the applicants this system exists to serve are precisely those for whom the
fields are blank. An absent bureau score is a valid application, not a
malformed one.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApplicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    applicant_name: str = Field(min_length=1, max_length=160)
    external_ref: str | None = Field(default=None, max_length=64)
    requested_amount: float = Field(gt=0, le=10_000_000)

    # ---- Traditional ----
    income_annual: float | None = Field(default=None, ge=0, le=1e9)
    employment_years: float | None = Field(default=None, ge=0, le=60)
    debt_to_income: float | None = Field(default=None, ge=0, le=50)
    age_years: float | None = Field(default=None, ge=18, le=100)
    loan_amount: float | None = Field(default=None, ge=0, le=1e8)
    loan_term_months: float | None = Field(default=None, ge=1, le=600)
    bureau_score: float | None = Field(default=None, ge=300, le=900)
    ext_source_1: float | None = Field(default=None, ge=0, le=1)
    ext_source_3: float | None = Field(default=None, ge=0, le=1)
    bureau_active_accounts: float | None = Field(default=None, ge=0, le=100)
    bureau_closed_accounts: float | None = Field(default=None, ge=0, le=100)
    bureau_max_days_overdue: float | None = Field(default=None, ge=0, le=3650)
    bureau_total_debt: float | None = Field(default=None, ge=0, le=1e9)
    credit_history_months: float | None = Field(default=None, ge=0, le=900)

    # ---- Alternative ----
    cashflow_inflow_regularity: float | None = Field(default=None, ge=0, le=3)
    cashflow_volatility: float | None = Field(default=None, ge=0, le=5)
    salary_credit_consistency: float | None = Field(default=None, ge=0, le=1)
    avg_monthly_balance: float | None = Field(default=None, ge=0, le=1e9)
    balance_trend_90d: float | None = Field(default=None, ge=-5, le=5)
    utility_ontime_ratio: float | None = Field(default=None, ge=0, le=1)
    rent_ontime_ratio: float | None = Field(default=None, ge=0, le=1)
    telecom_recharge_cadence_days: float | None = Field(default=None, ge=-400, le=400)
    ecom_txn_count_90d: float | None = Field(default=None, ge=0, le=10_000)
    device_tenure_days: float | None = Field(default=None, ge=0, le=20_000)

    # ---- Behavioural telemetry (fraud screen only) ----
    form_correction_count: int | None = Field(default=None, ge=0, le=500)
    pan_field_pasted: bool | None = None
    session_duration_seconds: float | None = Field(default=None, ge=0, le=100_000)
    applications_per_device_30d: int | None = Field(default=None, ge=0, le=500)
    hour_of_day: int | None = Field(default=None, ge=0, le=23)
    geo_velocity_kmh: float | None = Field(default=None, ge=0, le=5_000)

    def feature_payload(self) -> dict[str, Any]:
        """Model-facing fields only, excluding identity and request metadata."""
        excluded = {"applicant_name", "external_ref", "requested_amount"}
        return {
            key: value
            for key, value in self.model_dump().items()
            if key not in excluded and value is not None
        }


class ReasonOut(BaseModel):
    code: str
    statement: str
    improvement: str
    feature: str
    feature_value: float | None
    contribution_share: float


class DecisionResponse(BaseModel):
    decision_id: str
    application_id: str
    outcome: str
    probability_of_default: float
    approved_line: float | None
    is_thin_file: bool

    reasons: list[ReasonOut]

    fraud_score: float
    fraud_verdict: str
    fraud_signals: list[str]

    model_version: str
    latency_ms: float
    decided_at: datetime


class OverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    underwriter: str = Field(min_length=1, max_length=120)
    new_outcome: str = Field(pattern="^(APPROVE|REFER|DECLINE)$")
    # A justification is mandatory and substantive: an override without a
    # recorded rationale is indistinguishable from an unexplained deviation
    # when the file is reviewed later.
    justification: str = Field(min_length=15, max_length=2000)


class LedgerEntry(BaseModel):
    recorded_at: datetime
    decision_id: str
    application_id: str
    outcome: str
    probability_of_default: float
    model_version: str
    feature_set_hash: str
    input_hash: str
    approve_threshold: float
    refer_threshold: float
    reason_codes: list[Any]


class QueueItem(BaseModel):
    application_id: str
    decision_id: str
    applicant_name: str
    requested_amount: float
    outcome: str
    probability_of_default: float
    is_thin_file: bool
    fraud_verdict: str
    decided_at: datetime
