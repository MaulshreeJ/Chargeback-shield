"""Synthetic transaction + dispute generator.

No real Razorpay or cardholder data is used anywhere in this project.
Every number below is invented to encode *documented correlates* of
friendly-fraud disputes (digital goods with no delivery proof, repeat
disputers, cross-border mismatches, oversized first-time purchases) --
not fitted to any real dataset. This file is the single source of
"ground truth", and every metric this project reports should be read
against that fact.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

RNG_SEED = 42
N_CUSTOMERS = 400
N_MERCHANTS = 60
N_TRANSACTIONS = 20000  # bumped from 6000: more positive examples (~1900 vs ~570) for the model to learn from

REASON_CODES = [
    "PRODUCT_NOT_RECEIVED",
    "UNAUTHORIZED_TRANSACTION",
    "NOT_AS_DESCRIBED",
    "DUPLICATE_PROCESSING",
    "SUBSCRIPTION_CANCELLED",
    "CREDIT_NOT_PROCESSED",
]


def _pick_reason(row: dict, rng: random.Random) -> str:
    if row["is_subscription"] and rng.random() < 0.5:
        return "SUBSCRIPTION_CANCELLED"
    if row["category"] == "digital" and not row["delivery_confirmed"] and rng.random() < 0.55:
        return "PRODUCT_NOT_RECEIVED"
    if row["cross_border"] and rng.random() < 0.5:
        return "UNAUTHORIZED_TRANSACTION"
    if row["category"] == "digital" and rng.random() < 0.3:
        return "NOT_AS_DESCRIBED"
    return rng.choice(REASON_CODES)


def generate(n_transactions: int = N_TRANSACTIONS, seed: int = RNG_SEED) -> pd.DataFrame:
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    customer_ids = [f"CUST{i:05d}" for i in range(N_CUSTOMERS)]
    merchant_ids = [f"MERC{i:04d}" for i in range(N_MERCHANTS)]
    repeat_disputer = {cid: (np_rng.random() < 0.07) for cid in customer_ids}
    # Merchant-level heterogeneity: chargeback literature documents that
    # dispute risk clusters by merchant (fulfillment reliability, support
    # responsiveness, refund friendliness) independent of any single
    # transaction's own features. Modeled here as one fixed, invented
    # "quality" draw per merchant -- not fit to any real merchant data,
    # same discipline as every other correlate in this file.
    merchant_quality = {mid: float(np_rng.normal(0, 1)) for mid in merchant_ids}
    merchant_state = {mid: {"txn_count": 0, "dispute_count": 0} for mid in merchant_ids}

    state = {
        cid: {"txn_count": 0, "dispute_count": 0, "refund_count": 0, "amount_hist": []}
        for cid in customer_ids
    }

    start = datetime(2026, 3, 1, tzinfo=timezone.utc)
    raw = []
    for i in range(n_transactions):
        cid = rng.choice(customer_ids)
        mid = rng.choice(merchant_ids)
        ts = start + timedelta(minutes=int(np_rng.uniform(0, 180 * 24 * 60)))
        raw.append((ts, cid, mid))
    raw.sort(key=lambda x: x[0])

    rows = []
    for idx, (ts, cid, mid) in enumerate(raw):
        st = state[cid]
        category = rng.choices(["digital", "physical"], weights=[0.4, 0.6])[0]
        is_subscription = category == "digital" and rng.random() < 0.25
        cross_border = rng.random() < (0.15 if repeat_disputer[cid] else 0.04)

        base_amount = np_rng.lognormal(mean=6.2 if category == "physical" else 5.6, sigma=0.6)
        if st["txn_count"] == 0 and rng.random() < 0.12:
            base_amount *= rng.uniform(2.5, 5.0)
        amount = round(float(base_amount), 2)

        if category == "physical":
            delivery_confirmed = rng.random() < 0.93
            days_to_deliver = round(rng.uniform(1, 9), 1)
        else:
            delivery_confirmed = rng.random() < 0.78
            days_to_deliver = 0.0

        avg_amount = (sum(st["amount_hist"]) / len(st["amount_hist"])) if st["amount_hist"] else amount
        ticket_size_ratio = amount / avg_amount if avg_amount else 1.0

        # Causal merchant history: computed from ONLY this merchant's prior
        # transactions (transactions are processed in time order and state
        # updated after each one, exactly like the customer fields above) --
        # never from data the model wouldn't actually have yet at scoring
        # time. Laplace-smoothed toward the dataset's overall dispute rate
        # (roughly 10%, via the +1 / +10 pseudo-counts) so a merchant with
        # only 1-2 transactions doesn't get a wild 0% or 100% estimate.
        mst = merchant_state[mid]
        merchant_dispute_rate_90d = (mst["dispute_count"] + 1) / (mst["txn_count"] + 10)
        merchant_txn_count_90d = mst["txn_count"]

        row = {
            "transaction_id": f"TXN{idx:06d}",
            "customer_id": cid,
            "merchant_id": mid,
            "amount": amount,
            "timestamp": ts,
            "category": category,
            "delivery_confirmed": delivery_confirmed,
            "days_to_deliver": days_to_deliver,
            "is_subscription": is_subscription,
            "cross_border": cross_border,
            "ip_country": "US" if cross_border else "IN",
            "billing_country": "IN",
            "customer_txn_count_90d": st["txn_count"],
            "customer_dispute_count_lifetime": st["dispute_count"],
            "customer_refund_count_90d": st["refund_count"],
            "customer_avg_amount_90d": round(avg_amount, 2),
            "ticket_size_ratio": round(ticket_size_ratio, 3),
            "merchant_dispute_rate_90d": round(merchant_dispute_rate_90d, 4),
            "merchant_txn_count_90d": merchant_txn_count_90d,
            "hour_of_day": ts.hour,
        }

        z = -3.4
        z += 0.5 * merchant_quality[mid]
        z += 1.8 if (row["category"] == "digital" and not delivery_confirmed) else 0
        z += 1.3 if cross_border else 0
        z += 1.1 if is_subscription else 0
        z += 0.9 * min(ticket_size_ratio - 1, 4) if ticket_size_ratio > 1.8 else 0
        z += 1.6 if repeat_disputer[cid] else 0
        z += 0.7 if st["txn_count"] == 0 else 0
        z += 0.4 if row["hour_of_day"] in (0, 1, 2, 3) else 0
        prob = 1 / (1 + np.exp(-z))
        disputed = np_rng.random() < prob

        row["disputed"] = bool(disputed)
        if disputed:
            row["reason_code"] = _pick_reason(row, rng)
            st["dispute_count"] += 1
        else:
            row["reason_code"] = None
            if rng.random() < 0.05:
                st["refund_count"] += 1

        st["txn_count"] += 1
        st["amount_hist"].append(amount)
        mst["txn_count"] += 1
        if disputed:
            mst["dispute_count"] += 1
        rows.append(row)

    return pd.DataFrame(rows)


def generate_evidence_store(df: pd.DataFrame, seed: int = RNG_SEED) -> dict[str, dict[str, bool]]:
    """For every disputed transaction, simulate which evidence items a real
    system-of-record would actually be able to produce. Deliberately
    imperfect -- real evidence retrieval is never 100%.
    """
    rng = random.Random(seed + 1)
    store: dict[str, dict[str, bool]] = {}
    for _, row in df[df["disputed"]].iterrows():
        ev: dict[str, bool] = {}
        if row["category"] == "physical":
            ev["delivery_confirmation"] = bool(row["delivery_confirmed"]) and rng.random() < 0.9
            ev["tracking_number"] = ev["delivery_confirmation"] and rng.random() < 0.95
            ev["shipping_carrier_proof"] = ev["tracking_number"] and rng.random() < 0.85
        else:
            ev["delivery_confirmation"] = bool(row["delivery_confirmed"]) and rng.random() < 0.7
            ev["tracking_number"] = False
            ev["shipping_carrier_proof"] = False
        ev["avs_cvv_match"] = rng.random() < (0.3 if row["cross_border"] else 0.85)
        ev["device_fingerprint"] = rng.random() < 0.75
        ev["prior_txn_history_same_device"] = row["customer_txn_count_90d"] > 0 and rng.random() < 0.8
        ev["product_description_snapshot"] = rng.random() < 0.8
        ev["customer_communication_log"] = rng.random() < 0.5
        ev["duplicate_transaction_check"] = rng.random() < 0.9
        ev["unique_order_id_proof"] = rng.random() < 0.95
        ev["cancellation_policy_ack"] = bool(row["is_subscription"]) and rng.random() < 0.6
        ev["subscription_terms_timestamp"] = bool(row["is_subscription"]) and rng.random() < 0.9
        ev["usage_after_cancellation_log"] = bool(row["is_subscription"]) and rng.random() < 0.4
        ev["refund_transaction_proof"] = rng.random() < 0.3
        ev["refund_policy_ack"] = rng.random() < 0.8
        store[row["transaction_id"]] = ev
    return store


if __name__ == "__main__":
    from pathlib import Path

    out_dir = Path(__file__).resolve().parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_csv(out_dir / "transactions.csv", index=False)
    print(f"wrote {len(df)} transactions to {out_dir/'transactions.csv'}")
    print(f"dispute rate: {df['disputed'].mean():.3%}")
