import src.audit as audit_module


def test_log_and_get_event(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_module, "LOG_PATH", tmp_path / "audit_log.jsonl")
    audit_module.log_event("a1", "risk_score", "TXN-1", {"prob": 0.9})
    event = audit_module.get_event("a1")
    assert event is not None
    assert event["event_type"] == "risk_score"
    assert event["subject_id"] == "TXN-1"
    assert event["payload"]["prob"] == 0.9


def test_missing_event_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_module, "LOG_PATH", tmp_path / "audit_log2.jsonl")
    assert audit_module.get_event("does-not-exist") is None


def test_later_write_wins_on_same_audit_id(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_module, "LOG_PATH", tmp_path / "audit_log3.jsonl")
    audit_module.log_event("a1", "risk_score", "TXN-1", {"prob": 0.1})
    audit_module.log_event("a1", "risk_score", "TXN-1", {"prob": 0.9})
    event = audit_module.get_event("a1")
    assert event["payload"]["prob"] == 0.9
