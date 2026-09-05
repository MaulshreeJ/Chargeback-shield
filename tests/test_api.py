from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_dashboard_serves_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "Chargeback Shield" in r.text


def test_sample_disputes_returns_list():
    r = client.get("/sample-disputes?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) <= 5
    if body:
        assert "transaction_id" in body[0]
        assert "reason_code" in body[0]


def test_score_endpoint():
    payload = {
        "transaction_id": "TXN-TEST-1", "customer_id": "C1", "merchant_id": "M1",
        "amount": 3000, "currency": "INR", "timestamp": "2026-08-29T10:00:00Z",
        "category": "digital", "delivery_confirmed": False, "is_subscription": False,
        "ip_country": "US", "billing_country": "IN",
        "customer_txn_count_90d": 0, "customer_dispute_count_lifetime": 0,
        "customer_refund_count_90d": 0, "customer_avg_amount_90d": 0,
    }
    r = client.post("/score", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["dispute_probability"] <= 1.0
    assert body["risk_band"] in ("LOW", "MEDIUM", "HIGH")


def test_packet_endpoint_and_audit_lookup():
    payload = {
        "dispute_id": "DSP-TEST-1", "transaction_id": "TXN000010",
        "reason_code": "PRODUCT_NOT_RECEIVED", "amount": 3000, "filed_at": "2026-08-30T10:00:00Z",
    }
    r = client.post("/disputes/packet", json=payload)
    assert r.status_code == 200
    packet = r.json()
    assert packet["recommendation"] in ("FIGHT", "CONCEDE", "REVIEW")

    r2 = client.get(f"/audit/{packet['audit_id']}")
    assert r2.status_code == 200
    assert r2.json()["event_type"] == "evidence_packet"


def test_audit_lookup_missing_returns_404():
    r = client.get("/audit/does-not-exist")
    assert r.status_code == 404


def test_merchants_rollup_endpoint():
    r = client.get("/merchants/rollup")
    assert r.status_code == 200
    body = r.json()
    assert "highest_risk_merchants" in body
    assert "overall_dispute_rate" in body
    if body["highest_risk_merchants"]:
        top = body["highest_risk_merchants"][0]
        assert "merchant_id" in top and "dispute_rate" in top
