"""Unit tests for deterministic scoring and gates (multi-LLM)."""
import pytest
from app.schemas.master_json import (
    MasterJSON,
    MasterJSONHeader,
    MasterJSONCandidates,
    CandidateEntry,
    MasterJSONEvidence,
    MasterJSONExtraction,
    create_empty_master_json,
)
from app.services.multi_llm_scoring import (
    run_invariant_checks,
    compute_confidence,
    compute_gate,
    score_and_route,
    AUTO_ACCEPT,
    ESCALATE_LLM,
    NEEDS_REVIEW,
    AUTO_RETRY,
)


class TestMultiLLMScoring:
    def test_invariant_balance_sheet_pass(self):
        parsed = {"total_assets": 100, "total_liabilities": 60, "total_equity": 40}
        passed, reasons = run_invariant_checks("balance_sheet", parsed)
        assert passed is True
        assert reasons == []

    def test_invariant_balance_sheet_fail(self):
        parsed = {"total_assets": 100, "total_liabilities": 60, "total_equity": 50}
        passed, reasons = run_invariant_checks("balance_sheet", parsed)
        assert passed is False
        assert len(reasons) > 0

    def test_invariant_other_doc_type_pass(self):
        passed, reasons = run_invariant_checks("income_statement", {})
        assert passed is True

    def test_compute_gate_auto_accept(self):
        gate = compute_gate(confidence=0.9, evidence_coverage=0.95, invariant_pass=True)
        assert gate == AUTO_ACCEPT

    def test_compute_gate_needs_review_invariant_fail(self):
        gate = compute_gate(confidence=0.9, evidence_coverage=0.95, invariant_pass=False)
        assert gate == NEEDS_REVIEW

    def test_compute_gate_needs_review_low_confidence(self):
        gate = compute_gate(confidence=0.5, evidence_coverage=0.95, invariant_pass=True)
        assert gate == NEEDS_REVIEW

    def test_compute_gate_escalate_llm(self):
        gate = compute_gate(confidence=0.7, evidence_coverage=0.8, invariant_pass=True)
        assert gate == ESCALATE_LLM

    def test_score_and_route_returns_decision(self):
        master = create_empty_master_json(run_id="r1", document_upload_id=1, doc_type="balance_sheet")
        master.extraction = MasterJSONExtraction(confidence_score=80.0)
        master.candidates.entries.append(
            CandidateEntry(source="template", parsed_json={"line_items": [{"account_name": "Cash", "amount": 100}], "total_assets": 100, "total_liabilities": 60, "total_equity": 40})
        )
        master.evidence.entries = []
        master.evidence.coverage_pct = 0.5
        confidence, overall_gate, decision = score_and_route(master, rule_pass_rate=1.0)
        assert 0 <= confidence <= 1
        assert decision.overall_gate in (AUTO_ACCEPT, ESCALATE_LLM, NEEDS_REVIEW, AUTO_RETRY)
        assert decision.synthesis_rationale is not None
