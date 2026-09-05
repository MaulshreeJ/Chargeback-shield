"""Evaluate the evidence-packet engine over the synthetic disputed
transactions: packet completeness and how fight/concede/review splits
on this batch. Run: python -m scripts.evaluate_packets
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.data_gen import generate, generate_evidence_store
from src.evidence_engine import build_packet
from src.schemas import Dispute

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "transactions.csv"
OUT_PATH = ROOT / "reports" / "packet_metrics.json"


def main():
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    else:
        df = generate()

    disputed = df[df["disputed"] == True].copy()  # noqa: E712
    evidence_store = generate_evidence_store(df)

    packets = []
    for _, row in disputed.iterrows():
        dispute = Dispute(
            dispute_id=f"DSP-{row['transaction_id']}",
            transaction_id=row["transaction_id"],
            reason_code=row["reason_code"],
            amount=row["amount"],
            filed_at=row["timestamp"],
        )
        packet = build_packet(dispute, row["transaction_id"], evidence_store[row["transaction_id"]])
        packets.append(packet)

    n = len(packets)
    full = sum(1 for p in packets if p.completeness_ratio >= 0.999)
    by_rec: dict[str, int] = {}
    for p in packets:
        by_rec[p.recommendation.value] = by_rec.get(p.recommendation.value, 0) + 1

    metrics = {
        "disputed_transactions": n,
        "packets_fully_complete": full,
        "packets_fully_complete_pct": round(full / n, 3) if n else 0,
        "avg_completeness_ratio": round(sum(p.completeness_ratio for p in packets) / n, 3) if n else 0,
        "recommendation_breakdown": by_rec,
        "note": "Computed on the same synthetic disputed-transaction batch data_gen.py produces.",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
