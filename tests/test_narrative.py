from datetime import datetime, timezone

import src.narrative as narrative_module
from src.evidence_engine import build_packet
from src.schemas import Dispute, ReasonCode


def test_returns_none_when_no_api_key(monkeypatch):
    monkeypatch.setattr(narrative_module, "GEMINI_API_KEY", None)
    dispute = Dispute(
        dispute_id="D1",
        transaction_id="T1",
        reason_code=ReasonCode.PRODUCT_NOT_RECEIVED,
        amount=1000,
        filed_at=datetime.now(timezone.utc),
    )
    packet = build_packet(dispute, "T1", {"delivery_confirmation": True})
    assert narrative_module.draft_narrative(packet) is None
