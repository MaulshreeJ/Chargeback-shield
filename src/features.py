"""Feature engineering: raw transaction rows -> numeric matrix the risk
model trains and predicts on. Shared by training and the live API so
the two can never silently drift apart.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "amount",
    "ticket_size_ratio",
    "customer_txn_count_90d",
    "customer_dispute_count_lifetime",
    "customer_refund_count_90d",
    "is_subscription",
    "delivery_confirmed",
    "cross_border",
    "hour_of_day",
    "days_to_deliver",
    "digital_no_delivery",
    "merchant_dispute_rate_90d",
    "merchant_txn_count_90d",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    out["amount"] = df["amount"].astype(float)
    out["ticket_size_ratio"] = df["ticket_size_ratio"].astype(float)
    out["customer_txn_count_90d"] = df["customer_txn_count_90d"].astype(float)
    out["customer_dispute_count_lifetime"] = df["customer_dispute_count_lifetime"].astype(float)
    out["customer_refund_count_90d"] = df["customer_refund_count_90d"].astype(float)
    out["is_subscription"] = df["is_subscription"].astype(int)
    out["delivery_confirmed"] = df["delivery_confirmed"].astype(int)
    out["cross_border"] = df["cross_border"].astype(int)
    out["hour_of_day"] = df["hour_of_day"].astype(float)
    days = df["days_to_deliver"].astype(float)
    out["days_to_deliver"] = days.replace(0.0, np.nan)
    # Explicit interaction: digital goods with no delivery confirmation is
    # the single strongest correlate in this dataset (confirmed by
    # permutation importance during tuning) -- naming it directly gives a
    # depth-limited tree a cheaper path to it than re-deriving the AND.
    out["digital_no_delivery"] = ((df["category"] == "digital") & (~df["delivery_confirmed"].astype(bool))).astype(int)
    out["merchant_dispute_rate_90d"] = df["merchant_dispute_rate_90d"].astype(float)
    out["merchant_txn_count_90d"] = df["merchant_txn_count_90d"].astype(float)
    return out[FEATURE_COLUMNS]
