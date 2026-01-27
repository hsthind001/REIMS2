from typing import Any, Dict, Optional

from pydantic import BaseModel

class ReconciliationResult(BaseModel):
    rule_id: str
    rule_name: str
    category: str
    status: str  # PASS, FAIL, WARNING, SKIP
    source_value: float
    target_value: float
    difference: float
    variance_pct: float
    details: str
    severity: str = "medium"
    formula: str | None = None
    intermediate_calculations: Optional[Dict[str, Any]] = None
