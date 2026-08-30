"""
Generate a synthetic Pakistani loan-admissions dataset with deliberate,
realistic bias for demo purposes.

Bias baked in:
  1. URBAN BIAS (primary) – applicants from Multan, Peshawar, and Quetta
     face a noticeably lower approval rate than Lahore / Karachi / Islamabad,
     even at similar income and credit-score levels.
  2. GENDER BIAS (secondary) – female applicants face a smaller but
     measurable approval penalty on top of the lending logic.

The base lending model is a logistic function of monthly_income and
credit_score so higher income / credit score genuinely correlates with
approval.  The bias terms are additive penalties in log-odds space, layered
on top of that realistic baseline.

Usage:
    python generate_pakistani_dataset.py          # writes CSV next to this file
    python generate_pakistani_dataset.py --rows 500 --seed 99
"""

import argparse
import math
import os
import random
from typing import List, Dict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CITIES_MAJOR = ["Lahore", "Karachi", "Islamabad"]
CITIES_MINOR = ["Multan", "Peshawar", "Quetta"]

EDUCATION_LEVELS = [
    "Matric",
    "Intermediate",
    "Bachelors",
    "Masters",
    "PhD",
]

# City weight for sampling (major cities get more applicants)
CITY_WEIGHTS = {
    "Lahore": 25,
    "Karachi": 25,
    "Islamabad": 18,
    "Multan": 12,
    "Peshawar": 11,
    "Quetta": 9,
}

# Gender split
GENDER_OPTIONS = ["male", "female"]
GENDER_WEIGHTS = [52, 48]  # slight male majority, realistic for Pakistan

# Base lending model parameters (logistic regression in log-odds space)
# These make income and credit_score the primary drivers of approval.
INCOME_COEFF = 0.000020       # per PKR of monthly income
CREDIT_COEFF = 0.004          # per point of credit score
BASE_INTERCEPT = -3.2         # baseline log-odds (calibrated for ~65% base rate)

# Bias terms (additive log-odds penalties)
CITY_MINOR_PENALTY = -1.0     # strong urban bias (~25pp gap)
GENDER_FEMALE_PENALTY = -0.45 # secondary gender bias (~10pp gap)


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def generate_row(rng: random.Random) -> Dict:
    """Generate one synthetic applicant row."""
    gender = rng.choices(GENDER_OPTIONS, weights=GENDER_WEIGHTS, k=1)[0]
    age = rng.randint(21, 65)

    all_cities = CITIES_MAJOR + CITIES_MINOR
    city_weights = [CITY_WEIGHTS[c] for c in all_cities]
    city = rng.choices(all_cities, weights=city_weights, k=1)[0]

    education = rng.choices(
        EDUCATION_LEVELS,
        weights=[15, 25, 30, 22, 8],
        k=1,
    )[0]

    # Income: 15k–250k PKR, skewed right (more lower-income applicants)
    monthly_income = round(rng.gammavariate(3.0, 18000))
    monthly_income = max(15000, min(250000, monthly_income))

    # Credit score: 300–850, roughly normal around 620
    credit_score = round(rng.gauss(620, 100))
    credit_score = max(300, min(850, credit_score))

    # --- Approval probability (logistic model) ---
    log_odds = (
        BASE_INTERCEPT
        + INCOME_COEFF * monthly_income
        + CREDIT_COEFF * credit_score
    )

    # Urban bias
    if city in CITIES_MINOR:
        # Add some noise so the penalty isn't perfectly uniform
        log_odds += CITY_MINOR_PENALTY + rng.gauss(0, 0.08)

    # Gender bias
    if gender == "female":
        log_odds += GENDER_FEMALE_PENALTY + rng.gauss(0, 0.05)

    prob = sigmoid(log_odds)
    approved = "approved" if rng.random() < prob else "rejected"

    return {
        "gender": gender,
        "age": age,
        "city": city,
        "education_level": education,
        "monthly_income": monthly_income,
        "credit_score": credit_score,
        "loan_approved": approved,
    }


def generate_dataset(n_rows: int, seed: int) -> List[Dict]:
    rng = random.Random(seed)
    return [generate_row(rng) for _ in range(n_rows)]


def print_breakdown(rows: List[Dict]) -> None:
    """Print approval-rate breakdowns by city and gender."""
    # By city
    city_stats: Dict[str, Dict[str, int]] = {}
    for r in rows:
        c = r["city"]
        city_stats.setdefault(c, {"approved": 0, "total": 0})
        city_stats[c]["total"] += 1
        if r["loan_approved"] == "approved":
            city_stats[c]["approved"] += 1

    print("\n=== Approval Rate by City ===")
    print(f"{'City':<14} {'Approved':>8} {'Total':>6} {'Rate':>7}")
    print("-" * 38)
    for city in CITIES_MAJOR + CITIES_MINOR:
        s = city_stats.get(city, {"approved": 0, "total": 0})
        rate = s["approved"] / s["total"] if s["total"] else 0
        tag = " *" if city in CITIES_MINOR else ""
        print(f"{city + tag:<14} {s['approved']:>8} {s['total']:>6} {rate:>6.1%}")

    # By gender
    gender_stats: Dict[str, Dict[str, int]] = {}
    for r in rows:
        g = r["gender"]
        gender_stats.setdefault(g, {"approved": 0, "total": 0})
        gender_stats[g]["total"] += 1
        if r["loan_approved"] == "approved":
            gender_stats[g]["approved"] += 1

    print("\n=== Approval Rate by Gender ===")
    print(f"{'Gender':<14} {'Approved':>8} {'Total':>6} {'Rate':>7}")
    print("-" * 38)
    for g in GENDER_OPTIONS:
        s = gender_stats.get(g, {"approved": 0, "total": 0})
        rate = s["approved"] / s["total"] if s["total"] else 0
        print(f"{g:<14} {s['approved']:>8} {s['total']:>6} {rate:>6.1%}")

    # Overall
    total_approved = sum(1 for r in rows if r["loan_approved"] == "approved")
    print(f"\nOverall: {total_approved}/{len(rows)} approved "
          f"({total_approved / len(rows):.1%})")
    print("(* = minor city, expected lower rate due to urban bias)")


def main():
    parser = argparse.ArgumentParser(description="Generate Pakistani loan dataset")
    parser.add_argument("--rows", type=int, default=500, help="Number of rows")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV path (default: same dir as this script)",
    )
    args = parser.parse_args()

    rows = generate_dataset(args.rows, args.seed)

    if args.output:
        out_path = args.output
    else:
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "pakistani_loan_admissions.csv",
        )

    import csv

    fieldnames = [
        "gender", "age", "city", "education_level",
        "monthly_income", "credit_score", "loan_approved",
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows -> {out_path}")
    print_breakdown(rows)


if __name__ == "__main__":
    main()
