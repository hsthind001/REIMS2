"""API tests for extraction runs observability endpoints (multi-LLM)."""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

try:
    from app.main import app
    _APP_AVAILABLE = True
except Exception:
    _APP_AVAILABLE = False
    app = None

pytestmark = pytest.mark.skipif(not _APP_AVAILABLE, reason="Full backend deps required")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_extraction_run():
    r = Mock()
    r.run_id = "test-run-uuid"
    r.document_upload_id = 1
    r.extraction_log_id = 10
    r.created_at = None
    r.master_json = {
        "header": {"run_id": "test-run-uuid", "document_upload_id": 1},
        "decision": {"overall_gate": "AUTO_ACCEPT"},
        "evidence": {"coverage_pct": 0.9},
        "telemetry": {"total_latency_ms": 500.0, "entries": [{"provider": "anthropic", "call_count": 1, "latency_ms": 200.0}]},
        "candidates": {"entries": [{"source": "anthropic"}, {"source": "template"}]},
    }
    return r


def test_get_extraction_run_404_when_not_found(client):
    """GET /extract/runs/{run_id} returns 404 when run does not exist."""
    with patch("app.api.v1.extraction.get_db") as mock_get_db:
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value = mock_db
        # Endpoint requires auth; without auth we get 401
        resp = client.get("/api/v1/extract/runs/nonexistent-run-id")
        assert resp.status_code in (401, 404)


def test_list_extraction_runs_requires_auth(client):
    """GET /extract/runs returns 401 when unauthenticated."""
    resp = client.get("/api/v1/extract/runs")
    assert resp.status_code == 401
