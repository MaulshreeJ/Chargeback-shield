"""Append-only audit trail, backed by a JSONL file.

Deliberately not SQLite: this project's folder can live on a mounted or
synced drive (network share, cloud-synced folder, WSL/VM bind mount) where
SQLite's file locking can fail with "disk I/O error". A plain append-only
JSONL file has no locking requirements and is trivially inspectable
(grep it, or load it into pandas) -- which matters more for an audit trail
than query performance at this scale.

Every risk score and every evidence-packet decision gets one line, so any
single decision can be pulled back out with its exact inputs and rationale.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "reports" / "audit_log.jsonl"


def log_event(audit_id: str, event_type: str, subject_id: str, payload: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "audit_id": audit_id,
        "event_type": event_type,
        "subject_id": subject_id,
        "payload": payload,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def get_event(audit_id: str) -> dict | None:
    """Returns the most recent record for this audit_id, or None."""
    if not LOG_PATH.exists():
        return None
    match = None
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record["audit_id"] == audit_id:
                match = record
    return match
