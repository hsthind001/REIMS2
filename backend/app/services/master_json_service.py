"""
Master JSON service: create run_id, init/update/persist Master JSON for multi-LLM extraction.
"""
import uuid
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.extraction_run import ExtractionRun
from app.models.document_upload import DocumentUpload
from app.schemas.master_json import (
    MasterJSON,
    MasterJSONHeader,
    MasterJSONExtraction,
    MasterJSONCandidates,
    CandidateEntry,
    MasterJSONEvidence,
    EvidenceEntry,
    MasterJSONValidation,
    MasterJSONDecision,
    MasterJSONTelemetry,
    TelemetryEntry,
    ChallengeSuggestion,
    create_empty_master_json,
)

logger = logging.getLogger(__name__)


class MasterJSONService:
    """Create and persist Master JSON for each extraction run."""

    def __init__(self, db: Session):
        self.db = db

    def create_run(self, upload: DocumentUpload) -> tuple[str, ExtractionRun, MasterJSON]:
        """
        Create run_id, ExtractionRun row, and initial Master JSON.
        Returns (run_id, extraction_run, master_json).
        """
        run_id = str(uuid.uuid4())
        master = create_empty_master_json(
            run_id=run_id,
            document_upload_id=upload.id,
            doc_type=upload.document_type or "",
            period_id=upload.period_id,
            property_id=upload.property_id,
            file_hash=upload.file_hash,
            file_name=upload.file_name,
            config_snapshot={},
        )
        run_row = ExtractionRun(
            run_id=run_id,
            document_upload_id=upload.id,
            master_json=master.to_dict(),
        )
        self.db.add(run_row)
        self.db.flush()
        upload.extraction_run_id = run_row.id
        self.db.commit()
        self.db.refresh(run_row)
        logger.info("Created extraction run run_id=%s for upload_id=%s", run_id, upload.id)
        return run_id, run_row, master

    def get_run_by_run_id(self, run_id: str) -> Optional[ExtractionRun]:
        """Load ExtractionRun by run_id."""
        return self.db.query(ExtractionRun).filter(ExtractionRun.run_id == run_id).first()

    def get_run_by_upload_id(self, document_upload_id: int) -> Optional[ExtractionRun]:
        """Load ExtractionRun by document_upload_id (latest run for that upload)."""
        return (
            self.db.query(ExtractionRun)
            .filter(ExtractionRun.document_upload_id == document_upload_id)
            .order_by(ExtractionRun.created_at.desc())
            .first()
        )

    def load_master_json(self, run_row: ExtractionRun) -> MasterJSON:
        """Deserialize Master JSON from DB row."""
        data = run_row.master_json or {}
        return MasterJSON.from_dict(data)

    def persist_master_json(self, run_row: ExtractionRun, master: MasterJSON) -> None:
        """Update run row with current Master JSON and commit."""
        run_row.master_json = master.to_dict()
        self.db.commit()

    def update_extraction_section(
        self,
        run_row: ExtractionRun,
        text_preview: Optional[str] = None,
        total_pages: Optional[int] = None,
        engines_used: Optional[list] = None,
        primary_engine: Optional[str] = None,
        confidence_score: Optional[float] = None,
        quality_level: Optional[str] = None,
        processing_time_seconds: Optional[float] = None,
    ) -> None:
        """Update Master JSON extraction section and persist."""
        master = self.load_master_json(run_row)
        master.extraction = MasterJSONExtraction(
            text_preview=text_preview or master.extraction.text_preview,
            total_pages=total_pages if total_pages is not None else master.extraction.total_pages,
            engines_used=engines_used or master.extraction.engines_used,
            primary_engine=primary_engine or master.extraction.primary_engine,
            confidence_score=confidence_score if confidence_score is not None else master.extraction.confidence_score,
            quality_level=quality_level or master.extraction.quality_level,
            processing_time_seconds=processing_time_seconds if processing_time_seconds is not None else master.extraction.processing_time_seconds,
        )
        self.persist_master_json(run_row, master)

    def link_extraction_log(self, run_row: ExtractionRun, extraction_log_id: int) -> None:
        """Set extraction_log_id on run and commit."""
        run_row.extraction_log_id = extraction_log_id
        self.db.commit()

    def append_candidates_and_telemetry(
        self,
        run_row: ExtractionRun,
        candidate_results: List[Any],
        template_candidate: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Append LLM candidate results and optional template candidate to Master JSON;
        update telemetry entries. candidate_results are LLMCandidateResult instances.
        """
        master = self.load_master_json(run_row)
        entries = list(master.candidates.entries)
        telemetry_entries = list(master.telemetry.entries)
        total_latency = master.telemetry.total_latency_ms or 0.0

        if template_candidate:
            entries.append(
                CandidateEntry(
                    source="template",
                    model=None,
                    parsed_json=template_candidate,
                    raw_response_preview=None,
                    latency_ms=None,
                    tokens_estimate=None,
                    error=None,
                )
            )

        te_by_provider: Dict[str, TelemetryEntry] = {t.provider: t for t in telemetry_entries}
        for r in candidate_results:
            entries.append(
                CandidateEntry(
                    source=r.provider,
                    model=r.model,
                    parsed_json=r.parsed_json or {},
                    raw_response_preview=r.raw_response[:500] if r.raw_response else None,
                    latency_ms=r.latency_ms,
                    tokens_estimate=r.tokens_estimate,
                    error=r.error,
                )
            )
            if r.latency_ms is not None:
                total_latency += r.latency_ms
            if r.provider in te_by_provider:
                old = te_by_provider[r.provider]
                te_by_provider[r.provider] = TelemetryEntry(
                    provider=r.provider,
                    model=r.model or old.model,
                    call_count=old.call_count + 1,
                    tokens_estimate=(old.tokens_estimate or 0) + (r.tokens_estimate or 0),
                    latency_ms=(old.latency_ms or 0) + (r.latency_ms or 0),
                    error_count=old.error_count + (1 if r.error else 0),
                )
            else:
                te_by_provider[r.provider] = TelemetryEntry(
                    provider=r.provider,
                    model=r.model,
                    call_count=1,
                    tokens_estimate=r.tokens_estimate,
                    latency_ms=r.latency_ms,
                    error_count=1 if r.error else 0,
                )
        telemetry_entries = list(te_by_provider.values())

        master.candidates = MasterJSONCandidates(entries=entries)
        master.telemetry = MasterJSONTelemetry(entries=telemetry_entries, total_latency_ms=total_latency if total_latency else None)
        self.persist_master_json(run_row, master)

    def update_evidence_section(
        self,
        run_row: ExtractionRun,
        evidence_entries: List[EvidenceEntry],
        coverage_pct: Optional[float] = None,
    ) -> None:
        """Set Master JSON evidence section and persist."""
        master = self.load_master_json(run_row)
        master.evidence = MasterJSONEvidence(entries=evidence_entries, coverage_pct=coverage_pct)
        self.persist_master_json(run_row, master)

    def update_decision_section(
        self,
        run_row: ExtractionRun,
        overall_gate: str,
        field_decisions: List[Any],
        synthesis_rationale: Optional[str] = None,
        challenge_suggestions: Optional[List[Any]] = None,
    ) -> None:
        """Set Master JSON decision section (from deterministic scoring) and persist."""
        from app.schemas.master_json import MasterJSONDecision, FieldDecision
        master = self.load_master_json(run_row)
        fd = [FieldDecision(**d) if isinstance(d, dict) else d for d in field_decisions]
        cs = [ChallengeSuggestion(**s) if isinstance(s, dict) else s for s in (challenge_suggestions or [])]
        master.decision = MasterJSONDecision(
            overall_gate=overall_gate,
            field_decisions=fd,
            synthesis_rationale=synthesis_rationale,
            challenge_suggestions=cs,
        )
        self.persist_master_json(run_row, master)

    def append_challenge_suggestions(self, run_row: ExtractionRun, suggestions: List[Any]) -> None:
        """Append challenge suggestions to Master JSON decision section and persist."""
        master = self.load_master_json(run_row)
        existing = list(master.decision.challenge_suggestions)
        for s in suggestions:
            existing.append(ChallengeSuggestion(**s) if isinstance(s, dict) else s)
        master.decision.challenge_suggestions = existing
        self.persist_master_json(run_row, master)

    def update_validation_section(
        self,
        run_row: ExtractionRun,
        rule_pass_rate: Optional[float] = None,
        invariant_checks: Optional[List[Dict[str, Any]]] = None,
        fail_reasons: Optional[List[str]] = None,
        validation_results_ref: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set Master JSON validation section and persist."""
        from app.schemas.master_json import MasterJSONValidation
        master = self.load_master_json(run_row)
        master.validation = MasterJSONValidation(
            rule_pass_rate=rule_pass_rate or master.validation.rule_pass_rate,
            invariant_checks=invariant_checks or master.validation.invariant_checks,
            fail_reasons=fail_reasons or master.validation.fail_reasons,
            validation_results_ref=validation_results_ref or master.validation.validation_results_ref,
        )
        self.persist_master_json(run_row, master)
