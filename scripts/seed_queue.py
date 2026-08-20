"""Seed the decision queue with real Home Credit applicants.

Why this exists
---------------
The console is a queue-driven tool. With three records in it, the filters have
nothing to filter and the thin-file share cannot be seen. Pushing a few hundred
genuine applicants through the live API produces a queue that behaves like an
operating system rather than a demonstration, and every record is a real person
from the dataset rather than an invention.

These applications go through the same endpoint, the same policy, and the same
ledger as any other. Nothing is written directly to the database.

Run (with the API already running on :8000):
    python -m scripts.seed_queue --count 250
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from ml.features import is_thin_file
from ml.homecredit import load_homecredit

API_BASE = "http://127.0.0.1:8000"
SEED = 20

# Names are generated because Home Credit is anonymised -- it ships no names at
# all. Every financial attribute is real; only the label on the file is not.
GIVEN_NAMES = [
    "Aarav", "Ananya", "Rohan", "Ishita", "Kabir", "Meera", "Arjun", "Divya",
    "Vikram", "Sneha", "Rahul", "Priyanka", "Karthik", "Lakshmi", "Aditya",
    "Nisha", "Sanjay", "Pooja", "Manish", "Kavya", "Rajesh", "Anjali",
    "Suresh", "Deepa", "Nikhil", "Shreya", "Varun", "Radhika", "Amit", "Neha",
]
FAMILY_NAMES = [
    "Sharma", "Reddy", "Nair", "Iyer", "Patel", "Singh", "Rao", "Menon",
    "Desai", "Gupta", "Kulkarni", "Bose", "Chowdhury", "Pillai", "Joshi",
    "Verma", "Mehta", "Banerjee", "Naidu", "Kapoor",
]

# Upper and lower bounds mirroring the API schema. Values outside these are
# clipped rather than dropped: a clipped extreme is still a truthful ordering
# of that applicant against the others, whereas dropping the field would
# silently convert a known value into "not on file".
BOUNDS: dict[str, tuple[float, float]] = {
    "income_annual": (0, 1e9),
    "employment_years": (0, 60),
    "debt_to_income": (0, 50),
    "age_years": (18, 100),
    "loan_amount": (0, 1e8),
    "loan_term_months": (1, 600),
    "bureau_score": (300, 900),
    "ext_source_1": (0, 1),
    "ext_source_3": (0, 1),
    "bureau_active_accounts": (0, 100),
    "bureau_closed_accounts": (0, 100),
    "bureau_max_days_overdue": (0, 3650),
    "bureau_total_debt": (0, 1e9),
    "credit_history_months": (0, 900),
    "cashflow_inflow_regularity": (0, 3),
    "cashflow_volatility": (0, 5),
    "salary_credit_consistency": (0, 1),
    "avg_monthly_balance": (0, 1e9),
    "balance_trend_90d": (-5, 5),
    "utility_ontime_ratio": (0, 1),
    "rent_ontime_ratio": (0, 1),
    "telecom_recharge_cadence_days": (-400, 400),
    "ecom_txn_count_90d": (0, 10_000),
    "device_tenure_days": (0, 20_000),
}


def build_payload(row: pd.Series, rng: random.Random) -> dict:
    """Convert one dataset row into an API request body."""
    payload: dict[str, object] = {
        "applicant_name": f"{rng.choice(GIVEN_NAMES)} {rng.choice(FAMILY_NAMES)}",
        "external_ref": f"HC-{int(row['application_id'])}",
        "requested_amount": float(
            np.clip(row.get("loan_amount", 200_000) or 200_000, 10_000, 5_000_000)
        ),
    }

    for field, (low, high) in BOUNDS.items():
        value = row.get(field)
        # A missing value is left out entirely. That absence is meaningful --
        # it is what makes an applicant thin-file -- and must not be filled in.
        if value is None or pd.isna(value):
            continue
        payload[field] = float(np.clip(float(value), low, high))

    # Home Credit predates session telemetry, so behavioural signals are
    # simulated. Roughly one application in twenty-five carries fraud markers,
    # which is deliberately higher than reality so the fraud path is visible in
    # a queue of a few hundred rather than a few thousand.
    if rng.random() < 0.04:
        payload.update(
            {
                "form_correction_count": rng.randint(9, 18),
                "pan_field_pasted": True,
                "session_duration_seconds": float(rng.randint(12, 40)),
                "applications_per_device_30d": rng.randint(4, 9),
                "hour_of_day": rng.choice([0, 1, 2, 3, 4, 23]),
                "geo_velocity_kmh": float(rng.randint(320, 900)),
            }
        )
    else:
        payload.update(
            {
                "form_correction_count": rng.randint(0, 6),
                "pan_field_pasted": rng.random() < 0.08,
                "session_duration_seconds": float(rng.randint(90, 600)),
                "applications_per_device_30d": 1,
                "hour_of_day": rng.randint(7, 22),
                "geo_velocity_kmh": float(rng.randint(0, 90)),
            }
        )

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the queue from Home Credit.")
    parser.add_argument("--count", type=int, default=180)
    parser.add_argument("--path", default="data/home-credit")
    parser.add_argument("--api", default=API_BASE)
    parser.add_argument(
        "--thin-share",
        type=float,
        default=0.40,
        help="Share of seeded applicants drawn from the thin-file segment.",
    )
    args = parser.parse_args()

    rng = random.Random(SEED)

    print("Loading Home Credit (this takes a few minutes)...")
    df = load_homecredit(Path(args.path))

    # The dataset is 28% thin-file. Over-sampling that segment slightly gives
    # the console enough thin-file rows to demonstrate the filter without
    # misrepresenting the population -- the true share is reported in the deck
    # from the dataset itself, not from this queue.
    thin_mask = is_thin_file(df).to_numpy()
    thin_target = int(args.count * args.thin_share)

    thin_pool = df[thin_mask].sample(
        n=min(thin_target, int(thin_mask.sum())), random_state=SEED
    )
    thick_pool = df[~thin_mask].sample(
        n=min(args.count - len(thin_pool), int((~thin_mask).sum())), random_state=SEED
    )
    sample = pd.concat([thin_pool, thick_pool]).sample(frac=1, random_state=SEED)

    print(f"Seeding {len(sample)} applications to {args.api} ...")

    tally = {"APPROVE": 0, "REFER": 0, "DECLINE": 0}
    thin_approved = 0
    failures = 0

    with httpx.Client(base_url=args.api, timeout=30.0) as client:
        for position, (_, row) in enumerate(sample.iterrows(), start=1):
            try:
                response = client.post("/v1/decisions", json=build_payload(row, rng))
                response.raise_for_status()
                body = response.json()
                tally[body["outcome"]] = tally.get(body["outcome"], 0) + 1
                if body["is_thin_file"] and body["outcome"] == "APPROVE":
                    thin_approved += 1
            except httpx.HTTPStatusError as exc:
                failures += 1
                if failures <= 3:
                    print(f"  rejected: {exc.response.text[:180]}")
            except httpx.HTTPError as exc:
                print(f"\nAPI unreachable: {exc}")
                print("Start it with: uvicorn backend.main:app --reload --port 8000")
                return

            if position % 25 == 0:
                print(f"  {position}/{len(sample)}")

    total = sum(tally.values())
    print(f"\nSeeded {total} decisions ({failures} rejected)")
    for outcome, count in tally.items():
        share = count / total if total else 0
        print(f"  {outcome:<8} {count:>4}  ({share:.1%})")
    print(f"  thin-file approvals: {thin_approved}")


if __name__ == "__main__":
    main()
