from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.contracts import (
    ApiError,
    AttributionCandidate,
    ContractValidationResult,
    EvidenceRecord,
    NormalizedOutput,
    NormalizedTransaction,
    TransactionRelationship,
)

NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc)


def test_normalized_transaction_uses_integer_base_units_and_timezone():
    tx = NormalizedTransaction(
        network="bitcoin", txid="tx-1", timestamp=NOW, confirmed=True,
        inputs=[], outputs=[NormalizedOutput(index=0, address="bc1qexample", value_sats=123)],
        fee_sats=1, provider="test-fixture", fetched_at=NOW,
    )
    assert tx.outputs[0].value_sats == 123
    assert tx.timestamp.utcoffset().total_seconds() == 0


def test_confirmed_transaction_requires_timestamp():
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            network="bitcoin", txid="tx-1", confirmed=True, provider="fixture", fetched_at=NOW
        )


def test_transaction_output_indexes_must_be_unique():
    with pytest.raises(ValidationError):
        NormalizedTransaction(
            network="bitcoin", txid="tx-1", timestamp=NOW, confirmed=True,
            outputs=[NormalizedOutput(index=0, value_sats=1), NormalizedOutput(index=0, value_sats=2)],
            provider="fixture", fetched_at=NOW,
        )


def test_inferred_relationship_requires_method():
    with pytest.raises(ValidationError):
        TransactionRelationship(
            relationship_id="rel-1", network="bitcoin", relationship_type="heuristic_cluster",
            source_address="a", target_address="b", inferred=True,
        )


def test_observed_relationship_does_not_allow_inference_method():
    with pytest.raises(ValidationError):
        TransactionRelationship(
            relationship_id="rel-1", network="bitcoin", relationship_type="transaction_output",
            source_address="a", target_address="b", inferred=False, inference_method="common-input",
        )


def test_high_confidence_candidate_requires_evidence():
    with pytest.raises(ValidationError):
        AttributionCandidate(
            candidate_id="cand-1", entity_name="Example Exchange", entity_type="cex",
            network="bitcoin", confidence="High", evidence_ids=[],
        )


def test_evidence_timestamp_must_be_timezone_aware():
    with pytest.raises(ValidationError):
        EvidenceRecord(
            evidence_id="ev-1", evidence_type="direct_label", summary="Address label",
            source_name="test", collected_at=datetime(2026, 10, 28),
        )


def test_error_api_result_requires_error_payload():
    with pytest.raises(ValidationError):
        ContractValidationResult(status="error", request_id="req-1")


def test_valid_error_api_result():
    result = ContractValidationResult(
        status="error", request_id="req-1",
        error=ApiError(code="PROVIDER_UNAVAILABLE", message="Provider unavailable", retryable=True),
    )
    assert result.schema_version == "1.0"
    assert result.error.retryable is True
