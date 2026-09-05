"""FastAPI surface: score a transaction, generate an evidence packet for
a dispute, inspect an audit record, and read the last training metrics.
Run: uvicorn src.api:app --reload
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

load_dotenv()  # picks up GEMINI_API_KEY / GEMINI_MODEL from .env if present

from src.audit import get_event, log_event
from src.data_gen import generate as generate_data
from src.data_gen import generate_evidence_store
from src.evidence_engine import build_packet
from src.model import RiskModel
from src.narrative import draft_narrative
from src.schemas import Dispute, EvidencePacket, RiskScore, Transaction

app = FastAPI(title="Chargeback Shield", version="0.1.0")

# allow_origins=["*"] + allow_credentials=True is an invalid combination
# per the CORS spec (browsers won't send credentials to a wildcard
# origin) -- this API uses no cookies/auth, so credentials stay off and
# the wildcard origin is safe for local demo/grading use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "transactions.csv"
DASHBOARD_PATH = Path(__file__).resolve().parent / "static" / "dashboard.html"

_model: RiskModel | None = None
_evidence_store_cache: dict | None = None
_dataset_cache: pd.DataFrame | None = None


def get_dataset() -> pd.DataFrame:
    global _dataset_cache
    if _dataset_cache is None:
        if DATA_PATH.exists():
            _dataset_cache = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
        else:
            _dataset_cache = generate_data()
    return _dataset_cache


def get_model() -> RiskModel:
    global _model
    if _model is None:
        _model = RiskModel()
    return _model


@app.get("/", response_class=HTMLResponse)
def dashboard():
    if not DASHBOARD_PATH.exists():
        raise HTTPException(status_code=404, detail="Dashboard not found.")
    return DASHBOARD_PATH.read_text(encoding="utf-8")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sample-disputes")
def sample_disputes(limit: int = 15):
    """A handful of real (synthetic) disputed transactions, for the
    dashboard's evidence-packet demo dropdown -- so a viewer can generate
    a packet without hand-typing a transaction_id and reason code.
    """
    df = get_dataset()
    disputed = df[df["disputed"] == True]  # noqa: E712
    sample = disputed.sample(n=min(limit, len(disputed)), random_state=1) if len(disputed) else disputed
    return [
        {
            "transaction_id": row["transaction_id"],
            "reason_code": row["reason_code"],
            "amount": float(row["amount"]),
            "category": row["category"],
        }
        for _, row in sample.iterrows()
    ]


@app.get("/packet-metrics")
def packet_metrics():
    path = REPORTS_DIR / "packet_metrics.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="No packet metrics yet. Run `python -m scripts.evaluate_packets` first.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/merchants/rollup")
def merchants_rollup():
    path = REPORTS_DIR / "merchant_rollup.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="No merchant rollup yet. Run `python -m scripts.merchant_rollup` first.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/score", response_model=RiskScore)
def score(transaction: Transaction):
    row = pd.DataFrame(
        [
            {
                "amount": transaction.amount,
                "ticket_size_ratio": (
                    transaction.amount / transaction.customer_avg_amount_90d
                    if transaction.customer_avg_amount_90d
                    else 1.0
                ),
                "customer_txn_count_90d": transaction.customer_txn_count_90d,
                "customer_dispute_count_lifetime": transaction.customer_dispute_count_lifetime,
                "customer_refund_count_90d": transaction.customer_refund_count_90d,
                "is_subscription": transaction.is_subscription,
                "category": transaction.category.value,
                "delivery_confirmed": transaction.delivery_confirmed,
                "cross_border": transaction.ip_country != transaction.billing_country,
                "hour_of_day": transaction.timestamp.hour,
                "days_to_deliver": transaction.days_to_deliver or 0.0,
                "merchant_dispute_rate_90d": transaction.merchant_dispute_rate_90d,
                "merchant_txn_count_90d": transaction.merchant_txn_count_90d,
            }
        ]
    )
    try:
        model = get_model()
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model not trained yet. Run `python -m scripts.train` first.",
        )

    prob, band = model.score(row)
    top_factors = model.explain(row)
    result = RiskScore(
        transaction_id=transaction.transaction_id,
        dispute_probability=round(prob, 4),
        risk_band=band,
        model_version=model.clf.__class__.__name__,
        top_factors=top_factors,
    )
    log_event(
        audit_id=f"score-{transaction.transaction_id}",
        event_type="risk_score",
        subject_id=transaction.transaction_id,
        payload=result.model_dump(),
    )
    return result


@app.post("/disputes/packet", response_model=EvidencePacket)
def dispute_packet(dispute: Dispute):
    """Build an evidence packet for a filed dispute.

    Demo convenience: looks up a simulated evidence store from the synthetic
    dataset if this transaction_id happens to be in it, so the endpoint is
    demoable standalone. A real deployment would call an evidence-retrieval
    service here instead -- the policy logic in evidence_engine.py doesn't
    change either way.
    """
    global _evidence_store_cache
    if _evidence_store_cache is None:
        df = generate_data()
        _evidence_store_cache = generate_evidence_store(df)
    store = _evidence_store_cache.get(dispute.transaction_id, {})

    packet = build_packet(dispute, dispute.transaction_id, store)

    # Optional cosmetic layer: an LLM may phrase the case for a human
    # reader, but it never touches recommendation/completeness/confidence,
    # and if it's unavailable for any reason the packet is still complete
    # and usable with just `rationale`.
    packet.narrative = draft_narrative(packet)

    log_event(
        audit_id=packet.audit_id,
        event_type="evidence_packet",
        subject_id=dispute.dispute_id,
        payload=packet.model_dump(),
    )
    return packet


@app.get("/audit/{audit_id}")
def audit(audit_id: str):
    event = get_event(audit_id)
    if event is None:
        raise HTTPException(status_code=404, detail="No audit record with that id.")
    return event


@app.get("/metrics")
def metrics():
    path = REPORTS_DIR / "metrics.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No metrics yet. Run `python -m scripts.train` first.")
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)

