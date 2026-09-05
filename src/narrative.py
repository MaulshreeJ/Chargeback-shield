"""Optional LLM narrative-drafting layer -- pure decoration on top of
evidence_engine's decision, never a decision-maker itself.

This module may ONLY phrase what evidence_engine already decided into
readable prose for a human reviewer. It cannot change the recommendation,
cannot invent evidence that wasn't actually collected, and cannot alter
completeness_ratio or confidence -- those stay owned by the deterministic
policy layer, which is the whole point (see ARCHITECTURE.md). If this call
fails for any reason -- no API key configured, network error, wrong model
name, rate limit -- the caller falls back to packet.rationale, which is
always present and always sufficient on its own.
"""
from __future__ import annotations

import os

import requests

from src.schemas import EvidencePacket

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 8


def draft_narrative(packet: EvidencePacket) -> str | None:
    if not GEMINI_API_KEY:
        return None

    present = [e.type for e in packet.collected_evidence if e.present]
    absent = [e.type for e in packet.collected_evidence if not e.present]

    prompt = (
        "You are drafting an internal case summary of a payment dispute for a "
        "merchant operations reviewer. Use ONLY the facts listed below -- do not "
        "invent evidence, dates, amounts, or outcomes that aren't listed here, and "
        "do not state or imply any recommendation other than the one given.\n\n"
        f"Dispute reason code: {packet.reason_code.value}\n"
        f"Evidence confirmed present: {present or 'none'}\n"
        f"Evidence confirmed absent: {absent or 'none'}\n"
        f"Evidence completeness: {packet.completeness_ratio:.0%}\n"
        f"Policy engine recommendation (fixed -- not yours to change): {packet.recommendation.value}\n"
        f"Policy rationale: {packet.rationale}\n\n"
        "Write 2-3 plain sentences summarizing the case and the recommendation for "
        "a human reviewer. No headers, no bullet points, no markdown."
    )

    try:
        resp = requests.post(
            GEMINI_URL.format(model=GEMINI_MODEL),
            params={"key": GEMINI_API_KEY},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None
