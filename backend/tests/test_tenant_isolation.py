"""
Tenant Isolation Tests (E2-S1)

Verifies that requests with non-member organization ID return 403.
Cross-tenant access must be blocked.
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

try:
    from app.main import app
    _APP_AVAILABLE = True
except ImportError:
    _APP_AVAILABLE = False
    app = None

pytestmark = pytest.mark.skipif(not _APP_AVAILABLE, reason="Full backend deps required")


class TestTenantIsolation:
    """Tenant isolation and org membership enforcement."""

    def test_get_current_organization_rejects_non_member_org(self):
        """get_current_organization returns 403 when user is not a member of requested org."""
        from app.api.dependencies import get_current_organization
        from app.models.user import User

        mock_user = User()
        mock_user.id = 1
        mock_user.is_superuser = False

        mock_request = MagicMock()
        mock_request.headers = {"x-organization-id": "999"}

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None  # Not a member of org 999
        mock_db.query.return_value = mock_query

        with pytest.raises(HTTPException) as exc_info:
            get_current_organization(
                request=mock_request,
                organization_id="999",
                current_user=mock_user,
                db=mock_db,
            )
        assert exc_info.value.status_code == 403
        assert "not a member" in exc_info.value.detail.lower()

    def test_unauthenticated_storage_returns_401(self):
        """Storage endpoints return 401 when accessed without credentials (E1-S2)."""
        client = TestClient(app)
        resp = client.get("/api/v1/storage/files")
        assert resp.status_code == 401

    def test_unauthenticated_properties_list_returns_401(self):
        """Properties list returns 401 when unauthenticated."""
        client = TestClient(app)
        resp = client.get("/api/v1/properties/", headers={"X-Organization-ID": "1"})
        assert resp.status_code == 401
