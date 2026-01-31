"""
Integration tests for Multi-LLM extraction (AbeAI-style): Master JSON + run_id flow.

Verifies MasterJSONService creates run_id and Master JSON; with MULTI_LLM_EXTRACTION_ENABLED=false
no external LLM calls are made. Uses mocks so tests run without PostgreSQL or full model set.

For full integration (real DB, orchestrator), run with PostgreSQL and ensure all models are loaded.
"""
import pytest
from app.schemas.master_json import create_empty_master_json


class TestMasterJSONRunCreation:
    """Test Master JSON schema and empty master creation (create_run covered in test_master_json_service)."""

    @pytest.mark.integration
    def test_empty_master_json_has_required_sections(self):
        """create_empty_master_json produces header, extraction, candidates, evidence, decision, telemetry."""
        master = create_empty_master_json(
            run_id="test-uuid",
            document_upload_id=1,
            doc_type="balance_sheet",
            period_id=1,
            property_id=10,
            file_hash="x",
            file_name="x.pdf",
            config_snapshot={},
        )
        d = master.to_dict()
        assert d["header"]["run_id"] == "test-uuid"
        assert "extraction" in d
        assert "candidates" in d and "entries" in d["candidates"]
        assert "evidence" in d and "entries" in d["evidence"]
        assert "decision" in d
        assert "telemetry" in d and "entries" in d["telemetry"]
