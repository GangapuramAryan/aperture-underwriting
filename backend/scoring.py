"""The decision service: scoring, credit policy, fraud screening, audit.

Separation of concerns here is deliberate and worth stating out loud.

The *model* produces one thing: a probability of default. It does not decide.
The *policy* converts that probability into an outcome using thresholds that a
credit officer owns and can change without retraining anything. The *reason
codes* explain the decision. A language model, when configured, only phrases
those reasons -- it never selects them and never influences the outcome.

That boundary is what makes the system auditable. A regulator can inspect the
policy without reading model internals, and can verify that the explanation
given to the applicant is derived from the same attribution that drove the
decision.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from backend.config import get_settings
from ml.features import BEHAVIOURAL_FEATURES, is_thin_file
from ml.reason_codes import AttributedReason, ReasonCodeEngine

APPROVE = "APPROVE"
REFER = "REFER"
DECLINE = "DECLINE"

FRAUD_PASS = "PASS"
FRAUD_REVIEW = "REVIEW"
FRAUD_BLOCK = "BLOCK"


@dataclass
class DecisionResult:
    outcome: str
    probability_of_default: float
    approved_line: float | None
    reasons: list[AttributedReason]
    fraud_score: float
    fraud_verdict: str
    fraud_signals: list[str]
    is_thin_file: bool
    model_version: str
    feature_set_hash: str
    input_hash: str
    shap_attribution: dict[str, float]
    latency_ms: float


# ---------------------------------------------------------------------------
# Fraud screening
# ---------------------------------------------------------------------------
# Rules first, deliberately. A rules layer is inspectable, instantly adjustable
# when a new fraud vector appears, and produces no false-positive surprises that
# cannot be traced to a specific condition. A learned anomaly model is the
# natural next layer and is scoped in the roadmap; shipping rules that are fully
# explainable beats shipping a model nobody can interrogate under time pressure.

FRAUD_RULES: list[tuple[str, str, float]] = [
    ("applications_per_device_30d", "Multiple applications from one device", 0.30),
    ("geo_velocity_kmh", "Implausible travel between application events", 0.25),
    ("pan_field_pasted", "Identity number pasted rather than typed", 0.15),
    ("form_correction_count", "Unusually high number of field corrections", 0.15),
    ("session_duration_seconds", "Application completed unusually quickly", 0.10),
    ("hour_of_day", "Submitted during atypical hours", 0.05),
]


def screen_fraud(features: dict[str, Any]) -> tuple[float, str, list[str]]:
    """Behavioural fraud screen. Returns (score, verdict, triggered signals)."""
    settings = get_settings()
    score = 0.0
    signals: list[str] = []

    def triggered(name: str) -> bool:
        value = features.get(name)
        if value is None:
            return False
        match name:
            case "applications_per_device_30d":
                return value >= 4
            case "geo_velocity_kmh":
                return value >= 300
            case "pan_field_pasted":
                return bool(value)
            case "form_correction_count":
                return value >= 8
            case "session_duration_seconds":
                return value <= 45
            case "hour_of_day":
                return value < 6 or value >= 23
        return False

    for name, description, weight in FRAUD_RULES:
        if triggered(name):
            score += weight
            signals.append(description)

    score = round(min(score, 1.0), 4)
    if score >= settings.fraud_block_threshold:
        verdict = FRAUD_BLOCK
    elif score >= settings.fraud_review_threshold:
        verdict = FRAUD_REVIEW
    else:
        verdict = FRAUD_PASS
    return score, verdict, signals


# ---------------------------------------------------------------------------
# Credit policy
# ---------------------------------------------------------------------------

def size_credit_line(probability_of_default: float, income_annual: float | None) -> float:
    """Exposure scaled by income and inversely by risk.

    Kept simple and monotone on purpose: a line-sizing rule that a credit
    officer cannot explain in one sentence will not survive review.
    """
    settings = get_settings()
    if not income_annual or income_annual <= 0:
        base = settings.min_credit_line
    else:
        base = income_annual * settings.line_income_multiple

    risk_factor = max(0.0, 1.0 - (probability_of_default / settings.refer_threshold))
    line = base * (0.35 + 0.65 * risk_factor)
    return float(round(min(max(line, settings.min_credit_line), settings.max_credit_line), -2))


def apply_policy(
    probability_of_default: float, fraud_verdict: str
) -> str:
    """Map risk and fraud verdict onto an outcome.

    Fraud has precedence over credit risk: a blocked application is never
    approved on the strength of a good score, because the score was computed
    from data that may not describe a real person.
    """
    settings = get_settings()
    if fraud_verdict == FRAUD_BLOCK:
        return DECLINE
    if fraud_verdict == FRAUD_REVIEW:
        return REFER
    if probability_of_default <= settings.approve_threshold:
        return APPROVE
    if probability_of_default <= settings.refer_threshold:
        return REFER
    return DECLINE


# ---------------------------------------------------------------------------
# Scoring service
# ---------------------------------------------------------------------------

class DecisionService:
    """Loads the trained model once and scores applications against it."""

    def __init__(self, model_dir: Path | None = None) -> None:
        settings = get_settings()
        model_dir = Path(model_dir or settings.model_dir)
        bundle_path = model_dir / settings.enhanced_model_file
        if not bundle_path.exists():
            raise FileNotFoundError(
                f"No model at {bundle_path}. Run: python -m ml.train --data homecredit "
                f"--path data/home-credit"
            )

        bundle = joblib.load(bundle_path)
        self.model = bundle["model"]
        # Feature order is taken from the bundle, never from the request. A
        # model served with reordered columns fails silently rather than loudly.
        self.feature_names: list[str] = bundle["features"]
        self.reason_engine = ReasonCodeEngine(self.model, self.feature_names)

        metadata_path = model_dir / "metadata.json"
        metadata = (
            json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        )
        self.feature_set_hash: str = metadata.get("feature_set_hash", "unknown")
        self.data_provenance: str = metadata.get("data_provenance", "unknown")
        trained_at = metadata.get("trained_at_utc", "unknown")[:19]
        self.model_version = f"aperture-pd-{self.feature_set_hash}-{trained_at}"

    def _frame(self, features: dict[str, Any]) -> pd.DataFrame:
        """Align an arbitrary payload to the model's expected feature order.

        Absent features become NaN rather than zero. The estimator handles
        missing values natively, and a missing bureau score genuinely means
        "unknown" -- imputing zero would assert something false about the
        applicant.
        """
        row = {name: features.get(name, np.nan) for name in self.feature_names}
        return pd.DataFrame([row], columns=self.feature_names).astype(float)

    def decide(self, features: dict[str, Any]) -> DecisionResult:
        started = time.perf_counter()

        frame = self._frame(features)
        probability = float(self.model.predict_proba(frame.to_numpy(dtype=float))[0, 1])

        shap_row = self.reason_engine.shap_values(frame)[0]
        reasons = self.reason_engine.explain_one(frame.iloc[0], shap_row=shap_row)

        behavioural = {
            name: features.get(name)
            for name in BEHAVIOURAL_FEATURES
            if features.get(name) is not None
        }
        fraud_score, fraud_verdict, fraud_signals = screen_fraud(behavioural)

        outcome = apply_policy(probability, fraud_verdict)
        line = (
            size_credit_line(probability, features.get("income_annual"))
            if outcome == APPROVE
            else None
        )

        thin = bool(is_thin_file(frame).iloc[0])

        canonical = json.dumps(
            {k: features.get(k) for k in sorted(self.feature_names)},
            sort_keys=True,
            default=str,
        )
        input_hash = hashlib.sha256(canonical.encode()).hexdigest()

        attribution = {
            name: round(float(value), 6)
            for name, value in zip(self.feature_names, shap_row)
        }

        return DecisionResult(
            outcome=outcome,
            probability_of_default=round(probability, 6),
            approved_line=line,
            reasons=reasons,
            fraud_score=fraud_score,
            fraud_verdict=fraud_verdict,
            fraud_signals=fraud_signals,
            is_thin_file=thin,
            model_version=self.model_version,
            feature_set_hash=self.feature_set_hash,
            input_hash=input_hash,
            shap_attribution=attribution,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
        )
