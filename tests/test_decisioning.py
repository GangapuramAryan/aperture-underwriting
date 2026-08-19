"""Tests for decision-critical logic.

Scope is deliberate. These cover the parts where a silent error would produce a
plausible-looking but wrong decision -- the business metric and the legally
required disclosures -- rather than chasing coverage of the whole codebase.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.evaluate import adverse_impact_ratio, approval_rate_at_loss, safe_auc
from ml.features import (
    ALTERNATIVE_FEATURES,
    EXCLUDED_FEATURES,
    TRADITIONAL_FEATURES,
    is_thin_file,
)
from ml.reason_codes import MAX_PRINCIPAL_REASONS, REASON_CODES
from ml.synth import generate_applicants


# ---------------------------------------------------------------------------
# Business metric
# ---------------------------------------------------------------------------

def test_perfect_ranking_approves_all_non_defaulters():
    """With a perfect model, everyone who repaid should be approvable."""
    y = np.array([0, 0, 0, 0, 0, 0, 0, 0, 1, 1])
    perfect = y.astype(float)  # defaulters ranked last
    assert approval_rate_at_loss(y, perfect, target_loss_rate=0.0) == pytest.approx(0.8)


def test_tolerance_admits_some_defaulters():
    """A non-zero loss tolerance should approve strictly more than a zero one."""
    rng = np.random.default_rng(0)
    y = (rng.random(1000) < 0.1).astype(int)
    scores = y + rng.normal(0, 0.4, 1000)
    strict = approval_rate_at_loss(y, scores, 0.0)
    lenient = approval_rate_at_loss(y, scores, 0.05)
    assert lenient > strict


def test_returns_zero_when_tolerance_unreachable():
    """If even the safest applicant defaulted, nothing can be approved."""
    y = np.array([1, 1, 1])
    assert approval_rate_at_loss(y, np.array([0.1, 0.2, 0.3]), 0.01) == 0.0


def test_better_ranking_yields_higher_approvals():
    """The core claim of the project, as an invariant."""
    rng = np.random.default_rng(42)
    y = (rng.random(2000) < 0.1).astype(int)
    weak = y + rng.normal(0, 1.5, 2000)
    strong = y + rng.normal(0, 0.3, 2000)
    assert approval_rate_at_loss(y, strong, 0.03) > approval_rate_at_loss(y, weak, 0.03)


def test_auc_returns_nan_on_single_class_slice():
    """A thin segment may contain no defaulters; that must not raise."""
    assert np.isnan(safe_auc(np.array([0, 0, 0]), np.array([0.1, 0.2, 0.3])))


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def test_missing_bureau_score_is_thin_file():
    """An absent bureau score defines the population, and is never dropped."""
    df = generate_applicants(400, seed=3)
    df.loc[:, "bureau_score"] = np.nan
    assert is_thin_file(df).all()


def test_established_borrower_is_not_thin_file():
    df = generate_applicants(1, seed=5)
    df.loc[:, ["bureau_score", "credit_history_months"]] = [720.0, 96.0]
    df.loc[:, ["bureau_active_accounts", "bureau_closed_accounts"]] = [3, 4]
    assert not is_thin_file(df).iloc[0]


# ---------------------------------------------------------------------------
# Reason codes and fair lending
# ---------------------------------------------------------------------------

def test_every_model_feature_has_a_reason_code():
    """A feature that can drive a decline must be disclosable."""
    unmapped = [
        name
        for name in TRADITIONAL_FEATURES + ALTERNATIVE_FEATURES
        if name not in REASON_CODES
    ]
    assert unmapped == [], f"features with no adverse action code: {unmapped}"


def test_principal_reasons_are_capped():
    """Regulation B expects principal reasons, not an exhaustive dump."""
    assert 1 <= MAX_PRINCIPAL_REASONS <= 5


def test_no_prohibited_basis_reaches_the_model():
    """Excluded features must never appear in any modelled feature set."""
    modelled = set(TRADITIONAL_FEATURES + ALTERNATIVE_FEATURES)
    leaked = modelled & set(EXCLUDED_FEATURES)
    assert leaked == set(), f"prohibited features present in model: {leaked}"


def test_every_exclusion_records_a_justification():
    """The exclusion list is an audit artefact, so reasons are mandatory."""
    assert all(reason.strip() for reason in EXCLUDED_FEATURES.values())


def test_adverse_impact_ratio_flags_disparity():
    """A group approved far less often than the reference must be flagged."""
    approved = np.array([1] * 90 + [0] * 10 + [1] * 40 + [0] * 60)
    group = np.array(["A"] * 100 + ["B"] * 100)
    result = adverse_impact_ratio(approved, group).set_index("group")
    assert result.loc["B", "impact_ratio"] < 0.80
    assert result.loc["B", "flag"] == "REVIEW"
    assert result.loc["A", "flag"] == "ok"
