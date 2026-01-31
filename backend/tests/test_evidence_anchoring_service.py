"""Unit tests for evidence anchoring service (page + snippet per field)."""
import pytest
from app.services.evidence_anchoring_service import (
    anchor_evidence,
    fields_from_candidate_parsed_json,
)


class TestEvidenceAnchoringService:
    def test_fields_from_candidate_parsed_json_line_items(self):
        parsed = {
            "line_items": [
                {"account_name": "Cash", "amount": 1000},
                {"account_name": "Receivables", "amount": 500},
            ],
            "total_assets": 1500,
        }
        fields = fields_from_candidate_parsed_json(parsed)
        assert len(fields) >= 2
        names = [f["field_name"] for f in fields]
        assert "Cash" in names
        assert "Receivables" in names
        assert any(f["field_name"] == "total_assets" for f in fields)

    def test_fields_from_candidate_parsed_json_units(self):
        parsed = {"units": [{"unit_id": "101", "monthly_rent": 1200}]}
        fields = fields_from_candidate_parsed_json(parsed)
        assert len(fields) == 1
        assert fields[0]["field_name"] == "101"
        assert fields[0]["value"] == 1200

    def test_anchor_evidence_finds_snippet(self):
        # Use text that contains the number in same format as normalized (no comma)
        full_text = "Some preamble. Total Assets 1234.56 more text."
        fields = [{"field_name": "total_assets", "value": 1234.56}]
        entries, coverage = anchor_evidence(full_text, fields, pages=None)
        assert len(entries) == 1
        assert entries[0].field_name == "total_assets"
        assert entries[0].snippet is not None
        assert "1234" in (entries[0].snippet or "")
        assert coverage == 1.0

    def test_anchor_evidence_no_match_still_creates_entry(self):
        full_text = "No numbers here."
        fields = [{"field_name": "total_assets", "value": 99999}]
        entries, coverage = anchor_evidence(full_text, fields, pages=None)
        assert len(entries) == 1
        assert entries[0].field_name == "total_assets"
        assert entries[0].snippet is None
        assert coverage == 0.0

    def test_anchor_evidence_empty_fields(self):
        entries, coverage = anchor_evidence("any text", [], pages=None)
        assert entries == []
        assert coverage == 1.0

    def test_anchor_evidence_finds_snippet_with_comma_formatted_text(self):
        # Text has "1,234.56"; value is 1234.56 (normalized to "1234.56")
        full_text = "Some preamble. Total Assets 1,234.56 more text."
        fields = [{"field_name": "total_assets", "value": 1234.56}]
        entries, coverage = anchor_evidence(full_text, fields, pages=None)
        assert len(entries) == 1
        assert entries[0].field_name == "total_assets"
        assert entries[0].snippet is not None
        assert "1,234.56" in (entries[0].snippet or "") or "1234" in (entries[0].snippet or "")
        assert coverage == 1.0
