"""
Master JSON schema for AbeAI-style multi-LLM extraction (chain-of-custody).
Sections: header, extraction, candidates, evidence, validation, decision, telemetry.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class MasterJSONHeader(BaseModel):
    """Run metadata and config snapshot."""
    run_id: str
    document_upload_id: int
    doc_type: str = ""
    period_id: Optional[int] = None
    property_id: Optional[int] = None
    file_hash: Optional[str] = None
    file_name: Optional[str] = None
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[str] = None
    schema_version: str = "1.0"


class MasterJSONExtraction(BaseModel):
    """Chosen engine outputs and quality scores (from text extraction step)."""
    text_preview: Optional[str] = None
    total_pages: Optional[int] = None
    engines_used: List[str] = Field(default_factory=list)
    primary_engine: Optional[str] = None
    confidence_score: Optional[float] = None
    quality_level: Optional[str] = None
    processing_time_seconds: Optional[float] = None


class CandidateEntry(BaseModel):
    """Single candidate from one model or engine."""
    source: str  # e.g. "anthropic", "openai", "template"
    model: Optional[str] = None
    parsed_json: Dict[str, Any] = Field(default_factory=dict)
    raw_response_preview: Optional[str] = None
    latency_ms: Optional[float] = None
    tokens_estimate: Optional[int] = None
    error: Optional[str] = None


class MasterJSONCandidates(BaseModel):
    """Per-model candidate JSON outputs."""
    entries: List[CandidateEntry] = Field(default_factory=list)


class EvidenceEntry(BaseModel):
    """Evidence for one field: page + snippet, optional bbox."""
    field_name: str
    page_index: Optional[int] = None
    snippet: Optional[str] = None
    bbox: Optional[Dict[str, float]] = None


class MasterJSONEvidence(BaseModel):
    """Per-field evidence (page, snippet, optional bbox)."""
    entries: List[EvidenceEntry] = Field(default_factory=list)
    coverage_pct: Optional[float] = None


class MasterJSONValidation(BaseModel):
    """Rule results, invariant checks, fail reasons."""
    rule_pass_rate: Optional[float] = None
    invariant_checks: List[Dict[str, Any]] = Field(default_factory=list)
    fail_reasons: List[str] = Field(default_factory=list)
    validation_results_ref: Optional[Dict[str, Any]] = None


class FieldDecision(BaseModel):
    """Per-field chosen value and rationale."""
    field_name: str
    chosen_value: Any = None
    confidence: Optional[float] = None
    gate_outcome: Optional[str] = None  # AUTO_ACCEPT, ESCALATE_LLM, NEEDS_REVIEW
    rationale: Optional[str] = None


class ChallengeSuggestion(BaseModel):
    """Adversarial challenger suggestion for a low-confidence field."""
    field_name: str
    suspected_error_type: Optional[str] = None  # e.g. sign_swap, wrong_total
    suggested_correction: Any = None
    evidence_pointer: Optional[str] = None


class MasterJSONDecision(BaseModel):
    """Per-field final value, confidence, tie-break rationale."""
    overall_gate: Optional[str] = None  # AUTO_ACCEPT, AUTO_RETRY, ESCALATE_LLM, NEEDS_REVIEW
    field_decisions: List[FieldDecision] = Field(default_factory=list)
    synthesis_rationale: Optional[str] = None
    challenge_suggestions: List[ChallengeSuggestion] = Field(default_factory=list)


class TelemetryEntry(BaseModel):
    """Single model call telemetry."""
    provider: str
    model: Optional[str] = None
    call_count: int = 0
    tokens_estimate: Optional[int] = None
    latency_ms: Optional[float] = None
    error_count: int = 0


class MasterJSONTelemetry(BaseModel):
    """Per-run model calls, token estimates, latency, errors."""
    entries: List[TelemetryEntry] = Field(default_factory=list)
    total_latency_ms: Optional[float] = None


class MasterJSON(BaseModel):
    """Full Master JSON (all sections)."""
    header: MasterJSONHeader = Field(default_factory=MasterJSONHeader)
    extraction: MasterJSONExtraction = Field(default_factory=MasterJSONExtraction)
    candidates: MasterJSONCandidates = Field(default_factory=MasterJSONCandidates)
    evidence: MasterJSONEvidence = Field(default_factory=MasterJSONEvidence)
    validation: MasterJSONValidation = Field(default_factory=MasterJSONValidation)
    decision: MasterJSONDecision = Field(default_factory=MasterJSONDecision)
    telemetry: MasterJSONTelemetry = Field(default_factory=MasterJSONTelemetry)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSONB storage."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MasterJSON":
        """Deserialize from dict (e.g. from DB)."""
        return cls.model_validate(data)


def create_empty_master_json(
    run_id: str,
    document_upload_id: int,
    doc_type: str = "",
    period_id: Optional[int] = None,
    property_id: Optional[int] = None,
    file_hash: Optional[str] = None,
    file_name: Optional[str] = None,
    config_snapshot: Optional[Dict[str, Any]] = None,
) -> MasterJSON:
    """Create Master JSON with header only (for run start)."""
    return MasterJSON(
        header=MasterJSONHeader(
            run_id=run_id,
            document_upload_id=document_upload_id,
            doc_type=doc_type,
            period_id=period_id,
            property_id=property_id,
            file_hash=file_hash,
            file_name=file_name,
            config_snapshot=config_snapshot or {},
            started_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            schema_version="1.0",
        ),
    )
