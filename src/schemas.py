"""Pydantic data contracts shared across the engine.

Kept deliberately explicit (no free-form dicts crossing module boundaries)
so every score, decision, and audit entry has a fixed, inspectable shape.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Category(str, Enum):
    DIGITAL = "digital"
    PHYSICAL = "physical"


class ReasonCode(str, Enum):
    PRODUCT_NOT_RECEIVED = "PRODUCT_NOT_RECEIVED"
    UNAUTHORIZED_TRANSACTION = "UNAUTHORIZED_TRANSACTION"
    NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED"
    DUPLICATE_PROCESSING = "DUPLICATE_PROCESSING"
    SUBSCRIPTION_CANCELLED = "SUBSCRIPTION_CANCELLED"
    CREDIT_NOT_PROCESSED = "CREDIT_NOT_PROCESSED"


class RiskBand(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Recommendation(str, Enum):
    FIGHT = "FIGHT"
    CONCEDE = "CONCEDE"
    REVIEW = "REVIEW"


class Transaction(BaseModel):
    transaction_id: str
    customer_id: str
    merchant_id: str
    amount: float = Field(gt=0)
    currency: str = "INR"
    timestamp: datetime
    category: Category
    delivery_confirmed: bool
    days_to_deliver: Optional[float] = None
    is_subscription: bool = False
    ip_country: str = "IN"
    billing_country: str = "IN"
    customer_txn_count_90d: int = 0
    customer_dispute_count_lifetime: int = 0
    customer_refund_count_90d: int = 0
    customer_avg_amount_90d: float = 0.0
    merchant_dispute_rate_90d: float = 0.0
    merchant_txn_count_90d: int = 0


class Dispute(BaseModel):
    dispute_id: str
    transaction_id: str
    reason_code: ReasonCode
    amount: float
    filed_at: datetime


class RiskFactor(BaseModel):
    feature: str
    value: Optional[float] = None
    contribution: float  # signed: positive = pushed this transaction's risk up


class RiskScore(BaseModel):
    transaction_id: str
    dispute_probability: float
    risk_band: RiskBand
    model_version: str
    top_factors: list[RiskFactor] = []


class EvidenceItem(BaseModel):
    type: str
    present: bool
    source_ref: Optional[str] = None


class EvidencePacket(BaseModel):
    audit_id: str
    dispute_id: str
    transaction_id: str
    reason_code: ReasonCode
    required_evidence: list[str]
    collected_evidence: list[EvidenceItem]
    completeness_ratio: float
    recommendation: Recommendation
    confidence: float
    rationale: str
    narrative: Optional[str] = None
    generated_at: datetime
