from datetime import datetime, timezone

from src.evidence_engine import build_packet
from src.schemas import Dispute, ReasonCode, Recommendation


def _dispute(amount, reason=ReasonCode.PRODUCT_NOT_RECEIVED):
    return Dispute(
        dispute_id="DSP-1",
        transaction_id="TXN-1",
        reason_code=reason,
        amount=amount,
        filed_at=datetime.now(timezone.utc),
    )


def test_small_amount_always_concedes_even_with_full_evidence():
    dispute = _dispute(amount=50)
    store = {"delivery_confirmation": True, "tracking_number": True, "shipping_carrier_proof": True}
    packet = build_packet(dispute, "TXN-1", store)
    assert packet.recommendation == Recommendation.CONCEDE


def test_strong_evidence_recommends_fight():
    dispute = _dispute(amount=5000)
    store = {"delivery_confirmation": True, "tracking_number": True, "shipping_carrier_proof": True}
    packet = build_packet(dispute, "TXN-1", store)
    assert packet.recommendation == Recommendation.FIGHT
    assert packet.completeness_ratio == 1.0


def test_weak_evidence_recommends_concede():
    dispute = _dispute(amount=5000)
    store = {}
    packet = build_packet(dispute, "TXN-1", store)
    assert packet.recommendation == Recommendation.CONCEDE


def test_partial_evidence_routes_to_review():
    dispute = _dispute(amount=5000)
    store = {"delivery_confirmation": True, "tracking_number": True}
    packet = build_packet(dispute, "TXN-1", store)
    assert packet.recommendation == Recommendation.REVIEW


def test_never_reports_absent_evidence_as_present():
    dispute = _dispute(amount=5000)
    store = {"delivery_confirmation": True}
    packet = build_packet(dispute, "TXN-1", store)
    present_types = {e.type for e in packet.collected_evidence if e.present}
    assert present_types == {"delivery_confirmation"}
