"""
Storage Authentication Tests (E1-S2)

Verifies that storage endpoints require authentication and return 401
when accessed without valid credentials.

Requires full backend environment (celery, email_validator, etc).
Run with: cd backend && pip install -r requirements.txt && pytest tests/test_storage_auth.py
"""
import pytest

try:
    from fastapi.testclient import TestClient
    from app.main import app
    _APP_AVAILABLE = True
except ImportError:
    _APP_AVAILABLE = False
    TestClient = None
    app = None

pytestmark = pytest.mark.skipif(not _APP_AVAILABLE, reason="Full backend deps required")


@pytest.fixture
def client():
    """Test client without auth overrides."""
    return TestClient(app)


class TestStorageRequiresAuth:
    """Storage endpoints must return 401 when unauthenticated."""

    def test_unauthenticated_storage_upload_returns_401(self, client: TestClient):
        """POST /api/v1/storage/upload without auth returns 401."""
        response = client.post(
            "/api/v1/storage/upload",
            files={"file": ("test.txt", b"test content", "text/plain")},
        )
        assert response.status_code == 401

    def test_unauthenticated_storage_download_returns_401(self, client: TestClient):
        """GET /api/v1/storage/download/{filename} without auth returns 401."""
        response = client.get("/api/v1/storage/download/some-file.pdf")
        assert response.status_code == 401

    def test_unauthenticated_storage_list_returns_401(self, client: TestClient):
        """GET /api/v1/storage/files without auth returns 401."""
        response = client.get("/api/v1/storage/files")
        assert response.status_code == 401

    def test_unauthenticated_storage_info_returns_401(self, client: TestClient):
        """GET /api/v1/storage/info/{filename} without auth returns 401."""
        response = client.get("/api/v1/storage/info/some-file.pdf")
        assert response.status_code == 401

    def test_unauthenticated_storage_url_returns_401(self, client: TestClient):
        """GET /api/v1/storage/url/{filename} without auth returns 401."""
        response = client.get("/api/v1/storage/url/some-file.pdf")
        assert response.status_code == 401

    def test_unauthenticated_storage_delete_returns_401(self, client: TestClient):
        """DELETE /api/v1/storage/{filename} without auth returns 401."""
        response = client.delete("/api/v1/storage/some-file.pdf")
        assert response.status_code == 401


class TestStorageHealthPublic:
    """Storage health endpoint remains public for monitoring."""

    def test_storage_health_accessible_without_auth(self, client: TestClient):
        """GET /api/v1/storage/health is public (no auth required)."""
        response = client.get("/api/v1/storage/health")
        # May be 200 with status or 500 if MinIO unavailable; should NOT be 401
        assert response.status_code != 401
