"""Deterministic evidence assembly + fight/concede policy.

Design rule (non-negotiable, ties to the track's "defense-only" clause):
this module never invents evidence. It only reports which *actually
retrievable* evidence items exist for a dispute, and applies a fixed,
auditable policy on top of that honest count. Nothing here calls an LLM.
A narrative-drafting layer (LLM) could sit ON TOP of this later purely to
phrase the packet for human submission -- it would never be allowed to
change which evidence counts as present or alter the recommendation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from src.schemas import Dispute, EvidenceItem, EvidencePacket, ReasonCode, Recommendation

# Per-reason-code evidence requirements. Modeled on the evidence categories
# card networks actually ask for per dispute reason; simplified for a v1.
REASON_EVIDENCE_MAP: dict[ReasonCode, list[str]] = {
    ReasonCode.PRODUCT_NOT_RECEIVED: [
        "delivery_confirmation",
        "tracking_number",
        "shipping_carrier_proof",
    ],
    ReasonCode.UNAUTHORIZED_TRANSACTION: [
        "avs_cvv_match",
        "device_fingerprint",
        "prior_txn_history_same_device",
    ],
    ReasonCode.NOT_AS_DESCRIBED: [
        "product_description_snapshot",
        "customer_communication_log",
    ],
    ReasonCode.DUPLICATE_PROCESSING: [
        "duplicate_transaction_check",
        "unique_order_id_proof",
    ],
    ReasonCode.SUBSCRIPTION_CANCELLED: [
        "cancellation_policy_ack",
        "subscription_terms_timestamp",
        "usage_after_cancellation_log",
    ],
    ReasonCode.CREDIT_NOT_PROCESSED: [
        "refund_transaction_proof",
        "refund_policy_ack",
    ],
}

# Below this disputed amount, network/ops cost of fighting exceeds the
# expected recovery even with perfect evidence -- always concede.
MIN_FIGHT_AMOUNT = 150.0

FIGHT_COMPLETENESS_THRESHOLD = 0.80
CONCEDE_COMPLETENESS_THRESHOLD = 0.40


def collect_evidence(dispute: Dispute, evidence_store: dict[str, bool]) -> list[EvidenceItem]:
    """Look up which required evidence items are actually available.

    `evidence_store` simulates a real system-of-record lookup (delivery
    logs, device fingerprints, support tickets, ...): {evidence_type: bool}.
    Anything not present in the store is honestly reported as absent.
    """
    required = REASON_EVIDENCE_MAP[dispute.reason_code]
    items = []
    for etype in required:
        present = bool(evidence_store.get(etype, False))
        items.append(
            EvidenceItem(
                type=etype,
                present=present,
                source_ref=f"{dispute.transaction_id}:{etype}" if present else None,
            )
        )
    return items


def decide(dispute: Dispute, evidence: list[EvidenceItem]) -> tuple[Recommendation, float, str]:
    """Fixed, auditable fight/concede/review policy. No model, no LLM."""
    required_count = len(evidence)
    collected_count = sum(1 for e in evidence if e.present)
    completeness = collected_count / required_count if required_count else 0.0

    if dispute.amount < MIN_FIGHT_AMOUNT:
        return (
            Recommendation.CONCEDE,
            1.0,
            f"Disputed amount ({dispute.amount:.2f}) is below the minimum "
            f"fight threshold ({MIN_FIGHT_AMOUNT:.2f}); network/ops cost of "
            f"contesting exceeds any realistic recovery regardless of evidence.",
        )

    if completeness >= FIGHT_COMPLETENESS_THRESHOLD:
        return (
            Recommendation.FIGHT,
            round(completeness, 3),
            f"{collected_count}/{required_count} required evidence items are "
            f"available for reason code {dispute.reason_code.value}; case is "
            f"strong enough to contest.",
        )

    if completeness < CONCEDE_COMPLETENESS_THRESHOLD:
        return (
            Recommendation.CONCEDE,
            round(1 - completeness, 3),
            f"Only {collected_count}/{required_count} required evidence items "
            f"are available; contesting is unlikely to succeed and would "
            f"waste ops time and network fees.",
        )

    return (
        Recommendation.REVIEW,
        round(completeness, 3),
        f"{collected_count}/{required_count} required evidence items are "
        f"available -- borderline case, routed to a human reviewer rather "
        f"than auto-decided.",
    )


def build_packet(dispute: Dispute, transaction_id: str, evidence_store: dict[str, bool]) -> EvidencePacket:
    evidence = collect_evidence(dispute, evidence_store)
    recommendation, confidence, rationale = decide(dispute, evidence)
    required = REASON_EVIDENCE_MAP[dispute.reason_code]
    collected = sum(1 for e in evidence if e.present)
    return EvidencePacket(
        audit_id=str(uuid.uuid4()),
        dispute_id=dispute.dispute_id,
        transaction_id=transaction_id,
        reason_code=dispute.reason_code,
        required_evidence=required,
        collected_evidence=evidence,
        completeness_ratio=round(collected / len(required), 3) if required else 0.0,
        recommendation=recommendation,
        confidence=confidence,
        rationale=rationale,
        generated_at=datetime.now(timezone.utc),
    )
