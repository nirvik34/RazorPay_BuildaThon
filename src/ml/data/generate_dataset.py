"""Generate a reproducible synthetic dataset of agent payment requests.

Distribution mirrors the PRD scenarios: legitimate, over-limit, intent mismatch,
new merchant, transaction splitting, compromised bursts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

TRANSACTION_LIMIT = 20000
DAILY_LIMIT = 75000

KNOWN_MERCHANTS = ["amazon", "flipkart", "bigbasket", "croma"]
UNKNOWN_MERCHANTS = ["shopquick", "gadgethub", "megamart", "valuecart", "techdeals"]
ALLOWED_CATEGORIES = ["electronics", "groceries", "office_supplies"]
ALL_CATEGORIES = ALLOWED_CATEGORIES + ["gift_cards", "gambling", "cryptocurrency"]


def generate(count: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    idx = 0

    def base(label: str) -> dict:
        nonlocal idx
        idx += 1
        return {
            "request_id": f"sim_{idx:06d}",
            "label": label,
            "merchant_known": 0,
            "category_allowed": 1,
            "amount": 0,
            "amount_ratio": 0.0,
            "hour": int(rng.integers(8, 21)),
            "velocity_10m": 0,
            "category_familiar": 1,
            "prior_blocks_today": 0,
        }

    n_legit = int(count * 0.62)
    for _ in range(n_legit):
        r = base("legit")
        r["merchant_known"] = int(rng.random() < 0.85)
        r["amount"] = int(rng.integers(150, 9000))
        r["velocity_10m"] = int(rng.integers(0, 3))
        rows.append(r)

    n_over = int(count * 0.12)
    for _ in range(n_over):
        r = base("over_limit")
        r["merchant_known"] = int(rng.random() < 0.6)
        r["amount"] = int(rng.integers(22000, 60000))
        rows.append(r)

    n_intent = int(count * 0.08)
    for _ in range(n_intent):
        r = base("intent_mismatch")
        r["merchant_known"] = 1
        r["category_allowed"] = 0
        r["category_familiar"] = 0
        r["amount"] = int(rng.integers(3000, 12000))
        rows.append(r)

    n_new = int(count * 0.10)
    for _ in range(n_new):
        r = base("new_merchant")
        r["amount"] = int(rng.integers(800, 15000))
        rows.append(r)

    while len(rows) < count * 0.97:
        group_size = int(rng.integers(3, 4))
        session_hour = int(rng.integers(0, 24))
        for k in range(group_size):
            r = base("splitting")
            r["merchant_known"] = int(rng.random() < 0.3)
            r["amount"] = int(9400 + rng.integers(-400, 400))
            r["hour"] = session_hour
            r["velocity_10m"] = k
            r["prior_blocks_today"] = 0 if k < 2 else 1
            rows.append(r)

    while len(rows) < count:
        burst = int(rng.integers(6, 9))
        start_hour = int(rng.choice([0, 1, 2, 23]))
        for k in range(burst):
            r = base("compromised")
            r["amount"] = int(rng.integers(1500, 8000))
            r["hour"] = start_hour
            r["velocity_10m"] = k + 2
            r["category_familiar"] = int(rng.random() < 0.5)
            rows.append(r)

    df = pd.DataFrame(rows[:count])
    df["amount_ratio"] = (df["amount"] / TRANSACTION_LIMIT).round(3)
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=str(Path(__file__).parent / "dataset.csv"))
    args = parser.parse_args()

    frame = generate(args.count, args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.out, index=False)
    print(f"Wrote {len(frame)} rows to {args.out}")
    print(frame.groupby("label").size().to_string())


if __name__ == "__main__":
    main()
