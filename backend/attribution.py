"""Evidence-backed, label-first VASP attribution for NOVACORE Day 3.

This module intentionally does not infer ownership from transaction patterns.
It converts an existing address-label record into a transparent attribution
candidate and evidence record. Heuristic attribution can be added separately
with lower confidence and explicit evidence.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from backend.contracts import AttributionCandidate, EvidenceRecord


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def attribute_labeled_address(
    address: str,
    labels: Mapping[str, Mapping[str, Any]],
    network: str = "bitcoin",
) -> tuple[AttributionCandidate, EvidenceRecord] | None:
    """Return a candidate plus evidence when `address` has a usable label.

    Expected label keys match backend/btc/labels.py:
    entity, type, source, verified.
    Returns None when no usable label exists. A verified label is marked High;
    an unverified label is marked Medium. These levels describe label evidence,
    not proof of legal ownership or control of the address.
    """
    address = address.strip()
    if not address:
        return None

    label = labels.get(address)
    if not label:
        return None

    entity_name = str(label.get("entity", "")).strip()
    entity_type = str(label.get("type", "")).strip()
    source_name = str(label.get("source", "")).strip() or "Unspecified label source"
    verified_value = label.get("verified", False)
    verified = (
        verified_value is True
        or str(verified_value).strip().lower() in {"1", "true", "yes"}
    )

    if not entity_name or not entity_type:
        return None

    evidence_id = _stable_id("ev", f"{network}:{address}:{entity_name}:{source_name}")
    candidate_id = _stable_id("cand", f"{network}:{address}:{entity_name}")

    evidence = EvidenceRecord(
        evidence_id=evidence_id,
        evidence_type="direct_label",
        summary=(
            f"Address label associates {address} with {entity_name} "
            f"(label type: {entity_type}; verified source: {verified})."
        ),
        source_name=source_name,
        collected_at=__import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ),
        related_addresses=[address],
    )

    candidate = AttributionCandidate(
        candidate_id=candidate_id,
        entity_name=entity_name,
        entity_type=entity_type,
        network=network,
        confidence="High" if verified else "Medium",
        evidence_ids=[evidence_id],
        status="corroborated" if verified else "candidate",
        explanation=(
            "Matched an existing address label from a source marked verified."
            if verified
            else "Matched an existing address label, but the source is not marked verified."
        ),
    )
    return candidate, evidence
