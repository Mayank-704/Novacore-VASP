"""Versioned, chain-neutral data contracts for NOVACORE.

These models define the boundary between provider adapters, graph analysis,
attribution, and API/reporting layers.
"""

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

Network = str

EvidenceType = Literal[
    "direct_label",
    "documented_ownership",
    "corroborating_transaction",
    "heuristic_cluster",
    "deposit_pattern",
    "cross_chain_link",
]

RelationshipType = Literal[
    "transaction_input",
    "transaction_output",
    "documented_ownership",
    "heuristic_cluster",
    "possible_deposit",
    "cross_chain_event",
]

ConfidenceLevel = Literal["High", "Medium", "Low", "Unassessed"]
AttributionStatus = Literal[
    "candidate",
    "corroborated",
    "unresolved",
    "rejected",
]


class ContractModel(BaseModel):
    """Base class that rejects undeclared fields."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class NormalizedInput(ContractModel):
    address: str | None = None
    value_sats: int | None = Field(default=None, ge=0)
    script_type: str | None = None
    previous_txid: str | None = None
    previous_vout: int | None = Field(default=None, ge=0)
    is_coinbase: bool = False


class NormalizedOutput(ContractModel):
    index: int = Field(ge=0)
    address: str | None = None
    value_sats: int = Field(ge=0)
    script_type: str | None = None


class NormalizedTransaction(ContractModel):
    """Canonical transaction observation using integer base units."""

    network: str = Field(min_length=1, max_length=40)
    txid: str = Field(min_length=1, max_length=160)
    timestamp: datetime | None = None
    confirmed: bool
    block_height: int | None = Field(default=None, ge=0)
    inputs: list[NormalizedInput] = Field(default_factory=list)
    outputs: list[NormalizedOutput] = Field(default_factory=list)
    fee_sats: int | None = Field(default=None, ge=0)
    provider: str = Field(min_length=1, max_length=100)
    fetched_at: datetime
    raw_reference: str | None = None

    @field_validator("timestamp", "fetched_at")
    @classmethod
    def require_timezone_for_datetimes(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Datetime values must include a timezone")
        return value

    @model_validator(mode="after")
    def check_confirmation_consistency(self):
        if self.confirmed and self.timestamp is None:
            raise ValueError("Confirmed transactions must have a timestamp")

        indexes = [output.index for output in self.outputs]
        if len(indexes) != len(set(indexes)):
            raise ValueError(
                "Output indexes must be unique within a transaction"
            )

        return self


class TransactionRelationship(ContractModel):
    """A relationship with its evidential basis made explicit."""

    relationship_id: str = Field(min_length=1, max_length=200)
    network: str = Field(min_length=1, max_length=40)
    relationship_type: RelationshipType
    source_address: str | None = None
    target_address: str | None = None
    txid: str | None = None
    observed_at: datetime | None = None
    inferred: bool = False
    inference_method: str | None = None

    @field_validator("observed_at")
    @classmethod
    def require_timezone_for_observed_at(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Datetime values must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_inference_fields(self):
        if self.inferred and not self.inference_method:
            raise ValueError(
                "Inferred relationships require an inference method"
            )

        if not self.inferred and self.inference_method is not None:
            raise ValueError(
                "Observed relationships cannot specify an inference method"
            )

        return self


class EvidenceRecord(ContractModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    evidence_type: EvidenceType
    summary: str = Field(min_length=1, max_length=2000)
    source_name: str = Field(min_length=1, max_length=200)
    collected_at: datetime
    source_url: str | None = None
    related_addresses: list[str] = Field(default_factory=list)
    related_txids: list[str] = Field(default_factory=list)

    @field_validator("collected_at")
    @classmethod
    def require_timezone_for_collected_at(
        cls, value: datetime
    ) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime values must include a timezone")
        return value


class AttributionCandidate(ContractModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    entity_name: str = Field(min_length=1, max_length=300)
    entity_type: str = Field(min_length=1, max_length=100)
    network: str = Field(min_length=1, max_length=40)
    confidence: ConfidenceLevel
    evidence_ids: list[str] = Field(default_factory=list)
    status: AttributionStatus = "candidate"
    explanation: str | None = None

    @model_validator(mode="after")
    def high_confidence_requires_evidence(self):
        if self.confidence == "High" and not self.evidence_ids:
            raise ValueError(
                "High-confidence candidates require evidence"
            )
        return self


class ApiError(ContractModel):
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)
    retryable: bool = False
    details: dict[str, str] = Field(default_factory=dict)


class ContractValidationResult(ContractModel):
    schema_version: str = "1.0"
    status: Literal["success", "error"]
    request_id: str = Field(min_length=1, max_length=200)
    error: ApiError | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_result_payload(self):
        if self.status == "error" and self.error is None:
            raise ValueError("Error results require an error payload")

        if self.status == "success" and self.error is not None:
            raise ValueError("Success results cannot contain an error payload")

        return self
    