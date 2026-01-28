# Import Error Fix - AlertType Missing

**Date**: January 28, 2026 09:09 AM  
**Issue**: ReconciliationRuleEngine failing to import `AlertType`, `AlertSeverity`, `AlertStatus`, `CommitteeType`

---

## Root Cause

The logs showed:
```
ERROR: Failed to execute ReconciliationRuleEngine: cannot import name 'AlertType' from 'app.models'
ImportError: cannot import name 'AlertType' from 'app.models' (/app/app/models/__init__.py)
```

**Problem**: The `audit_rules_mixin.py` imports these enums from `app.models`:
```python
from app.models import (
    CommitteeAlert,
    AlertType,        # ❌ NOT exported from __init__.py
    AlertSeverity,    # ❌ NOT exported from __init__.py
    AlertStatus,      # ❌ NOT exported from __init__.py
    CommitteeType,    # ❌ NOT exported from __init__.py
    SystemConfig,
)
```

But `app/models/__init__.py` only exported `CommitteeAlert`, not the enums.

---

## Fix Applied

### File: `backend/app/models/__init__.py`

**Change 1 - Import the enums**:
```python
# OLD
from app.models.committee_alert import CommitteeAlert

# NEW
from app.models.committee_alert import (
    CommitteeAlert,
    AlertType,
    AlertSeverity,
    AlertStatus,
    CommitteeType
)
```

**Change 2 - Export the enums in __all__**:
```python
# OLD
__all__ = [
    ...
    "CommitteeAlert",
    "WorkflowLock",
    ...
]

# NEW
__all__ = [
    ...
    "CommitteeAlert",
    "AlertType",       # ✅ ADDED
    "AlertSeverity",   # ✅ ADDED
    "AlertStatus",     # ✅ ADDED
    "CommitteeType",   # ✅ ADDED
    "WorkflowLock",
    ...
]
```

---

## Expected Result

After backend restart:
- ✅ ReconciliationRuleEngine imports successfully
- ✅ All 311 rules execute
- ✅ Rules saved to `cross_document_reconciliations` table
- ✅ UI shows "250-311 Rules Active"

---

## Testing

**Backend restarted**: January 28, 2026 09:09 AM  
**Status**: Waiting for health check...

**Test steps**:
1. Wait 15 seconds for backend to be healthy
2. Refresh browser (Ctrl+Shift+R)
3. Run reconciliation for 2025-01
4. Check "Rules Active" count

---

**Status**: ✅ Fix applied, backend restarting
