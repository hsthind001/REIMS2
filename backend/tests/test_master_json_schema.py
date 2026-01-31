"""Unit tests for Master JSON schema (multi-LLM chain-of-custody)."""
import pytest
from app.schemas.master_json import (
    MasterJSON,
    MasterJSONHeader,
    MasterJSONCandidates,
    CandidateEntry,
    MasterJSONEvidence,
    EvidenceEntry,
    MasterJSONDecision,
    FieldDecision,
    create_empty_master_json,
)


class TestMasterJSONSchema:
    def test_create_empty_master_json(self):
        master = create_empty_master_json(
            run_id="test-uuid-123",
            document_upload_id=42,
            doc_type="balance_sheet",
            period_id=1,
            property_id=10,
            file_hash="abc",
            file_name="test.pdf",
        )
        assert master.header.run_id == "test-uuid-123"
        assert master.header.document_upload_id == 42
        assert master.header.doc_type == "balance_sheet"
        assert master.header.schema_version == "1.0"
        assert master.candidates.entries == []
        assert master.evidence.entries == []
        assert master.decision.overall_gate is None

    def test_master_json_to_dict_roundtrip(self):
        master = create_empty_master_json(run_id="r1", document_upload_id=1)
        master.candidates.entries.append(
            CandidateEntry(source="template", parsed_json={"line_items": []})
        )
        d = master.to_dict()
        assert "header" in d
        assert d["header"]["run_id"] == "r1"
        assert len(d["candidates"]["entries"]) == 1
        restored = MasterJSON.from_dict(d)
        assert restored.header.run_id == master.header.run_id
        assert len(restored.candidates.entries) == 1
        assert restored.candidates.entries[0].source == "template"

    def test_evidence_entry(self):
        e = EvidenceEntry(field_name="total_assets", page_index=0, snippet="Total Assets $100")
        assert e.field_name == "total_assets"
        assert e.page_index == 0
        assert e.snippet == "Total Assets $100"
        assert e.bbox is None

    def test_field_decision(self):
        fd = FieldDecision(
            field_name="Cash",
            chosen_value=1000.0,
            confidence=0.9,
            gate_outcome="AUTO_ACCEPT",
            rationale="concordance",
        )
        assert fd.field_name == "Cash"
        assert fd.chosen_value == 1000.0
        assert fd.gate_outcome == "AUTO_ACCEPT"
