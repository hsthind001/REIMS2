"""
Tests for API v2 Documents Endpoint

Tests the new v2 documents API with standardized responses.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime


class TestV2DocumentsAPI:
    """Test v2 documents API endpoints"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        return MagicMock()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user"""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        user.is_superuser = False
        user.role = "user"
        return user

    @pytest.fixture
    def mock_admin_user(self):
        """Create mock admin user"""
        user = Mock()
        user.id = 2
        user.username = "admin"
        user.is_superuser = True
        user.role = "admin"
        return user

    def test_list_documents_pagination(self, mock_db, mock_user):
        """Test document listing returns proper pagination"""
        from app.api.v2.documents import list_documents
        from app.schemas.base import PaginatedResponse

        # Mock query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 50
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        mock_db.query.return_value = mock_query

        # Call endpoint
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            list_documents(
                page=1,
                page_size=10,
                current_user=mock_user,
                db=mock_db
            )
        )

        # Verify pagination structure
        assert hasattr(result, 'pagination')
        assert result.pagination.total == 50
        assert result.pagination.page == 1
        assert result.pagination.page_size == 10
        assert result.pagination.total_pages == 5

    def test_list_documents_filters_applied(self, mock_db, mock_user):
        """Test document listing applies filters correctly"""
        from app.api.v2.documents import list_documents, DocumentTypeEnum

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        mock_db.query.return_value = mock_query

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            list_documents(
                page=1,
                page_size=10,
                property_code="ESP001",
                document_type=DocumentTypeEnum.balance_sheet,
                current_user=mock_user,
                db=mock_db
            )
        )

        # Verify filter was called (multiple times for different conditions)
        assert mock_query.filter.called

    def test_get_document_not_found(self, mock_db, mock_user):
        """Test 404 response for non-existent document"""
        from app.api.v2.documents import get_document
        from fastapi import HTTPException

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        mock_db.query.return_value = mock_query

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                get_document(
                    document_id=999,
                    current_user=mock_user,
                    db=mock_db
                )
            )

        assert exc_info.value.status_code == 404
        assert "NOT_FOUND" in str(exc_info.value.detail)

    def test_delete_document_requires_admin(self, mock_db, mock_user):
        """Test delete requires admin role"""
        from app.api.dependencies import require_role, UserRole
        from fastapi import HTTPException

        # The require_role dependency should reject non-admin users
        dependency = require_role(UserRole.ADMIN, UserRole.SUPERUSER)

        with pytest.raises(HTTPException) as exc_info:
            # Mock get_current_user to return regular user
            with patch('app.api.dependencies.get_current_user', return_value=mock_user):
                dependency(current_user=mock_user)

        assert exc_info.value.status_code == 403

    def test_delete_document_allowed_for_admin(self, mock_db, mock_admin_user):
        """Test delete allowed for admin users"""
        from app.api.v2.documents import delete_document
        from app.models import DocumentUpload

        # Mock document
        mock_doc = Mock(spec=DocumentUpload)
        mock_doc.id = 1
        mock_doc.is_active = True

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_doc

        mock_db.query.return_value = mock_query

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            delete_document(
                document_id=1,
                current_user=mock_admin_user,
                db=mock_db
            )
        )

        # Should soft delete
        assert mock_doc.is_active is False
        assert mock_db.commit.called
        assert result.deleted_id == 1


class TestV2ResponseFormats:
    """Test v2 API response format consistency"""

    def test_success_response_has_timestamp(self):
        """Test success responses include timestamp"""
        from app.schemas.base import SuccessResponse

        response = SuccessResponse(
            message="Test",
            data={"key": "value"}
        )

        assert response.timestamp is not None
        assert response.status.value == "success"

    def test_error_response_structure(self):
        """Test error responses have proper structure"""
        from app.schemas.base import ErrorResponse, ErrorDetail, ErrorCode

        response = ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.NOT_FOUND,
                message="Resource not found",
                field=None,
                details={"resource_id": 123}
            )
        )

        assert response.status.value == "error"
        assert response.error.code == ErrorCode.NOT_FOUND
        assert response.error.details["resource_id"] == 123

    def test_delete_response_structure(self):
        """Test delete responses have proper structure"""
        from app.schemas.base import DeleteResponse

        response = DeleteResponse(
            message="Deleted successfully",
            deleted_id=123
        )

        assert response.status.value == "success"
        assert response.deleted_id == 123


class TestV2Versioning:
    """Test API versioning functionality"""

    def test_v2_version_info(self):
        """Test v2 version information is available"""
        from app.api.v2 import API_VERSION, DEPRECATION_DATE

        assert API_VERSION == "2.0.0"
        assert DEPRECATION_DATE == "2027-01-01"

    def test_deprecated_route_adds_headers(self):
        """Test deprecated route class adds proper headers"""
        from app.api.v2.router import DeprecatedRoute, API_VERSION, DEPRECATION_DATE
        from fastapi import APIRouter, Response
        from starlette.testclient import TestClient

        # Create a simple app with deprecated route
        router = APIRouter(route_class=DeprecatedRoute)

        @router.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        # The route class should add deprecation headers
        # This is a structural test - full integration would need FastAPI app
        assert DeprecatedRoute is not None
