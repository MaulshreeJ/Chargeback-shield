"""Merchant-level dispute-ratio rollup: an operational monitoring view over
the full synthetic transaction history -- "which merchants are chronically
high-risk?" -- distinct from the model's own causal per-transaction feature
(merchant_dispute_rate_90d in src/features.py, computed from only a
merchant's prior history at each transaction, to avoid leakage).

This rollup is allowed to use each merchant's FULL history (including
transactions after any given point) because it's a reporting view for a
human to look at, not a training or scoring signal -- there's no leakage
concern for a dashboard that says "here's how a merchant looks today."

Run: python -m scripts.merchant_rollup
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.data_gen import generate

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "transactions.csv"
OUT_PATH = ROOT / "reports" / "merchant_rollup.json"

# Below this many transactions, a merchant's dispute rate is too noisy to
# act on (e.g. 1 dispute out of 3 transactions is a 33% "rate" that means
# almost nothing) -- excluded from the ranked lists, though still counted
# in total_merchants.
MIN_VOLUME_THRESHOLD = 20


def main():
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    else:
        df = generate()

    grouped = df.groupby("merchant_id")
    rows = []
    for merchant_id, g in grouped:
        txn_count = int(len(g))
        dispute_count = int(g["disputed"].sum())
        disputed_rows = g[g["disputed"] == True]  # noqa: E712
        top_reason = (
            disputed_rows["reason_code"].mode().iat[0]
            if len(disputed_rows) and not disputed_rows["reason_code"].mode().empty
            else None
        )
        rows.append(
            {
                "merchant_id": merchant_id,
                "txn_count": txn_count,
                "dispute_count": dispute_count,
                "dispute_rate": round(dispute_count / txn_count, 4) if txn_count else 0.0,
                "avg_amount": round(float(g["amount"].mean()), 2),
                "top_reason_code": top_reason,
            }
        )

    eligible = [r for r in rows if r["txn_count"] >= MIN_VOLUME_THRESHOLD]
    highest_risk = sorted(eligible, key=lambda r: r["dispute_rate"], reverse=True)[:10]
    lowest_risk = sorted(eligible, key=lambda r: r["dispute_rate"])[:5]

    rollup = {
        "min_volume_threshold": MIN_VOLUME_THRESHOLD,
        "total_merchants": len(rows),
        "merchants_meeting_threshold": len(eligible),
        "overall_dispute_rate": round(float(df["disputed"].mean()), 4),
        "highest_risk_merchants": highest_risk,
        "lowest_risk_merchants": lowest_risk,
        "note": (
            "Computed over the full synthetic transaction history (src/data_gen.py), "
            f"filtered to merchants with at least {MIN_VOLUME_THRESHOLD} transactions to "
            "avoid noisy small-sample dispute rates. This is an operational monitoring "
            "view, not the leakage-safe per-transaction feature the model trains on -- "
            "see merchant_dispute_rate_90d in src/features.py for that."
        ),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rollup, f, indent=2)
    print(json.dumps(rollup, indent=2))


if __name__ == "__main__":
    main()
