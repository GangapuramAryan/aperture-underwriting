"""Train and compare the baseline and enhanced probability-of-default models.

Run:
    python -m ml.train                  # synthetic data (default)
    python -m ml.train --data homecredit --path data/home-credit

Produces:
    artifacts/model_baseline.joblib     traditional features only
    artifacts/model_enhanced.joblib     + alternative data
    artifacts/comparison.csv            headline lift table (deck slide 3)
    artifacts/segments.csv              population summary
    artifacts/metadata.json             versions, hashes, config for audit

Model choice
------------
Histogram-based gradient boosting from scikit-learn. Chosen over LightGBM
because scikit-learn's wheels vendor their own OpenMP runtime and therefore
install cleanly on Apple Silicon without Homebrew. The algorithm is the same
family (LightGBM's histogram binning was the direct inspiration for this
estimator), it handles missing values natively -- essential here, since an
absent bureau score is the defining feature of the population we serve, not a
defect to impute away -- and it supports the monotonic constraints the credit
policy requires.

The two models are deliberately identical in hyperparameters and random seed.
The only difference between them is the feature set, so any measured difference
in performance is attributable to the alternative data and nothing else.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split

from ml.evaluate import DEFAULT_TARGET_LOSS_RATE, comparison_table
from ml.features import (
    BASELINE_FEATURES,
    ENHANCED_FEATURES,
    is_thin_file,
    segment_summary,
)

ARTIFACT_DIR = Path("artifacts")
TARGET = "default"
RANDOM_SEED = 42

# Monotonic constraints encode domain knowledge the model is not permitted to
# contradict: a longer on-time payment history must never increase predicted
# risk. This costs a little accuracy and buys defensibility -- a model that has
# learned a perverse direction on a sensitive-adjacent feature cannot be
# explained to a regulator, however good its AUC.
#
# Convention: -1 means predicted risk must fall as the feature rises;
#             +1 means predicted risk must rise as the feature rises.
MONOTONE_DIRECTIONS: dict[str, int] = {
    "bureau_score": -1,
    "bureau_max_days_overdue": 1,
    "debt_to_income": 1,
    "utility_ontime_ratio": -1,
    "rent_ontime_ratio": -1,
    "salary_credit_consistency": -1,
    "cashflow_inflow_regularity": -1,
    "cashflow_volatility": 1,
    "employment_years": -1,
}

MODEL_PARAMS = {
    "max_iter": 500,
    "learning_rate": 0.06,
    "max_leaf_nodes": 31,
    "min_samples_leaf": 60,
    "l2_regularization": 1.0,
    "early_stopping": True,
    "validation_fraction": 0.15,
    "n_iter_no_change": 40,
    "random_state": RANDOM_SEED,
}


def monotone_vector(feature_names: list[str]) -> list[int]:
    """Constraint vector aligned to the given feature order."""
    return [MONOTONE_DIRECTIONS.get(name, 0) for name in feature_names]


def train_model(
    train_df: pd.DataFrame, feature_names: list[str]
) -> HistGradientBoostingClassifier:
    """Fit one model on the given feature set.

    Early stopping uses a validation slice carved from the training data, so the
    test set stays untouched until final evaluation.
    """
    model = HistGradientBoostingClassifier(
        monotonic_cst=monotone_vector(feature_names), **MODEL_PARAMS
    )
    model.fit(train_df[feature_names].to_numpy(dtype=float), train_df[TARGET].to_numpy())
    return model


def predict_pd(
    model: HistGradientBoostingClassifier, df: pd.DataFrame, feature_names: list[str]
) -> np.ndarray:
    """Predicted probability of default for each row."""
    return model.predict_proba(df[feature_names].to_numpy(dtype=float))[:, 1]


def load_data(source: str, path: str | None) -> tuple[pd.DataFrame, str]:
    """Load the applicant table. Returns the frame and a provenance label."""
    if source == "synthetic":
        from ml.synth import generate_applicants

        return generate_applicants(40_000), "SYNTHETIC -- not a source of findings"

    if source == "homecredit":
        if path is None:
            raise ValueError("--path is required when --data homecredit is used")
        from ml.homecredit import load_homecredit

        return load_homecredit(Path(path)), "Home Credit Default Risk (Kaggle)"

    raise ValueError(f"unknown data source: {source}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Aperture PD models.")
    parser.add_argument("--data", default="synthetic", choices=["synthetic", "homecredit"])
    parser.add_argument("--path", default=None, help="Directory of Home Credit CSVs")
    parser.add_argument("--target-loss", type=float, default=DEFAULT_TARGET_LOSS_RATE)
    args = parser.parse_args()

    ARTIFACT_DIR.mkdir(exist_ok=True)

    df, provenance = load_data(args.data, args.path)
    print(f"\nData source : {provenance}")
    print(f"Applicants  : {len(df):,}")

    # Stratify on the target so both splits carry a comparable default rate.
    train_df, test_df = train_test_split(
        df, test_size=0.30, random_state=RANDOM_SEED, stratify=df[TARGET]
    )
    print(f"Train / test: {len(train_df):,} / {len(test_df):,}")

    print("\nPopulation by segment")
    segments = segment_summary(df, TARGET)
    print(segments.to_string(index=False))

    baseline_features = [f for f in BASELINE_FEATURES if f in df.columns]
    enhanced_features = [f for f in ENHANCED_FEATURES if f in df.columns]

    print(f"\nTraining baseline ({len(baseline_features)} traditional features)...")
    baseline_model = train_model(train_df, baseline_features)

    print(f"Training enhanced ({len(enhanced_features)} features, + alternative data)...")
    enhanced_model = train_model(train_df, enhanced_features)

    baseline_scores = predict_pd(baseline_model, test_df, baseline_features)
    enhanced_scores = predict_pd(enhanced_model, test_df, enhanced_features)
    thin_mask = is_thin_file(test_df).to_numpy()

    table = comparison_table(
        test_df[TARGET].to_numpy(),
        baseline_scores,
        enhanced_scores,
        thin_mask,
        args.target_loss,
    )

    print(f"\n{'=' * 78}")
    print(f"HEADLINE RESULT  (loss tolerance = {args.target_loss:.1%} realised default rate)")
    print("=" * 78)
    print(table.to_string(index=False))
    print("=" * 78)

    thin_row = table.loc[table["segment"] == "Thin-file / NTC"].iloc[0]
    print(
        f"\nThin-file segment: AUC {thin_row['auc_baseline']:.3f} -> "
        f"{thin_row['auc_enhanced']:.3f}  (+{thin_row['auc_lift']:.3f})"
    )
    print(
        f"Approvals at constant loss: {thin_row['approval_baseline']:.1%} -> "
        f"{thin_row['approval_enhanced']:.1%}  ({thin_row['approval_lift_pp']:+.1f} pp)"
    )
    if args.data == "synthetic":
        print("\n[!] SYNTHETIC DATA. Do not put these numbers in the deck.")

    # ---- Persist artefacts ------------------------------------------------
    # Feature order is stored alongside each model: a model served with columns
    # in a different order than it was trained on fails silently, producing
    # plausible nonsense. The API loads this to guarantee alignment.
    joblib.dump(
        {"model": baseline_model, "features": baseline_features},
        ARTIFACT_DIR / "model_baseline.joblib",
    )
    joblib.dump(
        {"model": enhanced_model, "features": enhanced_features},
        ARTIFACT_DIR / "model_enhanced.joblib",
    )
    table.to_csv(ARTIFACT_DIR / "comparison.csv", index=False)
    segments.to_csv(ARTIFACT_DIR / "segments.csv", index=False)

    feature_hash = hashlib.sha256(",".join(enhanced_features).encode()).hexdigest()[:16]
    metadata = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_provenance": provenance,
        "n_applicants": int(len(df)),
        "target_loss_rate": args.target_loss,
        "random_seed": RANDOM_SEED,
        "estimator": "sklearn.ensemble.HistGradientBoostingClassifier",
        "sklearn_version": sklearn.__version__,
        "model_params": MODEL_PARAMS,
        "baseline_features": baseline_features,
        "enhanced_features": enhanced_features,
        "feature_set_hash": feature_hash,
        "iterations_baseline": int(baseline_model.n_iter_),
        "iterations_enhanced": int(enhanced_model.n_iter_),
        "monotone_constraints": {
            k: v for k, v in MONOTONE_DIRECTIONS.items() if k in enhanced_features
        },
    }
    (ARTIFACT_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))

    print(f"\nArtifacts written to {ARTIFACT_DIR.resolve()}")


if __name__ == "__main__":
    main()
