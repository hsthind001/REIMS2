"""
Repository layer for tenant-scoped data access.

Use these helpers instead of direct session.query() to enforce
organization isolation and prevent cross-tenant reads.
"""
from .tenant_scoped import (
    get_property_for_org,
    get_property_by_code_for_org,
    get_upload_for_org,
    get_upload_by_path_for_org,
    get_period_for_org,
    get_workflow_lock_for_org,
    get_reconciliation_session_for_org,
)
