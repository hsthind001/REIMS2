"""Unit tests for MasterJSONService (multi-LLM run and Master JSON persistence)."""
import pytest
from unittest.mock import Mock, MagicMock
from app.services.master_json_service import MasterJSONService
from app.schemas.master_json import EvidenceEntry
from app.services.llm_adapters.base import LLMCandidateResult


class TestMasterJSONService:
    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.flush = Mock()
        db.refresh = Mock()
        db.query = Mock()
        return db

    @pytest.fixture
    def mock_upload(self):
        u = Mock()
        u.id = 1
        u.document_type = "balance_sheet"
        u.period_id = 1
        u.property_id = 10
        u.file_hash = "abc"
        u.file_name = "test.pdf"
        u.extraction_run_id = None
        return u

    @pytest.fixture
    def mock_run_row(self):
        r = Mock()
        r.id = 100
        r.run_id = "run-uuid-123"
        r.document_upload_id = 1
        r.extraction_log_id = None
        r.master_json = {
            "header": {"run_id": "run-uuid-123", "document_upload_id": 1},
            "candidates": {"entries": []},
            "evidence": {"entries": [], "coverage_pct": None},
            "telemetry": {"entries": [], "total_latency_ms": None},
        }
        r.created_at = None
        return r

    def test_load_master_json_deserializes(self, mock_db, mock_run_row):
        svc = MasterJSONService(mock_db)
        master = svc.load_master_json(mock_run_row)
        assert master.header.run_id == "run-uuid-123"
        assert master.header.document_upload_id == 1
        assert len(master.candidates.entries) == 0

    def test_update_evidence_section_persists(self, mock_db, mock_run_row):
        svc = MasterJSONService(mock_db)
        entries = [EvidenceEntry(field_name="Cash", page_index=0, snippet="Cash 100")]
        svc.update_evidence_section(mock_run_row, entries, coverage_pct=0.5)
        assert mock_run_row.master_json is not None
        assert mock_run_row.master_json.get("evidence", {}).get("coverage_pct") == 0.5
        assert len(mock_run_row.master_json.get("evidence", {}).get("entries", [])) == 1
        mock_db.commit.assert_called_once()

    def test_append_candidates_and_telemetry_adds_entries(self, mock_db, mock_run_row):
        svc = MasterJSONService(mock_db)
        results = [
            LLMCandidateResult(provider="anthropic", parsed_json={"line_items": []}, latency_ms=100.0),
            LLMCandidateResult(provider="openai", error="timeout", latency_ms=5000.0),
        ]
        svc.append_candidates_and_telemetry(mock_run_row, results, template_candidate={"line_items": []})
        mock_db.commit.assert_called()
        master = svc.load_master_json(mock_run_row)
        assert len(master.candidates.entries) == 3  # template + anthropic + openai
        assert any(e.source == "template" for e in master.candidates.entries)
        assert any(e.source == "anthropic" for e in master.candidates.entries)
        assert len(master.telemetry.entries) >= 2
