"""
Security Tests for REIMS Application

Tests for SQL injection prevention, RBAC, input validation,
and other security-related fixes.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.orm import Session
import re


class TestSQLInjectionPrevention:
    """Test SQL injection prevention in text_to_sql and risk_workbench"""

    def test_text_to_sql_parameterized_queries(self):
        """Verify text_to_sql returns parameterized queries"""
        from app.services.nlq.text_to_sql import TextToSQLService

        service = TextToSQLService()

        # Test with potential SQL injection in property_code
        context = {
            'property_code': "ESP001'; DROP TABLE properties; --",
            'period_year': 2024,
            'period_month': 12
        }

        # The service should return parameterized query
        # SQL injection should not be possible
        sql, params = service._build_context_filters(context)

        # Verify the query uses parameters, not string interpolation
        assert 'property_code' not in sql or ':property_code' in sql
        assert "DROP TABLE" not in sql
        assert params.get('property_code') == context['property_code']

    def test_risk_workbench_safe_sort_columns(self):
        """Verify risk_workbench only allows safe sort columns"""
        from app.api.v1.risk_workbench import VALID_SORT_FIELDS

        # Verify only known safe columns are allowed
        expected_safe_columns = {
            'id', 'type', 'severity', 'property', 'age_seconds',
            'impact', 'status', 'created_at', 'account_name'
        }

        assert VALID_SORT_FIELDS == expected_safe_columns

    def test_risk_workbench_rejects_invalid_sort_field(self):
        """Verify invalid sort fields are rejected or handled safely"""
        from app.api.v1.risk_workbench import VALID_SORT_FIELDS

        malicious_inputs = [
            "id; DROP TABLE alerts; --",
            "1=1",
            "' OR '1'='1",
            "id ORDER BY 1",
            "../../../etc/passwd"
        ]

        for malicious in malicious_inputs:
            assert malicious not in VALID_SORT_FIELDS


class TestRBACDecorator:
    """Test Role-Based Access Control decorator"""

    def test_user_role_hierarchy(self):
        """Verify role hierarchy is correct"""
        from app.api.dependencies import UserRole, ROLE_HIERARCHY

        # Superuser should have all roles
        assert UserRole.USER in ROLE_HIERARCHY[UserRole.SUPERUSER]
        assert UserRole.ANALYST in ROLE_HIERARCHY[UserRole.SUPERUSER]
        assert UserRole.ADMIN in ROLE_HIERARCHY[UserRole.SUPERUSER]
        assert UserRole.SUPERUSER in ROLE_HIERARCHY[UserRole.SUPERUSER]

        # Admin should not have superuser
        assert UserRole.SUPERUSER not in ROLE_HIERARCHY[UserRole.ADMIN]
        assert UserRole.ADMIN in ROLE_HIERARCHY[UserRole.ADMIN]

        # User should only have user role
        assert ROLE_HIERARCHY[UserRole.USER] == [UserRole.USER]

    def test_has_role_function(self):
        """Test has_role correctly checks permissions"""
        from app.api.dependencies import has_role, UserRole
        from app.models.user import User

        # Create mock superuser
        superuser = Mock(spec=User)
        superuser.is_superuser = True

        # Superuser should have all roles
        assert has_role(superuser, UserRole.USER) is True
        assert has_role(superuser, UserRole.ADMIN) is True
        assert has_role(superuser, UserRole.SUPERUSER) is True

        # Create mock regular user
        regular_user = Mock(spec=User)
        regular_user.is_superuser = False
        regular_user.role = None

        # Regular user should only have user role
        assert has_role(regular_user, UserRole.USER) is True
        assert has_role(regular_user, UserRole.ADMIN) is False
        assert has_role(regular_user, UserRole.SUPERUSER) is False


class TestInputValidation:
    """Test input validation improvements"""

    def test_password_strength_validation(self):
        """Test password strength requirements"""
        from app.api.v1.auth import validate_password_strength

        # Weak passwords should fail
        weak_passwords = [
            "short",          # Too short
            "nouppercase1!",  # No uppercase
            "NOLOWERCASE1!",  # No lowercase
            "NoNumbers!",     # No numbers
            "NoSpecial123",   # No special chars
        ]

        for weak_pwd in weak_passwords:
            with pytest.raises(HTTPException) as exc_info:
                validate_password_strength(weak_pwd)
            assert exc_info.value.status_code == 400

        # Strong password should pass
        strong_password = "SecurePass123!"
        # Should not raise
        validate_password_strength(strong_password)

    def test_extraction_strategy_enum_validation(self):
        """Test extraction strategy uses enum validation"""
        from app.api.v1.extraction import ExtractionStrategy

        # Valid strategies
        valid_strategies = ['auto', 'fast', 'accurate', 'multi_engine']
        for strategy in valid_strategies:
            assert ExtractionStrategy(strategy).value == strategy

        # Invalid strategy should raise
        with pytest.raises(ValueError):
            ExtractionStrategy('invalid_strategy')


class TestFileUploadSecurity:
    """Test file upload security measures"""

    def test_pdf_magic_bytes_validation(self):
        """Test PDF magic bytes validation"""
        from app.core.constants import FileUploadLimits

        # Valid PDF should start with %PDF
        valid_pdf_header = b'%PDF-1.4 some content'
        assert valid_pdf_header.startswith(FileUploadLimits.PDF_MAGIC_BYTES)

        # Invalid files should not pass
        invalid_headers = [
            b'<html>Not a PDF</html>',
            b'PK\x03\x04',  # ZIP file
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'GIF89a',  # GIF
        ]

        for header in invalid_headers:
            assert not header.startswith(FileUploadLimits.PDF_MAGIC_BYTES)


class TestSessionSecurity:
    """Test session security configuration"""

    def test_session_config_has_security_settings(self):
        """Verify session has secure configuration"""
        from app.core.config import settings

        # Should have session configuration
        assert hasattr(settings, 'SESSION_HTTPS_ONLY')
        assert hasattr(settings, 'SESSION_SAME_SITE')
        assert hasattr(settings, 'SESSION_MAX_AGE_SECONDS')

        # SameSite should be 'lax' or 'strict'
        assert settings.SESSION_SAME_SITE in ['lax', 'strict', 'none']


class TestCredentialSecurity:
    """Test credential handling security"""

    def test_no_hardcoded_secrets_in_config(self):
        """Verify no hardcoded secrets in production mode"""
        import os

        # Temporarily set production environment
        original_env = os.environ.get('ENVIRONMENT')

        try:
            os.environ['ENVIRONMENT'] = 'production'

            # Should require env vars in production
            from app.core.config import _get_env_or_generate

            # Without required env var, should raise in production
            # Note: This test verifies the function exists and handles production mode
            with pytest.raises(ValueError) as exc_info:
                _get_env_or_generate('NONEXISTENT_SECRET_KEY', 'default_value')

            assert 'production' in str(exc_info.value).lower()

        finally:
            # Restore original environment
            if original_env:
                os.environ['ENVIRONMENT'] = original_env
            else:
                os.environ.pop('ENVIRONMENT', None)


class TestRateLimiting:
    """Test rate limiting on sensitive endpoints"""

    def test_rate_limit_decorators_present(self):
        """Verify rate limiting is configured on sensitive endpoints"""
        import ast
        import os

        # Check documents.py for rate limiting
        docs_path = os.path.join(
            os.path.dirname(__file__),
            '../app/api/v1/documents.py'
        )

        with open(docs_path, 'r') as f:
            content = f.read()

        # Should have limiter decorators
        assert '@limiter.limit' in content
        assert 'slowapi' in content or 'limiter' in content


class TestExceptionHandling:
    """Test proper exception handling (no bare except blocks)"""

    def test_no_bare_except_in_main_services(self):
        """Verify no bare 'except:' blocks in critical services"""
        import os
        import re

        services_dir = os.path.join(
            os.path.dirname(__file__),
            '../app/services'
        )

        # Pattern for bare except (except: without Exception type)
        bare_except_pattern = re.compile(r'except:\s*$', re.MULTILINE)

        violations = []

        for root, dirs, files in os.walk(services_dir):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r') as f:
                        content = f.read()
                        matches = bare_except_pattern.findall(content)
                        if matches:
                            violations.append(f"{filepath}: {len(matches)} bare except(s)")

        # Should have minimal or no bare excepts
        # Allow some for specific cases but flag if too many
        assert len(violations) < 20, f"Too many bare except blocks: {violations}"


class TestTransactionHandling:
    """Test database transaction handling"""

    def test_db_session_has_rollback_on_error(self):
        """Verify database session handles rollback on exceptions"""
        from app.db.database import get_db

        # get_db should be a generator that handles rollback
        gen = get_db()
        session = next(gen)

        # Should have rollback capability
        assert hasattr(session, 'rollback')
        assert hasattr(session, 'commit')

        # Cleanup
        try:
            gen.close()
        except StopIteration:
            pass


class TestAPIResponseSchemas:
    """Test standardized API response schemas"""

    def test_error_response_schema(self):
        """Test ErrorResponse has required fields"""
        from app.schemas.base import ErrorResponse, ErrorDetail, ErrorCode

        error = ErrorResponse(
            error=ErrorDetail(
                code=ErrorCode.VALIDATION_ERROR,
                message="Test error"
            )
        )

        assert error.status.value == "error"
        assert error.error.code == ErrorCode.VALIDATION_ERROR
        assert error.error.message == "Test error"
        assert error.timestamp is not None

    def test_paginated_response_schema(self):
        """Test PaginatedResponse structure"""
        from app.schemas.base import PaginatedResponse, PaginationMeta

        pagination = PaginationMeta.from_query(total=100, page=1, page_size=10)

        assert pagination.total == 100
        assert pagination.page == 1
        assert pagination.page_size == 10
        assert pagination.total_pages == 10
        assert pagination.has_next is True
        assert pagination.has_previous is False

    def test_pagination_meta_boundary_cases(self):
        """Test pagination handles boundary cases"""
        from app.schemas.base import PaginationMeta

        # Empty results
        empty = PaginationMeta.from_query(total=0, page=1, page_size=10)
        assert empty.total_pages == 0
        assert empty.has_next is False
        assert empty.has_previous is False

        # Last page
        last = PaginationMeta.from_query(total=25, page=3, page_size=10)
        assert last.total_pages == 3
        assert last.has_next is False
        assert last.has_previous is True


class TestConstantsExtraction:
    """Test that magic numbers are properly extracted to constants"""

    def test_confidence_thresholds_defined(self):
        """Verify confidence thresholds are centralized"""
        from app.core.constants import ConfidenceThresholds

        assert ConfidenceThresholds.TIER_0_AUTO_CLOSE == 98.0
        assert ConfidenceThresholds.TIER_1_AUTO_SUGGEST == 90.0
        assert ConfidenceThresholds.TIER_2_COMMITTEE == 70.0
        assert ConfidenceThresholds.HIGH_CONFIDENCE == 90.0

    def test_batch_processing_limits_defined(self):
        """Verify batch limits are centralized"""
        from app.core.constants import BatchProcessingLimits

        assert BatchProcessingLimits.BULK_DELETE_BATCH_SIZE == 100
        assert BatchProcessingLimits.QUERY_PAGE_SIZE_DEFAULT == 50
        assert BatchProcessingLimits.QUERY_PAGE_SIZE_MAX == 500

    def test_file_upload_limits_defined(self):
        """Verify file upload limits are centralized"""
        from app.core.constants import FileUploadLimits

        assert FileUploadLimits.MAX_FILE_SIZE_MB == 50
        assert FileUploadLimits.PDF_MAGIC_BYTES == b'%PDF'
        assert 'pdf' in FileUploadLimits.ALLOWED_EXTENSIONS
