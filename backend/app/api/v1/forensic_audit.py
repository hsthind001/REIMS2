"""
Forensic Audit API Endpoints
Big 5 Accounting Firm-Level Comprehensive Forensic Audit System
Implements 140+ audit rules across 7 phases
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text, func, or_
from typing import List, Optional, Dict, Any
from datetime import datetime
from io import BytesIO
import json
from pydantic import BaseModel, Field
from enum import Enum
from celery.result import AsyncResult

from app.db.database import get_db
from app.core.config import settings
from app.core.celery_config import celery_app
from app.models.cash_flow_adjustments import CashFlowAdjustment
from app.models.cash_flow_data import CashFlowData
from app.models.document_upload import DocumentUpload
from app.models.financial_metrics import FinancialMetrics
from app.models.financial_period import FinancialPeriod
from app.models.property import Property
from app.models.validation_result import ValidationResult
from app.models.validation_rule import ValidationRule
from app.services.metrics_service import MetricsService
from app.services.fraud_detection_service import FraudDetectionService
from app.services.validation_service import ValidationService
from app.services.tenant_risk_analysis_service import TenantRiskAnalysisService
from app.services.collections_revenue_quality_service import CollectionsRevenueQualityService
from app.services.audit_scorecard_generator_service import AuditScorecardGeneratorService
from app.services.covenant_compliance_service import CovenantComplianceService
from app.tasks.forensic_audit_tasks import run_complete_forensic_audit_task, await_async, AsyncSessionWrapper

router = APIRouter(prefix="/forensic-audit", tags=["forensic-audit"])


# ============================================================================
# Enums
# ============================================================================

class TrafficLightStatus(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class ReconciliationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


class RiskSeverity(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


class TaskPriority(str, Enum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AuditOpinion(str, Enum):
    UNQUALIFIED = "UNQUALIFIED"  # Clean opinion - all tests passed
    QUALIFIED = "QUALIFIED"  # Some issues but manageable
    ADVERSE = "ADVERSE"  # Significant issues requiring immediate attention


def normalize_traffic_status(
    value: Optional[str],
    default: TrafficLightStatus = TrafficLightStatus.YELLOW
) -> TrafficLightStatus:
    if isinstance(value, TrafficLightStatus):
        return value
    if value is None:
        return default
    normalized = str(value).strip().upper()
    if normalized in {TrafficLightStatus.GREEN.value, TrafficLightStatus.YELLOW.value, TrafficLightStatus.RED.value}:
        return TrafficLightStatus(normalized)
    if normalized in {"PASS", "PASSED", "OK", "SUCCESS", "COMPLIANT"}:
        return TrafficLightStatus.GREEN
    if normalized in {"FAIL", "FAILED", "ERROR", "CRITICAL"}:
        return TrafficLightStatus.RED
    if normalized in {"WARNING", "WARN"}:
        return TrafficLightStatus.YELLOW
    return default


# ============================================================================
# Request Models
# ============================================================================

class RunAuditRequest(BaseModel):
    property_id: int
    period_id: int
    document_id: Optional[int] = Field(default=None, description="Document upload ID for anomaly linkage")
    refresh_views: bool = Field(default=True, description="Refresh materialized views before audit")
    run_fraud_detection: bool = Field(default=True, description="Include fraud detection tests")
    run_covenant_analysis: bool = Field(default=True, description="Include covenant compliance checks")


# ============================================================================
# Response Models
# ============================================================================

class TrafficLightMetric(BaseModel):
    metric_name: str
    current_value: Optional[float] = None
    target_value: Optional[float] = None
    status: TrafficLightStatus
    trend: str = Field(description="UP, DOWN, or STABLE")
    variance_pct: Optional[float] = None


class PriorityRisk(BaseModel):
    risk_id: int
    severity: RiskSeverity
    category: str
    description: str
    financial_impact: Optional[float] = None
    action_required: str
    owner: str
    due_date: Optional[str] = None
    related_metric: Optional[str] = None


class ActionItem(BaseModel):
    action_id: int
    priority: TaskPriority
    description: str
    assigned_to: str
    due_date: str
    status: str  # PENDING, IN_PROGRESS, COMPLETED
    related_risk_id: Optional[int] = None


class ReconciliationResult(BaseModel):
    reconciliation_type: str
    rule_code: str
    status: ReconciliationStatus
    source_document: str
    target_document: str
    source_value: float
    target_value: float
    difference: float
    materiality_threshold: float
    is_material: bool
    explanation: str
    recommendation: Optional[str] = None


class FraudIndicator(BaseModel):
    test_name: str
    status: TrafficLightStatus
    test_statistic: Optional[float] = None
    benchmark_value: Optional[float] = None
    description: str
    severity: str


class CovenantMetric(BaseModel):
    covenant_name: str
    current_value: float
    covenant_threshold: float
    cushion: float
    cushion_pct: float
    status: TrafficLightStatus
    trend: str
    in_compliance: bool


class CovenantDscrTest(BaseModel):
    status: TrafficLightStatus
    dscr: float
    covenant_threshold: float
    trend: Optional[str] = None
    prior_period_dscr: Optional[float] = None
    noi: float
    annual_debt_service: float
    cushion: float
    cushion_pct: float
    explanation: Optional[str] = None


class CovenantLtvTest(BaseModel):
    status: TrafficLightStatus
    ltv: float
    covenant_threshold: float
    trend: Optional[str] = None
    prior_period_ltv: Optional[float] = None
    mortgage_balance: float
    property_value: float
    cushion_pct: float
    explanation: Optional[str] = None


class CovenantInterestCoverageTest(BaseModel):
    status: TrafficLightStatus
    icr: float
    noi: float
    interest_expense: float
    explanation: Optional[str] = None


class CovenantLiquidityTest(BaseModel):
    status: TrafficLightStatus
    current_ratio: float
    current_assets: float
    current_liabilities: float
    quick_ratio: float
    quick_assets: float
    explanation: Optional[str] = None


class CovenantComplianceTests(BaseModel):
    dscr: CovenantDscrTest
    ltv: CovenantLtvTest
    interest_coverage: CovenantInterestCoverageTest
    liquidity: CovenantLiquidityTest


class AuditScorecard(BaseModel):
    """Executive-level audit scorecard for CEO dashboard"""

    # Overall Health
    overall_health_score: int = Field(ge=0, le=100, description="0-100 composite score")
    traffic_light_status: TrafficLightStatus
    audit_opinion: AuditOpinion

    # Property Info
    property_id: int
    property_name: str
    period_id: int
    period_label: str

    # Traffic Light Metrics
    metrics: List[TrafficLightMetric]

    # Priority Risks (Top 5)
    priority_risks: List[PriorityRisk]

    # Financial Performance Summary
    financial_summary: Dict[str, Any]

    # Action Items
    action_items: List[ActionItem]

    # Reconciliation Summary
    reconciliation_summary: Dict[str, Any]

    # Fraud Detection Summary
    fraud_detection_summary: Dict[str, Any]

    # Covenant Compliance Summary
    covenant_summary: Dict[str, Any]

    # Metadata
    generated_at: datetime
    generated_by: str = "REIMS Forensic Audit Engine v1.0"


class AuditTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    estimated_duration_seconds: int = Field(default=180, description="Estimated 2-5 minutes")


class DocumentCompletenessResponse(BaseModel):
    property_id: int
    period_id: int
    period_year: int
    period_month: int
    has_balance_sheet: bool
    has_income_statement: bool
    has_cash_flow_statement: bool
    has_rent_roll: bool
    has_mortgage_statement: bool
    completeness_percentage: float
    missing_documents: List[str]
    status: TrafficLightStatus


class MathIntegrityCheck(BaseModel):
    document_type: str
    rule_name: str
    rule_description: Optional[str] = None
    passed: bool
    severity: str
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None
    difference_percentage: Optional[float] = None
    error_message: Optional[str] = None


class MathIntegrityDocumentSummary(BaseModel):
    document_type: str
    total_checks: int
    passed: int
    failed: int
    warnings: int
    errors: int
    overall_status: TrafficLightStatus
    missing: bool = False


class MathIntegrityResponse(BaseModel):
    property_id: int
    period_id: int
    overall_status: TrafficLightStatus
    total_checks: int
    passed: int
    failed: int
    warnings: int
    errors: int
    missing_documents: List[str]
    documents: List[MathIntegrityDocumentSummary]
    checks: List[MathIntegrityCheck]


class PerformanceBenchmarkMetric(BaseModel):
    metric_key: str
    metric_name: str
    description: str
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    unit: str
    benchmark_low: Optional[float] = None
    benchmark_high: Optional[float] = None
    benchmark_label: Optional[str] = None
    status: TrafficLightStatus
    trend: str = Field(description="UP, DOWN, or STABLE")


class PerformanceBenchmarkResponse(BaseModel):
    property_id: int
    period_id: int
    period_label: str
    overall_status: TrafficLightStatus
    metrics: List[PerformanceBenchmarkMetric]
    missing_inputs: List[str]
    generated_at: datetime


class CrossDocReconciliationResponse(BaseModel):
    property_id: int
    period_id: int
    period_label: str
    total_reconciliations: int
    passed: int
    failed: int
    warnings: int
    pass_rate: float
    reconciliations: List[ReconciliationResult]


class FraudDetectionResponse(BaseModel):
    property_id: int
    period_id: int
    period_label: str
    overall_risk_level: TrafficLightStatus
    tests_conducted: int
    red_flags_found: int
    test_results: Dict[str, FraudIndicator]


class CovenantComplianceResponse(BaseModel):
    overall_status: TrafficLightStatus
    lender_notification_required: Optional[bool] = None
    any_breaches: Optional[bool] = None
    tests: CovenantComplianceTests


class TenantRiskConcentration(BaseModel):
    top_1_pct: float
    top_3_pct: float
    top_5_pct: float
    top_10_pct: float
    top_tenants: List[Dict[str, Any]]


class TenantRiskRollover(BaseModel):
    rollover_12mo_pct: float
    rollover_24mo_pct: float
    rollover_36mo_pct: float


class TenantRiskOccupancy(BaseModel):
    physical_occupancy_pct: float
    economic_occupancy_pct: float
    occupied_sf: float
    total_sf: float


class TenantRiskCreditQuality(BaseModel):
    investment_grade_pct: float
    non_investment_grade_pct: float
    tenant_count: int


class TenantRiskRentPerSf(BaseModel):
    average: float
    median: float
    min: float
    max: float
    std_dev: float


class TenantRiskResponse(BaseModel):
    property_id: int
    period_id: int
    overall_status: TrafficLightStatus
    concentration: TenantRiskConcentration
    rollover: TenantRiskRollover
    occupancy: TenantRiskOccupancy
    credit_quality: TenantRiskCreditQuality
    rent_per_sf: TenantRiskRentPerSf


class CollectionsQualityRevenue(BaseModel):
    quality_score: int = Field(ge=0, le=100)
    total_revenue: float
    collectible_revenue: float
    at_risk_revenue: float
    collectible_pct: float


class CollectionsQualityDso(BaseModel):
    current_dso: float
    target_dso: float
    previous_dso: Optional[float] = None
    dso_status: TrafficLightStatus


class CollectionsQualityCashConversion(BaseModel):
    revenue_recognized: float
    cash_collected: float
    conversion_ratio: float
    conversion_status: TrafficLightStatus


class CollectionsQualityArAging(BaseModel):
    current_0_30: float
    current_0_30_pct: float
    days_31_60: float
    days_31_60_pct: float
    days_61_90: float
    days_61_90_pct: float
    over_90: float
    over_90_pct: float
    total_ar: float


class CollectionsQualityEfficiency(BaseModel):
    collection_rate: float
    write_off_rate: float
    recovery_rate: float


class CollectionsQualityResponse(BaseModel):
    property_id: int
    period_id: int
    overall_status: TrafficLightStatus
    revenue_quality: CollectionsQualityRevenue
    dso: CollectionsQualityDso
    cash_conversion: CollectionsQualityCashConversion
    ar_aging: CollectionsQualityArAging
    efficiency: CollectionsQualityEfficiency


class AuditHistoryItem(BaseModel):
    period_id: int
    period_label: str
    audit_date: datetime
    overall_health_score: int
    traffic_light_status: TrafficLightStatus
    audit_opinion: AuditOpinion
    dscr: Optional[float] = None
    occupancy_rate: Optional[float] = None
    critical_issues: int


# ============================================================================
# API Endpoints
# ============================================================================

def get_period_label(db: Session, property_id: int, period_id: int) -> str:
    period_query = text("""
        SELECT period_year, period_month
        FROM financial_periods
        WHERE id = :period_id AND property_id = :property_id
    """)
    result = db.execute(
        period_query,
        {"period_id": period_id, "property_id": property_id}
    )
    row = result.fetchone()
    if row and row[0] is not None and row[1] is not None:
        return f"{row[0]}-{int(row[1]):02d}"
    return f"Period {period_id}"

@router.post("/run-audit", response_model=AuditTaskResponse, summary="Trigger Complete Forensic Audit")
def run_complete_forensic_audit(
    request: RunAuditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger a complete forensic audit in the background (2-5 minutes).

    This comprehensive audit includes:

    **Phase 1: Document Completeness** (10% progress)
    - Verify all 5 financial documents are present
    - Check version control and period consistency

    **Phase 2: Mathematical Integrity** (20% progress)
    - Balance Sheet equation: Assets = Liabilities + Equity
    - Income Statement calculations
    - Cash Flow statement integrity

    **Phase 3: Cross-Document Reconciliation** (40% progress)
    - Net income flow (IS → BS)
    - Three-way depreciation (IS → BS → CF)
    - Cash reconciliation (BS → CF)
    - Mortgage principal (MS → BS → CF)
    - Four-way property tax and insurance

    **Phase 4: Rent Roll Analysis** (55% progress)
    - Tenant concentration risk
    - Lease rollover analysis
    - Occupancy verification

    **Phase 5: Collections & Revenue Quality** (70% progress)
    - Days Sales Outstanding (DSO)
    - Cash conversion ratio
    - Revenue quality score (0-100)

    **Phase 6: Fraud Detection** (85% progress)
    - Benford's Law analysis
    - Round number detection
    - Duplicate payment analysis
    - Cash ratio integrity

    **Phase 7: Covenant Compliance** (95% progress)
    - DSCR monitoring (≥1.25x)
    - LTV ratio (≤75%)
    - Interest coverage ratio
    - Liquidity ratios

    Returns task ID for status monitoring via `/audit-status/{task_id}`
    """

    try:
        document_id = request.document_id
        if document_id is None:
            document = db.query(DocumentUpload).filter(
                DocumentUpload.property_id == request.property_id,
                DocumentUpload.period_id == request.period_id,
                DocumentUpload.is_active.is_(True)
            ).order_by(DocumentUpload.upload_date.desc()).first()
            if document:
                document_id = document.id

        options = {
            "refresh_views": request.refresh_views,
            "run_fraud_detection": request.run_fraud_detection,
            "run_covenant_analysis": request.run_covenant_analysis,
            "create_anomalies": document_id is not None
        }

        task_result = run_complete_forensic_audit_task.delay(
            request.property_id,
            request.period_id,
            document_id,
            options
        )

        message = "Forensic audit queued successfully. Use /audit-status/{task_id} to monitor progress."
        if document_id is None:
            message += " Anomaly integration skipped (no document upload found)."

        return AuditTaskResponse(
            task_id=task_result.id,
            status="QUEUED",
            message=message,
            estimated_duration_seconds=180
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue audit: {str(e)}"
        )


@router.get("/scorecard/{property_id}/{period_id}", response_model=AuditScorecard, summary="Get CEO Audit Scorecard")
def get_audit_scorecard(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the executive-level audit scorecard for CEO dashboard.

    This endpoint returns a comprehensive scorecard including:

    - **Overall Health Score** (0-100)
    - **Traffic Light Metrics** (15+ key indicators)
    - **Top 5 Priority Risks** with severity and action items
    - **Financial Performance Summary** (YTD revenue, NOI, net income)
    - **Reconciliation Grid** (pass/fail status of all tie-outs)
    - **Fraud Detection Panel** (Benford's Law, round numbers, etc.)
    - **Covenant Compliance Monitor** (DSCR, LTV gauges)

    Perfect for Fortune 500 CEO-level oversight and board reporting.
    """

    try:
        # Query property info
        property_query = text("""
            SELECT p.id, p.property_code, p.property_name,
                   fp.period_year, fp.period_month
            FROM properties p
            JOIN financial_periods fp ON fp.property_id = p.id
            WHERE p.id = :property_id AND fp.id = :period_id
        """)

        result = db.execute(
            property_query,
            {"property_id": property_id, "period_id": period_id}
        )
        property_row = result.fetchone()

        if not property_row:
            raise HTTPException(
                status_code=404,
                detail="Property or period not found"
            )

        scorecard_query = text("""
            SELECT scorecard_data, updated_at, created_at
            FROM audit_scorecard_summary
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY updated_at DESC NULLS LAST, created_at DESC
            LIMIT 1
        """)

        scorecard_result = db.execute(
            scorecard_query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        scorecard_row = scorecard_result.fetchone()

        if scorecard_row and scorecard_row[0]:
            scorecard_data = scorecard_row[0]
            if isinstance(scorecard_data, str):
                scorecard_data = json.loads(scorecard_data)

            scorecard_data.setdefault("property_id", property_id)
            scorecard_data.setdefault("property_name", property_row[2])
            scorecard_data.setdefault("period_id", period_id)
            scorecard_data.setdefault(
                "period_label",
                f"{property_row[3]}-{property_row[4]:02d}"
            )
            scorecard_data.setdefault("metrics", [])
            scorecard_data.setdefault("priority_risks", [])
            scorecard_data.setdefault("action_items", [])
            scorecard_data.setdefault(
                "financial_summary",
                {"total_revenue": 0, "net_income": 0, "noi": 0, "cash_balance": 0}
            )
            scorecard_data.setdefault(
                "reconciliation_summary",
                {
                    "total_reconciliations": 0,
                    "passed": 0,
                    "failed": 0,
                    "warnings": 0,
                    "pass_rate": 0,
                    "pass_rate_pct": 0,
                    "critical_failures": 0
                }
            )
            scorecard_data.setdefault(
                "fraud_detection_summary",
                {
                    "overall_risk_level": "GREEN",
                    "benfords_law_chi_square": None,
                    "benfords_law_threshold": 15.51,
                    "round_number_pct": None,
                    "duplicate_payments_found": 0,
                    "cash_conversion_ratio": None
                }
            )
            scorecard_data.setdefault(
                "covenant_summary",
                {
                    "dscr": None,
                    "dscr_status": "UNKNOWN",
                    "dscr_covenant": 1.25,
                    "dscr_period_id": None,
                    "dscr_period_label": None,
                    "ltv_ratio": None,
                    "ltv": None,
                    "ltv_status": "UNKNOWN",
                    "ltv_covenant": 75.0,
                    "current_ratio": None,
                    "quick_ratio": None
                }
            )

            # Always refresh covenant summary so DSCR reflects latest complete period
            async_db = AsyncSessionWrapper(db)
            scorecard_service = AuditScorecardGeneratorService(async_db)
            scorecard_data["covenant_summary"] = await_async(
                scorecard_service._get_covenant_summary(property_id, period_id)
            )

            if not scorecard_data.get("generated_at"):
                generated_at = scorecard_row[1] or scorecard_row[2] or datetime.now()
                scorecard_data["generated_at"] = (
                    generated_at.isoformat() if hasattr(generated_at, "isoformat") else str(generated_at)
                )

            return AuditScorecard(**scorecard_data)

        async_db = AsyncSessionWrapper(db)
        scorecard_service = AuditScorecardGeneratorService(async_db)
        scorecard_data = await_async(
            scorecard_service.generate_complete_scorecard(property_id, period_id)
        )
        return AuditScorecard(**scorecard_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate scorecard: {str(e)}"
        )


@router.get("/reconciliations/{property_id}/{period_id}",
            response_model=CrossDocReconciliationResponse,
            summary="Get Cross-Document Reconciliation Results")
def get_cross_document_reconciliations(
    property_id: int,
    period_id: int,
    status_filter: Optional[ReconciliationStatus] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    Get all cross-document reconciliation test results.

    Returns detailed results for all 9 reconciliation tests:

    1. **Net Income Flow** (IS → BS Current Period Earnings)
    2. **Depreciation Three-Way** (IS → BS → CF)
    3. **Amortization Three-Way** (IS → BS → CF)
    4. **Cash Reconciliation** (BS → CF)
    5. **Mortgage Principal** (MS → BS → CF)
    6. **Property Tax Four-Way** (IS → BS → CF → MS)
    7. **Insurance Four-Way** (IS → BS → CF → MS)
    8. **Escrow Accounts** (BS → MS)
    9. **Rent to Revenue** (RR → IS)

    Each result includes source/target values, variance, and materiality assessment.
    """

    try:
        # Query from cross_document_reconciliations table
        query = text("""
            SELECT
                reconciliation_type,
                rule_code,
                status,
                source_document,
                target_document,
                source_value,
                target_value,
                difference,
                materiality_threshold,
                is_material,
                explanation,
                recommendation
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY
                CASE status
                    WHEN 'FAIL' THEN 1
                    WHEN 'WARNING' THEN 2
                    WHEN 'PASS' THEN 3
                END,
                reconciliation_type
        """)

        result = db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        rows = result.fetchall()

        reconciliations = []
        for row in rows:
            recon = ReconciliationResult(
                reconciliation_type=row[0],
                rule_code=row[1],
                status=ReconciliationStatus(row[2]),
                source_document=row[3],
                target_document=row[4],
                source_value=float(row[5]),
                target_value=float(row[6]),
                difference=float(row[7]),
                materiality_threshold=float(row[8]),
                is_material=row[9],
                explanation=row[10],
                recommendation=row[11]
            )
            reconciliations.append(recon)

        # Apply status filter if provided
        if status_filter:
            reconciliations = [r for r in reconciliations if r.status == status_filter]

        # Calculate summary statistics
        total = len(reconciliations)
        passed = sum(1 for r in reconciliations if r.status == ReconciliationStatus.PASS)
        failed = sum(1 for r in reconciliations if r.status == ReconciliationStatus.FAIL)
        warnings = sum(1 for r in reconciliations if r.status == ReconciliationStatus.WARNING)
        pass_rate = (passed / total * 100) if total > 0 else 0.0

        return CrossDocReconciliationResponse(
            property_id=property_id,
            period_id=period_id,
            period_label=get_period_label(db, property_id, period_id),
            total_reconciliations=total,
            passed=passed,
            failed=failed,
            warnings=warnings,
            pass_rate=round(pass_rate, 2),
            reconciliations=reconciliations
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get reconciliations: {str(e)}"
        )


@router.get("/fraud-detection/{property_id}/{period_id}",
            response_model=FraudDetectionResponse,
            summary="Get Fraud Detection Test Results")
def get_fraud_detection_results(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get fraud detection test results including:

    - **Benford's Law Analysis** - First digit distribution (chi-square test)
    - **Round Number Analysis** - Fabrication detection (<5% normal, >10% red flag)
    - **Duplicate Payment Detection** - Fictitious payment identification
    - **Cash Conversion Ratio** - Profit vs cash alignment (0.9x+ expected)
    - **Variance Analysis** - Period-over-period anomalies

    Returns overall risk level (GREEN/YELLOW/RED) and detailed test statistics.
    """

    try:
        def build_response(
            *,
            benfords_chi: Optional[float],
            benfords_status_raw: Optional[str],
            round_pct: Optional[float],
            round_status_raw: Optional[str],
            duplicate_count: Optional[int],
            cash_ratio: Optional[float],
            cash_status_raw: Optional[str],
            overall_status_raw: Optional[str],
            red_flags_found: Optional[int]
        ) -> FraudDetectionResponse:
            benfords_status = normalize_traffic_status(benfords_status_raw)
            round_status = normalize_traffic_status(round_status_raw)
            cash_status = normalize_traffic_status(cash_status_raw)
            duplicates = int(duplicate_count or 0)
            duplicate_status = TrafficLightStatus.GREEN if duplicates == 0 else TrafficLightStatus.RED
            duplicate_severity = "GREEN" if duplicates == 0 else "RED"

            test_results = {
                "benfords_law": FraudIndicator(
                    test_name="Benford's Law Analysis",
                    status=benfords_status,
                    test_statistic=float(benfords_chi) if benfords_chi is not None else None,
                    benchmark_value=15.51,  # Chi-square critical value at α=0.05
                    description="First digit distribution analysis. Chi-square > 20.09 indicates manipulation.",
                    severity=str(benfords_status_raw or benfords_status.value)
                ),
                "round_numbers": FraudIndicator(
                    test_name="Round Number Analysis",
                    status=round_status,
                    test_statistic=float(round_pct) if round_pct is not None else None,
                    benchmark_value=10.0,
                    description="Percentage of round numbers. >10% suggests fabrication.",
                    severity=str(round_status_raw or round_status.value)
                ),
                "duplicate_payments": FraudIndicator(
                    test_name="Duplicate Payment Detection",
                    status=duplicate_status,
                    test_statistic=float(duplicates),
                    benchmark_value=0.0,
                    description="Number of duplicate payments found.",
                    severity=duplicate_severity
                ),
                "cash_conversion": FraudIndicator(
                    test_name="Cash Conversion Ratio",
                    status=cash_status,
                    test_statistic=float(cash_ratio) if cash_ratio is not None else None,
                    benchmark_value=0.9,
                    description="Ratio of cash flow to net income. <0.7 requires investigation.",
                    severity=str(cash_status_raw or cash_status.value)
                )
            }

            return FraudDetectionResponse(
                property_id=property_id,
                period_id=period_id,
                period_label=get_period_label(db, property_id, period_id),
                overall_risk_level=normalize_traffic_status(overall_status_raw),
                tests_conducted=4,
                red_flags_found=red_flags_found or 0,
                test_results=test_results
            )

        query = text("""
            SELECT
                benfords_law_chi_square,
                benfords_law_status,
                round_number_pct,
                round_number_status,
                duplicate_payment_count,
                cash_conversion_ratio,
                cash_ratio_status,
                overall_fraud_risk_level,
                red_flags_found
            FROM fraud_detection_results
            WHERE property_id = :property_id AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        row = result.fetchone()

        if not row:
            async_db = AsyncSessionWrapper(db)
            fraud_service = FraudDetectionService(async_db)
            fraud_results = await_async(
                fraud_service.run_all_fraud_tests(property_id, period_id)
            )

            try:
                await_async(
                    fraud_service.save_fraud_detection_results(property_id, period_id, fraud_results)
                )
            except Exception:
                pass

            benfords = fraud_results.get("benfords_law", {})
            round_numbers = fraud_results.get("round_numbers", {})
            duplicate_payments = fraud_results.get("duplicate_payments", {})
            cash_conversion = fraud_results.get("cash_conversion", {})

            return build_response(
                benfords_chi=benfords.get("chi_square"),
                benfords_status_raw=benfords.get("status"),
                round_pct=round_numbers.get("round_number_pct"),
                round_status_raw=round_numbers.get("status"),
                duplicate_count=duplicate_payments.get("duplicate_count"),
                cash_ratio=cash_conversion.get("cash_conversion_ratio"),
                cash_status_raw=cash_conversion.get("status"),
                overall_status_raw=fraud_results.get("overall_fraud_risk_level"),
                red_flags_found=fraud_results.get("red_flags_found")
            )

        return build_response(
            benfords_chi=row[0],
            benfords_status_raw=row[1],
            round_pct=row[2],
            round_status_raw=row[3],
            duplicate_count=row[4],
            cash_ratio=row[5],
            cash_status_raw=row[6],
            overall_status_raw=row[7],
            red_flags_found=row[8]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get fraud detection results: {str(e)}"
        )


@router.get("/covenant-compliance/{property_id}/{period_id}",
            response_model=CovenantComplianceResponse,
            summary="Get Lender Covenant Compliance Status")
def get_covenant_compliance(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get lender covenant compliance monitoring results.

    Tracks key financial covenants including:

    - **DSCR** (Debt Service Coverage Ratio) - Covenant: ≥1.25x
    - **LTV** (Loan-to-Value Ratio) - Covenant: ≤75%
    - **ICR** (Interest Coverage Ratio) - Covenant: ≥2.0x
    - **Current Ratio** - Covenant: ≥1.5x
    - **Quick Ratio** - Covenant: ≥1.0x

    Returns cushion calculations, trending, and breach/warning status.
    """

    try:
        async_db = AsyncSessionWrapper(db)
        covenant_service = CovenantComplianceService(async_db)
        results = await_async(
            covenant_service.calculate_all_covenants(property_id, period_id)
        )

        try:
            await_async(
                covenant_service.save_covenant_compliance_results(property_id, period_id, results)
            )
        except Exception:
            pass

        dscr = results.get("dscr", {})
        ltv = results.get("ltv", {})
        icr = results.get("interest_coverage", {})
        liquidity = results.get("liquidity", {})

        liquidity_status = TrafficLightStatus.GREEN
        if not liquidity.get("current_ratio_compliant", False) or not liquidity.get("quick_ratio_compliant", False):
            liquidity_status = TrafficLightStatus.YELLOW

        current_liabilities = float(liquidity.get("current_liabilities", 0) or 0)
        quick_assets = float(liquidity.get("quick_ratio", 0) or 0) * current_liabilities if current_liabilities else 0.0

        lender_notification_required = bool(
            dscr.get("requires_lender_notification")
            or not dscr.get("in_compliance", True)
            or not ltv.get("in_compliance", True)
        )

        return CovenantComplianceResponse(
            overall_status=TrafficLightStatus(results.get("overall_compliance_status", "GREEN")),
            lender_notification_required=lender_notification_required,
            any_breaches=bool(results.get("covenant_breaches")),
            tests=CovenantComplianceTests(
                dscr=CovenantDscrTest(
                    status=TrafficLightStatus(dscr.get("status", "YELLOW")),
                    dscr=float(dscr.get("dscr", 0) or 0),
                    covenant_threshold=float(dscr.get("covenant_threshold", 1.25) or 1.25),
                    trend=dscr.get("trend"),
                    prior_period_dscr=dscr.get("prior_period_dscr"),
                    noi=float(dscr.get("annual_noi", dscr.get("noi", 0)) or 0),
                    annual_debt_service=float(dscr.get("annual_debt_service", 0) or 0),
                    cushion=float(dscr.get("cushion", 0) or 0),
                    cushion_pct=float(dscr.get("cushion_pct", 0) or 0),
                    explanation=dscr.get("interpretation")
                ),
                ltv=CovenantLtvTest(
                    status=TrafficLightStatus(ltv.get("status", "YELLOW")),
                    ltv=float(ltv.get("ltv_ratio", ltv.get("ltv", 0)) or 0),
                    covenant_threshold=float(ltv.get("covenant_threshold", 75.0) or 75.0),
                    trend=ltv.get("trend"),
                    prior_period_ltv=ltv.get("prior_period_ltv"),
                    mortgage_balance=float(ltv.get("mortgage_balance", 0) or 0),
                    property_value=float(ltv.get("property_value", 0) or 0),
                    cushion_pct=float(ltv.get("cushion_pct", 0) or 0),
                    explanation=ltv.get("interpretation")
                ),
                interest_coverage=CovenantInterestCoverageTest(
                    status=TrafficLightStatus(icr.get("status", "YELLOW")),
                    icr=float(icr.get("interest_coverage_ratio", icr.get("icr", 0)) or 0),
                    noi=float(icr.get("noi", 0) or 0),
                    interest_expense=float(icr.get("interest_expense", 0) or 0),
                    explanation=icr.get("interpretation")
                ),
                liquidity=CovenantLiquidityTest(
                    status=liquidity_status,
                    current_ratio=float(liquidity.get("current_ratio", 0) or 0),
                    current_assets=float(liquidity.get("current_assets", 0) or 0),
                    current_liabilities=current_liabilities,
                    quick_ratio=float(liquidity.get("quick_ratio", 0) or 0),
                    quick_assets=quick_assets,
                    explanation=None
                )
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get covenant compliance: {str(e)}"
        )


@router.get("/tenant-risk/{property_id}/{period_id}",
            response_model=TenantRiskResponse,
            summary="Get Tenant Concentration & Rollover Risk")
def get_tenant_risk_analysis(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get tenant concentration and lease rollover risk analysis.

    Analyzes:

    - **Tenant Concentration** (Top 1, 3, 5, 10 tenants as % of rent)
      - Single tenant >20% = HIGH RISK
      - Top 3 tenants >50% = MODERATE RISK

    - **Lease Rollover** (12-month, 24-month, 36-month windows)
      - 12-month rollover >25% = HIGH RISK
      - 24-month rollover >50% = MODERATE RISK

    - **Credit Quality** (Investment grade vs non-investment grade)

    Returns detailed tenant profiles and risk assessments.
    """

    try:
        async_db = AsyncSessionWrapper(db)
        tenant_service = TenantRiskAnalysisService(async_db)
        results = await_async(
            tenant_service.run_all_tenant_risk_tests(property_id, period_id)
        )

        try:
            await_async(
                tenant_service.save_tenant_risk_results(property_id, period_id, results)
            )
        except Exception:
            pass

        concentration = results.get('concentration_analysis', {})
        rollover = results.get('rollover_analysis', {})
        occupancy = results.get('occupancy_metrics', {})
        credit_quality = results.get('credit_quality', {})
        rent_per_sf = results.get('rent_per_sf_analysis', {})

        overall_status = TrafficLightStatus.GREEN
        if results.get('concentration_risk_status') == 'RED' or results.get('rollover_risk_status') == 'RED':
            overall_status = TrafficLightStatus.RED
        elif results.get('concentration_risk_status') == 'YELLOW' or results.get('rollover_risk_status') == 'YELLOW':
            overall_status = TrafficLightStatus.YELLOW

        top_tenants_raw = concentration.get('top_tenants', []) or []
        top_tenants = []
        for tenant in top_tenants_raw:
            top_tenants.append({
                "tenant_name": tenant.get("tenant_name"),
                "monthly_rent": tenant.get("monthly_rent", 0),
                "pct_of_total": tenant.get("percent_of_total_rent", 0)
            })

        return TenantRiskResponse(
            property_id=property_id,
            period_id=period_id,
            overall_status=overall_status,
            concentration=TenantRiskConcentration(
                top_1_pct=float(concentration.get('top_1_tenant_pct', 0)),
                top_3_pct=float(concentration.get('top_3_tenant_pct', 0)),
                top_5_pct=float(concentration.get('top_5_tenant_pct', 0)),
                top_10_pct=float(concentration.get('top_10_tenant_pct', 0)),
                top_tenants=top_tenants
            ),
            rollover=TenantRiskRollover(
                rollover_12mo_pct=float(rollover.get('rollover_12mo_pct', 0)),
                rollover_24mo_pct=float(rollover.get('rollover_24mo_pct', 0)),
                rollover_36mo_pct=float(rollover.get('rollover_36mo_pct', 0))
            ),
            occupancy=TenantRiskOccupancy(
                physical_occupancy_pct=float(occupancy.get('occupancy_rate', 0)),
                economic_occupancy_pct=float(occupancy.get('economic_occupancy', occupancy.get('occupancy_rate', 0))),
                occupied_sf=float(occupancy.get('occupied_sf', 0)),
                total_sf=float(occupancy.get('total_sf', 0))
            ),
            credit_quality=TenantRiskCreditQuality(
                investment_grade_pct=float(credit_quality.get('investment_grade_pct', 0)),
                non_investment_grade_pct=float(credit_quality.get('non_investment_grade_pct', 0)),
                tenant_count=int(credit_quality.get('tenant_count', 0))
            ),
            rent_per_sf=TenantRiskRentPerSf(
                average=float(rent_per_sf.get('average_rent_per_sf', 0)),
                median=float(rent_per_sf.get('median_rent_per_sf', 0)),
                min=float(rent_per_sf.get('min_rent_per_sf', 0)),
                max=float(rent_per_sf.get('max_rent_per_sf', 0)),
                std_dev=float(rent_per_sf.get('std_dev_rent_per_sf', 0))
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tenant risk analysis: {str(e)}"
        )


@router.get("/collections-quality/{property_id}/{period_id}",
            response_model=CollectionsQualityResponse,
            summary="Get Collections & Revenue Quality Metrics")
def get_collections_revenue_quality(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get collections and revenue quality metrics.

    Calculates:

    - **DSO** (Days Sales Outstanding)
      - Formula: (A/R Balance / Monthly Rent) × 30 days
      - <30 days = EXCELLENT, 30-60 = GOOD, >60 = RED FLAG

    - **Cash Conversion Ratio**
      - Formula: Cash Collections / Billed Revenue
      - >90% = EXCELLENT, 80-90% = GOOD, <80% = POOR

    - **Revenue Quality Score** (0-100 composite)
      - Collections: 40 points
      - Cash Conversion: 30 points
      - Occupancy: 20 points
      - Tenant Credit Quality: 10 points

    - **A/R Aging** (Current, 30-60, 60-90, 90+ days)
    """

    try:
        async_db = AsyncSessionWrapper(db)
        collections_service = CollectionsRevenueQualityService(async_db)
        results = await_async(
            collections_service.run_all_collections_tests(property_id, period_id)
        )

        try:
            await_async(
                collections_service.save_collections_results(property_id, period_id, results)
            )
        except Exception:
            pass

        dso_result = results["tests"]["days_sales_outstanding"]
        cash_result = results["tests"]["cash_conversion_ratio"]
        aging_result = results["tests"]["ar_aging_analysis"]
        quality_result = results["tests"]["revenue_quality_score"]

        revenue_total = float(cash_result.get("billed_revenue", 0))
        cash_collected = float(cash_result.get("cash_collections", 0))
        collectible_pct = float(cash_result.get("cash_conversion_percentage", 0))

        return CollectionsQualityResponse(
            property_id=property_id,
            period_id=period_id,
            overall_status=TrafficLightStatus(results["overall_status"]),
            revenue_quality=CollectionsQualityRevenue(
                quality_score=int(quality_result.get("total_score", 0)),
                total_revenue=revenue_total,
                collectible_revenue=cash_collected,
                at_risk_revenue=max(revenue_total - cash_collected, 0.0),
                collectible_pct=collectible_pct
            ),
            dso=CollectionsQualityDso(
                current_dso=float(dso_result.get("dso_days", 0)),
                target_dso=CollectionsRevenueQualityService.DSO_EXCELLENT,
                previous_dso=None,
                dso_status=TrafficLightStatus(dso_result.get("status", "YELLOW"))
            ),
            cash_conversion=CollectionsQualityCashConversion(
                revenue_recognized=revenue_total,
                cash_collected=cash_collected,
                conversion_ratio=float(cash_result.get("cash_conversion_ratio", 0)),
                conversion_status=TrafficLightStatus(cash_result.get("status", "YELLOW"))
            ),
            ar_aging=CollectionsQualityArAging(
                current_0_30=float(aging_result.get("current_0_30", 0)),
                current_0_30_pct=float(aging_result.get("current_pct", 0)),
                days_31_60=float(aging_result.get("days_31_60", 0)),
                days_31_60_pct=float(aging_result.get("pct_31_60", 0)),
                days_61_90=float(aging_result.get("days_61_90", 0)),
                days_61_90_pct=float(aging_result.get("pct_61_90", 0)),
                over_90=float(aging_result.get("days_91_plus", 0)),
                over_90_pct=float(aging_result.get("pct_91_plus", 0)),
                total_ar=float(aging_result.get("total_ar", 0))
            ),
            efficiency=CollectionsQualityEfficiency(
                collection_rate=float(cash_result.get("cash_conversion_percentage", 0)),
                write_off_rate=0.0,
                recovery_rate=0.0
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get collections quality: {str(e)}"
        )


@router.get("/document-completeness/{property_id}/{period_id}",
            response_model=DocumentCompletenessResponse,
            summary="Get Document Completeness Matrix")
def get_document_completeness(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get document completeness status for the period.

    Verifies presence of all 5 required financial documents:

    1. Balance Sheet
    2. Income Statement
    3. Cash Flow Statement
    4. Rent Roll
    5. Mortgage Statement

    Returns completeness percentage and list of missing documents.
    """

    try:
        query = text("""
            SELECT
                period_year,
                period_month,
                has_balance_sheet,
                has_income_statement,
                has_cash_flow_statement,
                has_rent_roll,
                has_mortgage_statement,
                completeness_percentage
            FROM document_completeness_matrix
            WHERE property_id = :property_id AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)

        result = db.execute(
            query,
            {"property_id": str(property_id), "period_id": str(period_id)}
        )
        row = result.fetchone()

        if not row:
            period = db.query(FinancialPeriod).filter(
                FinancialPeriod.id == period_id,
                FinancialPeriod.property_id == property_id
            ).first()

            if not period:
                raise HTTPException(
                    status_code=404,
                    detail="Property or period not found"
                )

            doc_rows = db.query(
                DocumentUpload.document_type,
                func.count(DocumentUpload.id)
            ).filter(
                DocumentUpload.property_id == property_id,
                DocumentUpload.period_id == period_id,
                DocumentUpload.is_active.is_(True)
            ).group_by(DocumentUpload.document_type).all()

            present_types = {row_type for row_type, row_count in doc_rows if row_count}

            has_balance_sheet = "balance_sheet" in present_types
            has_income_statement = "income_statement" in present_types
            has_cash_flow_statement = "cash_flow" in present_types
            has_rent_roll = "rent_roll" in present_types
            has_mortgage_statement = "mortgage_statement" in present_types

            completeness_count = sum([
                has_balance_sheet,
                has_income_statement,
                has_cash_flow_statement,
                has_rent_roll,
                has_mortgage_statement
            ])
            completeness_pct = (completeness_count / 5) * 100

            missing_documents = []
            if not has_balance_sheet:
                missing_documents.append("Balance Sheet")
            if not has_income_statement:
                missing_documents.append("Income Statement")
            if not has_cash_flow_statement:
                missing_documents.append("Cash Flow Statement")
            if not has_rent_roll:
                missing_documents.append("Rent Roll")
            if not has_mortgage_statement:
                missing_documents.append("Mortgage Statement")

            status = TrafficLightStatus.GREEN if completeness_pct == 100.0 else (
                TrafficLightStatus.YELLOW if completeness_pct >= 80.0 else TrafficLightStatus.RED
            )

            return DocumentCompletenessResponse(
                property_id=property_id,
                period_id=period_id,
                period_year=period.period_year,
                period_month=period.period_month,
                has_balance_sheet=has_balance_sheet,
                has_income_statement=has_income_statement,
                has_cash_flow_statement=has_cash_flow_statement,
                has_rent_roll=has_rent_roll,
                has_mortgage_statement=has_mortgage_statement,
                completeness_percentage=completeness_pct,
                missing_documents=missing_documents,
                status=status
            )

        missing_documents = []
        if not row[2]:
            missing_documents.append("Balance Sheet")
        if not row[3]:
            missing_documents.append("Income Statement")
        if not row[4]:
            missing_documents.append("Cash Flow Statement")
        if not row[5]:
            missing_documents.append("Rent Roll")
        if not row[6]:
            missing_documents.append("Mortgage Statement")

        completeness_pct = float(row[7])
        status = TrafficLightStatus.GREEN if completeness_pct == 100.0 else (
            TrafficLightStatus.YELLOW if completeness_pct >= 80.0 else TrafficLightStatus.RED
        )

        return DocumentCompletenessResponse(
            property_id=property_id,
            period_id=period_id,
            period_year=row[0],
            period_month=row[1],
            has_balance_sheet=row[2],
            has_income_statement=row[3],
            has_cash_flow_statement=row[4],
            has_rent_roll=row[5],
            has_mortgage_statement=row[6],
            completeness_percentage=completeness_pct,
            missing_documents=missing_documents,
            status=status
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get document completeness: {str(e)}"
        )


@router.get("/math-integrity/{property_id}/{period_id}",
            response_model=MathIntegrityResponse,
            summary="Get Mathematical Integrity Checks")
def get_math_integrity(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get mathematical integrity checks across core documents.

    Uses validation rules for balance checks and calculation checks to determine
    whether statements tie internally.
    """

    try:
        document_types = [
            ("balance_sheet", "Balance Sheet"),
            ("income_statement", "Income Statement"),
            ("cash_flow", "Cash Flow Statement"),
            ("rent_roll", "Rent Roll"),
            ("mortgage_statement", "Mortgage Statement"),
        ]
        rule_types = ["balance_check", "calculation_check"]

        documents: List[MathIntegrityDocumentSummary] = []
        checks: List[MathIntegrityCheck] = []
        missing_documents: List[str] = []

        validation_service = ValidationService(db)

        for document_type, label in document_types:
            upload = db.query(DocumentUpload).filter(
                DocumentUpload.property_id == property_id,
                DocumentUpload.period_id == period_id,
                DocumentUpload.document_type == document_type,
                DocumentUpload.is_active.is_(True)
            ).order_by(
                DocumentUpload.upload_date.desc().nullslast(),
                DocumentUpload.id.desc()
            ).first()

            if not upload:
                missing_documents.append(label)
                documents.append(MathIntegrityDocumentSummary(
                    document_type=document_type,
                    total_checks=0,
                    passed=0,
                    failed=0,
                    warnings=0,
                    errors=0,
                    overall_status=TrafficLightStatus.YELLOW,
                    missing=True
                ))
                continue

            base_query = db.query(ValidationResult, ValidationRule).join(
                ValidationRule, ValidationRule.id == ValidationResult.rule_id
            ).filter(
                ValidationResult.upload_id == upload.id,
                ValidationRule.document_type == document_type,
                ValidationRule.rule_type.in_(rule_types)
            ).order_by(ValidationResult.created_at.desc())

            results = base_query.all()
            if not results:
                validation_service.validate_upload(upload.id)
                results = base_query.all()

            seen_rule_ids = set()
            document_checks = []

            for result, rule in results:
                if rule.id in seen_rule_ids:
                    continue
                seen_rule_ids.add(rule.id)
                check = MathIntegrityCheck(
                    document_type=document_type,
                    rule_name=rule.rule_name,
                    rule_description=rule.rule_description,
                    passed=result.passed,
                    severity=result.severity,
                    expected_value=float(result.expected_value) if result.expected_value is not None else None,
                    actual_value=float(result.actual_value) if result.actual_value is not None else None,
                    difference=float(result.difference) if result.difference is not None else None,
                    difference_percentage=float(result.difference_percentage) if result.difference_percentage is not None else None,
                    error_message=result.error_message
                )
                checks.append(check)
                document_checks.append(check)

            total_checks = len(document_checks)
            passed_checks = sum(1 for check in document_checks if check.passed)
            failed_checks = total_checks - passed_checks
            warnings = sum(1 for check in document_checks if not check.passed and check.severity == "warning")
            errors = sum(1 for check in document_checks if not check.passed and check.severity == "error")
            overall_status = (
                TrafficLightStatus.RED if errors > 0 else
                TrafficLightStatus.YELLOW if warnings > 0 else
                TrafficLightStatus.GREEN
            )

            documents.append(MathIntegrityDocumentSummary(
                document_type=document_type,
                total_checks=total_checks,
                passed=passed_checks,
                failed=failed_checks,
                warnings=warnings,
                errors=errors,
                overall_status=overall_status,
                missing=False
            ))

        total_checks = sum(doc.total_checks for doc in documents)
        passed_checks = sum(doc.passed for doc in documents)
        failed_checks = sum(doc.failed for doc in documents)
        warning_checks = sum(doc.warnings for doc in documents)
        error_checks = sum(doc.errors for doc in documents)

        overall_status = (
            TrafficLightStatus.RED if error_checks > 0 else
            TrafficLightStatus.YELLOW if warning_checks > 0 or missing_documents else
            TrafficLightStatus.GREEN
        )

        return MathIntegrityResponse(
            property_id=property_id,
            period_id=period_id,
            overall_status=overall_status,
            total_checks=total_checks,
            passed=passed_checks,
            failed=failed_checks,
            warnings=warning_checks,
            errors=error_checks,
            missing_documents=missing_documents,
            documents=documents,
            checks=checks
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get mathematical integrity results: {str(e)}"
        )


@router.get("/performance-benchmark/{property_id}/{period_id}",
            response_model=PerformanceBenchmarkResponse,
            summary="Get Performance & Benchmarking Metrics")
def get_performance_benchmark(
    property_id: int,
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Get performance metrics and benchmarking for Phase 8.

    Includes same-store growth, NOI margin, operating expense ratio,
    and capital expenditure ratio benchmarks.
    """

    def trend_for(current: Optional[float], previous: Optional[float], threshold: float = 0.1) -> str:
        if current is None or previous is None:
            return "STABLE"
        delta = current - previous
        if abs(delta) < threshold:
            return "STABLE"
        return "UP" if delta > 0 else "DOWN"

    def get_period(year: int, month: int) -> Optional[FinancialPeriod]:
        return db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id,
            FinancialPeriod.period_year == year,
            FinancialPeriod.period_month == month
        ).first()

    def get_metrics_for_period(target_period_id: int) -> Optional[FinancialMetrics]:
        return db.query(FinancialMetrics).filter(
            FinancialMetrics.property_id == property_id,
            FinancialMetrics.period_id == target_period_id
        ).first()

    def compute_same_store_growth(
        target_period: Optional[FinancialPeriod],
        target_metrics: Optional[FinancialMetrics]
    ) -> Optional[float]:
        if not target_period or not target_metrics:
            return None
        if target_metrics.total_revenue is None:
            return None
        prior_period = get_period(target_period.period_year - 1, target_period.period_month)
        if not prior_period:
            return None
        prior_metrics = get_metrics_for_period(prior_period.id)
        if not prior_metrics or prior_metrics.total_revenue in (None, 0):
            return None
        current_revenue = float(target_metrics.total_revenue)
        prior_revenue = float(prior_metrics.total_revenue)
        return ((current_revenue - prior_revenue) / prior_revenue) * 100
        return ((current_revenue - prior_revenue) / prior_revenue) * 100

    def compute_capex_ratio(target_period_id: int, revenue: Optional[float]) -> Optional[float]:
        if revenue is None or revenue == 0:
            return None
            
        # Try adjustments first (Manual Journal Entries for CapEx)
        capex_sum = db.query(func.sum(CashFlowAdjustment.amount)).filter(
            CashFlowAdjustment.property_id == property_id,
            CashFlowAdjustment.period_id == target_period_id,
            CashFlowAdjustment.adjustment_category == 'PROPERTY_EQUIPMENT'
        ).scalar()
        
        # Fallback to CashFlowData if no adjustments found
        # Look for CapEx items in ADDITIONAL_EXPENSE section
        if capex_sum is None or capex_sum == 0:
             search_terms = [
                'improvements', 'construction', 'capex', 'capital', 
                'renovation', 'replacement', 'fixed assets', 'major repairs',
                '30 year'  # Specific for "30 Year - Roof"
             ]
             
             conditions = [CashFlowData.account_name.ilike(f'%{term}%') for term in search_terms]
             
             cf_sum = db.query(func.sum(CashFlowData.period_amount)).filter(
                 CashFlowData.property_id == property_id,
                 CashFlowData.period_id == target_period_id,
                 CashFlowData.line_section == 'ADDITIONAL_EXPENSE',
                 or_(*conditions)
             ).scalar()
             
             if cf_sum is not None:
                 # Cash flow outflows are usually negative, we want positive amount for ratio
                 capex_sum = abs(float(cf_sum))
             elif capex_sum is None: # If both are None
                 return None
             else:
                 capex_sum = abs(float(capex_sum)) # Logic: if cf_sum None but capex_sum 0, use 0.
        else:
             capex_sum = abs(float(capex_sum))
             
        # Add any found CF data to adjustment data if both exist (rare but possible)
        # Actually simplest is: if adjustment exists, use it. If not, fallback.
        # The above logic does exactly that.
             
        return (capex_sum / revenue) * 100

    try:
        period = db.query(FinancialPeriod).filter(
            FinancialPeriod.id == period_id,
            FinancialPeriod.property_id == property_id
        ).first()

        if not period:
            raise HTTPException(
                status_code=404,
                detail="Property or period not found"
            )

        property_row = db.query(Property).filter(Property.id == property_id).first()
        property_type = (property_row.property_type or "").strip().lower() if property_row else ""

        metrics_record = get_metrics_for_period(period_id)
        if not metrics_record:
            metrics_service = MetricsService(db)
            metrics_record = metrics_service.calculate_all_metrics(property_id, period_id)

        current_revenue = float(metrics_record.total_revenue) if metrics_record and metrics_record.total_revenue is not None else None

        prev_year = period.period_year
        prev_month = period.period_month - 1 if period.period_month else None
        if prev_month == 0:
            prev_year -= 1
            prev_month = 12
        prev_period = get_period(prev_year, prev_month) if prev_month else None
        prev_metrics = get_metrics_for_period(prev_period.id) if prev_period else None

        # Benchmarks by property type
        noi_benchmarks = {
            "retail": (60.0, 70.0),
            "office": (50.0, 60.0),
            "industrial": (60.0, 70.0),
            "multi-family": (50.0, 65.0),
            "multifamily": (50.0, 65.0),
            "mixed-use": (50.0, 60.0)
        }
        opex_benchmarks = {
            "retail": (30.0, 40.0),
            "office": (40.0, 50.0),
            "industrial": (30.0, 40.0),
            "multi-family": (35.0, 50.0),
            "multifamily": (35.0, 50.0),
            "mixed-use": (35.0, 50.0)
        }
        noi_low, noi_high = noi_benchmarks.get(property_type, (55.0, 65.0))
        opex_low, opex_high = opex_benchmarks.get(property_type, (35.0, 50.0))

        missing_inputs: List[str] = []
        metrics_response: List[PerformanceBenchmarkMetric] = []

        if current_revenue is None:
            missing_inputs.append("Total revenue")

        same_store_growth = compute_same_store_growth(period, metrics_record)
        prev_same_store_growth = compute_same_store_growth(prev_period, prev_metrics) if prev_period else None

        if same_store_growth is None:
            missing_inputs.append("Prior-year revenue")

        if same_store_growth is None:
            same_store_status = TrafficLightStatus.YELLOW
        elif same_store_growth >= 5:
            same_store_status = TrafficLightStatus.GREEN
        elif same_store_growth >= 0:
            same_store_status = TrafficLightStatus.YELLOW
        else:
            same_store_status = TrafficLightStatus.RED

        metrics_response.append(PerformanceBenchmarkMetric(
            metric_key="same_store_growth",
            metric_name="Same-Store Revenue Growth",
            description="Year-over-year revenue change for the same period",
            current_value=same_store_growth,
            previous_value=prev_same_store_growth,
            unit="%",
            benchmark_low=2.0,
            benchmark_high=5.0,
            benchmark_label="Strong >5%, moderate 2-5%",
            status=same_store_status,
            trend=trend_for(same_store_growth, prev_same_store_growth)
        ))

        noi_margin = float(metrics_record.operating_margin) if metrics_record and metrics_record.operating_margin is not None else None
        prev_noi_margin = float(prev_metrics.operating_margin) if prev_metrics and prev_metrics.operating_margin is not None else None

        if noi_margin is None:
            missing_inputs.append("NOI margin")

        if noi_margin is None:
            noi_status = TrafficLightStatus.YELLOW
        elif noi_margin >= noi_low:
            noi_status = TrafficLightStatus.GREEN
        elif noi_margin >= (noi_low - 5):
            noi_status = TrafficLightStatus.YELLOW
        else:
            noi_status = TrafficLightStatus.RED

        metrics_response.append(PerformanceBenchmarkMetric(
            metric_key="noi_margin",
            metric_name="NOI Margin",
            description="Net operating income as a percent of revenue",
            current_value=noi_margin,
            previous_value=prev_noi_margin,
            unit="%",
            benchmark_low=noi_low,
            benchmark_high=noi_high,
            benchmark_label=f"Target {noi_low:.0f}-{noi_high:.0f}%",
            status=noi_status,
            trend=trend_for(noi_margin, prev_noi_margin)
        ))

        opex_ratio = float(metrics_record.expense_ratio) if metrics_record and metrics_record.expense_ratio is not None else None
        prev_opex_ratio = float(prev_metrics.expense_ratio) if prev_metrics and prev_metrics.expense_ratio is not None else None

        if opex_ratio is None:
            missing_inputs.append("Operating expense ratio")

        if opex_ratio is None:
            opex_status = TrafficLightStatus.YELLOW
        elif opex_ratio <= opex_low:
            opex_status = TrafficLightStatus.GREEN
        elif opex_ratio <= opex_high:
            opex_status = TrafficLightStatus.YELLOW
        else:
            opex_status = TrafficLightStatus.RED

        metrics_response.append(PerformanceBenchmarkMetric(
            metric_key="operating_expense_ratio",
            metric_name="Operating Expense Ratio",
            description="Operating expenses as a percent of revenue",
            current_value=opex_ratio,
            previous_value=prev_opex_ratio,
            unit="%",
            benchmark_low=opex_low,
            benchmark_high=opex_high,
            benchmark_label=f"Target {opex_low:.0f}-{opex_high:.0f}%",
            status=opex_status,
            trend=trend_for(opex_ratio, prev_opex_ratio)
        ))

        capex_ratio = compute_capex_ratio(period_id, current_revenue)
        prev_capex_ratio = compute_capex_ratio(prev_period.id, float(prev_metrics.total_revenue)) if prev_period and prev_metrics and prev_metrics.total_revenue is not None else None

        if capex_ratio is None:
            missing_inputs.append("CapEx adjustments")

        if capex_ratio is None:
            capex_status = TrafficLightStatus.YELLOW
        elif capex_ratio <= 5:
            capex_status = TrafficLightStatus.GREEN
        elif capex_ratio <= 10:
            capex_status = TrafficLightStatus.YELLOW
        else:
            capex_status = TrafficLightStatus.RED

        metrics_response.append(PerformanceBenchmarkMetric(
            metric_key="capex_ratio",
            metric_name="CapEx Ratio",
            description="Capital expenditures as a percent of revenue",
            current_value=capex_ratio,
            previous_value=prev_capex_ratio,
            unit="%",
            benchmark_low=5.0,
            benchmark_high=10.0,
            benchmark_label="Target <5%, monitor 5-10%",
            status=capex_status,
            trend=trend_for(capex_ratio, prev_capex_ratio)
        ))

        overall_status = TrafficLightStatus.GREEN
        if any(metric.status == TrafficLightStatus.RED for metric in metrics_response):
            overall_status = TrafficLightStatus.RED
        elif any(metric.status == TrafficLightStatus.YELLOW for metric in metrics_response):
            overall_status = TrafficLightStatus.YELLOW

        return PerformanceBenchmarkResponse(
            property_id=property_id,
            period_id=period_id,
            period_label=f"{period.period_year}-{period.period_month:02d}",
            overall_status=overall_status,
            metrics=metrics_response,
            missing_inputs=sorted(set(missing_inputs)),
            generated_at=datetime.utcnow()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance benchmarks: {str(e)}"
        )


@router.get("/export-report/{property_id}/{period_id}",
            summary="Export Audit Report (PDF/Excel)")
def export_audit_report(
    property_id: int,
    period_id: int,
    format: str = Query("pdf", regex="^(pdf|excel)$", description="Export format: pdf or excel"),
    db: Session = Depends(get_db)
):
    """
    Export complete audit report in PDF or Excel format.

    **PDF Format:**
    - Executive summary with scorecard
    - All reconciliation results
    - Fraud detection findings
    - Covenant compliance status
    - Recommendations and action items

    **Excel Format:**
    - Multiple worksheets for each audit phase
    - Pivot tables for analysis
    - Data export for further analysis

    Returns downloadable file.
    """

    try:
        property_query = text("""
            SELECT p.property_code, p.property_name,
                   fp.period_year, fp.period_month
            FROM properties p
            JOIN financial_periods fp ON fp.property_id = p.id
            WHERE p.id = :property_id AND fp.id = :period_id
        """)

        property_result = db.execute(
            property_query,
            {"property_id": property_id, "period_id": period_id}
        )
        property_row = property_result.fetchone()
        if not property_row:
            raise HTTPException(status_code=404, detail="Property or period not found")

        scorecard_model = get_audit_scorecard(property_id, period_id, db)
        scorecard = scorecard_model.model_dump() if hasattr(scorecard_model, "model_dump") else scorecard_model.dict()

        recon_query = text("""
            SELECT
                reconciliation_type,
                rule_code,
                status,
                source_document,
                target_document,
                source_value,
                target_value,
                difference,
                materiality_threshold,
                is_material,
                explanation,
                recommendation
            FROM cross_document_reconciliations
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY rule_code
        """)
        recon_rows = db.execute(
            recon_query,
            {"property_id": property_id, "period_id": period_id}
        ).fetchall()

        fraud_query = text("""
            SELECT
                overall_fraud_risk_level,
                benfords_law_chi_square,
                round_number_pct,
                duplicate_payment_count,
                cash_conversion_ratio,
                red_flags_found
            FROM fraud_detection_results
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        fraud_row = db.execute(
            fraud_query,
            {"property_id": property_id, "period_id": period_id}
        ).fetchone()

        covenant_query = text("""
            SELECT
                dscr,
                dscr_status,
                dscr_covenant_threshold,
                ltv_ratio,
                ltv_status,
                ltv_covenant_threshold,
                interest_coverage_ratio,
                current_ratio,
                quick_ratio,
                overall_compliance_status
            FROM covenant_compliance_tracking
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        covenant_row = db.execute(
            covenant_query,
            {"property_id": property_id, "period_id": period_id}
        ).fetchone()

        tenant_query = text("""
            SELECT
                top_1_tenant_pct,
                top_3_tenant_pct,
                top_5_tenant_pct,
                top_10_tenant_pct,
                lease_rollover_12mo_pct,
                lease_rollover_24mo_pct,
                lease_rollover_36mo_pct,
                occupancy_rate,
                investment_grade_tenant_pct
            FROM tenant_risk_analysis
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        tenant_row = db.execute(
            tenant_query,
            {"property_id": property_id, "period_id": period_id}
        ).fetchone()

        collections_query = text("""
            SELECT
                days_sales_outstanding,
                dso_status,
                cash_conversion_ratio,
                revenue_quality_score,
                overall_status
            FROM collections_revenue_quality
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        collections_row = db.execute(
            collections_query,
            {"property_id": property_id, "period_id": period_id}
        ).fetchone()

        completeness_query = text("""
            SELECT
                has_balance_sheet,
                has_income_statement,
                has_cash_flow_statement,
                has_rent_roll,
                has_mortgage_statement,
                completeness_percentage
            FROM document_completeness_matrix
            WHERE property_id = :property_id
            AND period_id = :period_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        completeness_row = db.execute(
            completeness_query,
            {"property_id": property_id, "period_id": period_id}
        ).fetchone()

        validation_query = text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN vr.passed THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN vr.passed = false THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN vr.passed = false AND vr.severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical_failures
            FROM validation_results vr
            JOIN document_uploads du ON du.id = vr.upload_id
            WHERE du.property_id = :property_id
            AND du.period_id = :period_id
            AND du.is_active = true
        """)
        validation_row = db.execute(
            validation_query,
            {"property_id": property_id, "period_id": period_id}
        ).fetchone()

        period_label = scorecard.get("period_label") or f"{property_row[2]}-{property_row[3]:02d}"
        file_base = f"forensic_audit_report_{property_row[0] or property_row[1]}_{period_label}"

        if format == "excel":
            import pandas as pd

            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                summary_df = pd.DataFrame([
                    {"Metric": "Property", "Value": property_row[1]},
                    {"Metric": "Property Code", "Value": property_row[0]},
                    {"Metric": "Period", "Value": period_label},
                    {"Metric": "Generated At", "Value": scorecard.get("generated_at")},
                    {"Metric": "Overall Health Score", "Value": scorecard.get("overall_health_score")},
                    {"Metric": "Traffic Light Status", "Value": scorecard.get("traffic_light_status")},
                    {"Metric": "Audit Opinion", "Value": scorecard.get("audit_opinion")}
                ])
                summary_df.to_excel(writer, sheet_name="Executive Summary", index=False)

                financial_summary = scorecard.get("financial_summary") or {}
                financial_df = pd.DataFrame([
                    {"Metric": "Total Revenue", "Value": financial_summary.get("total_revenue", 0)},
                    {"Metric": "Net Income", "Value": financial_summary.get("net_income", 0)},
                    {"Metric": "NOI", "Value": financial_summary.get("noi", 0)},
                    {"Metric": "Cash Balance", "Value": financial_summary.get("cash_balance", 0)},
                    {"Metric": "NOI Margin %", "Value": financial_summary.get("noi_margin_pct", 0)}
                ])
                financial_df.to_excel(writer, sheet_name="Financial Summary", index=False)

                risks_df = pd.DataFrame(scorecard.get("priority_risks") or [])
                if not risks_df.empty:
                    risks_df.to_excel(writer, sheet_name="Priority Risks", index=False)

                actions_df = pd.DataFrame(scorecard.get("action_items") or [])
                if not actions_df.empty:
                    actions_df.to_excel(writer, sheet_name="Action Items", index=False)

                metrics_df = pd.DataFrame(scorecard.get("metrics") or [])
                if not metrics_df.empty:
                    metrics_df.to_excel(writer, sheet_name="Traffic Metrics", index=False)

                if recon_rows:
                    recon_df = pd.DataFrame([
                        {
                            "Reconciliation Type": row[0],
                            "Rule Code": row[1],
                            "Status": row[2],
                            "Source": row[3],
                            "Target": row[4],
                            "Source Value": row[5],
                            "Target Value": row[6],
                            "Difference": row[7],
                            "Materiality Threshold": row[8],
                            "Material": row[9],
                            "Explanation": row[10],
                            "Recommendation": row[11]
                        }
                        for row in recon_rows
                    ])
                    recon_df.to_excel(writer, sheet_name="Reconciliations", index=False)

                fraud_df = pd.DataFrame([
                    {
                        "Overall Risk Level": fraud_row[0] if fraud_row else None,
                        "Benford Chi Square": fraud_row[1] if fraud_row else None,
                        "Round Number %": fraud_row[2] if fraud_row else None,
                        "Duplicate Payments": fraud_row[3] if fraud_row else None,
                        "Cash Conversion Ratio": fraud_row[4] if fraud_row else None,
                        "Red Flags Found": fraud_row[5] if fraud_row else None
                    }
                ])
                fraud_df.to_excel(writer, sheet_name="Fraud Detection", index=False)

                covenant_df = pd.DataFrame([
                    {
                        "DSCR": covenant_row[0] if covenant_row else None,
                        "DSCR Status": covenant_row[1] if covenant_row else None,
                        "DSCR Covenant": covenant_row[2] if covenant_row else None,
                        "LTV": covenant_row[3] if covenant_row else None,
                        "LTV Status": covenant_row[4] if covenant_row else None,
                        "LTV Covenant": covenant_row[5] if covenant_row else None,
                        "Interest Coverage": covenant_row[6] if covenant_row else None,
                        "Current Ratio": covenant_row[7] if covenant_row else None,
                        "Quick Ratio": covenant_row[8] if covenant_row else None,
                        "Overall Status": covenant_row[9] if covenant_row else None
                    }
                ])
                covenant_df.to_excel(writer, sheet_name="Covenant Compliance", index=False)

                tenant_df = pd.DataFrame([
                    {
                        "Top 1 Tenant %": tenant_row[0] if tenant_row else None,
                        "Top 3 Tenants %": tenant_row[1] if tenant_row else None,
                        "Top 5 Tenants %": tenant_row[2] if tenant_row else None,
                        "Top 10 Tenants %": tenant_row[3] if tenant_row else None,
                        "Rollover 12mo %": tenant_row[4] if tenant_row else None,
                        "Rollover 24mo %": tenant_row[5] if tenant_row else None,
                        "Rollover 36mo %": tenant_row[6] if tenant_row else None,
                        "Occupancy %": tenant_row[7] if tenant_row else None,
                        "Investment Grade %": tenant_row[8] if tenant_row else None
                    }
                ])
                tenant_df.to_excel(writer, sheet_name="Tenant Risk", index=False)

                collections_df = pd.DataFrame([
                    {
                        "DSO": collections_row[0] if collections_row else None,
                        "DSO Status": collections_row[1] if collections_row else None,
                        "Cash Conversion Ratio": collections_row[2] if collections_row else None,
                        "Revenue Quality Score": collections_row[3] if collections_row else None,
                        "Overall Status": collections_row[4] if collections_row else None
                    }
                ])
                collections_df.to_excel(writer, sheet_name="Collections Quality", index=False)

                completeness_df = pd.DataFrame([
                    {
                        "Balance Sheet": completeness_row[0] if completeness_row else None,
                        "Income Statement": completeness_row[1] if completeness_row else None,
                        "Cash Flow Statement": completeness_row[2] if completeness_row else None,
                        "Rent Roll": completeness_row[3] if completeness_row else None,
                        "Mortgage Statement": completeness_row[4] if completeness_row else None,
                        "Completeness %": completeness_row[5] if completeness_row else None
                    }
                ])
                completeness_df.to_excel(writer, sheet_name="Document Completeness", index=False)

                validation_df = pd.DataFrame([
                    {
                        "Total Checks": validation_row[0] if validation_row else 0,
                        "Passed": validation_row[1] if validation_row else 0,
                        "Failed": validation_row[2] if validation_row else 0,
                        "Critical Failures": validation_row[3] if validation_row else 0
                    }
                ])
                validation_df.to_excel(writer, sheet_name="Math Integrity", index=False)

            output.seek(0)
            filename = f"{file_base}.xlsx".replace(" ", "_")
            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, title="Forensic Audit Report")
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Forensic Audit Report", styles["Title"]))
        story.append(Paragraph(f"Property: {property_row[1]} ({property_row[0]})", styles["Normal"]))
        story.append(Paragraph(f"Period: {period_label}", styles["Normal"]))
        story.append(Paragraph(f"Generated At: {scorecard.get('generated_at')}", styles["Normal"]))
        story.append(Spacer(1, 12))

        summary_table = Table([
            ["Overall Health Score", scorecard.get("overall_health_score")],
            ["Traffic Light Status", scorecard.get("traffic_light_status")],
            ["Audit Opinion", scorecard.get("audit_opinion")]
        ])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica")
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 12))

        financial_summary = scorecard.get("financial_summary") or {}
        financial_table = Table([
            ["Total Revenue", financial_summary.get("total_revenue", 0)],
            ["Net Income", financial_summary.get("net_income", 0)],
            ["NOI", financial_summary.get("noi", 0)],
            ["Cash Balance", financial_summary.get("cash_balance", 0)]
        ])
        financial_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica")
        ]))
        story.append(Paragraph("Financial Summary", styles["Heading2"]))
        story.append(financial_table)
        story.append(Spacer(1, 12))

        risks = scorecard.get("priority_risks") or []
        if risks:
            risk_rows = [["Severity", "Category", "Description", "Owner", "Due Date"]]
            for risk in risks:
                risk_rows.append([
                    risk.get("severity"),
                    risk.get("category"),
                    risk.get("description"),
                    risk.get("owner"),
                    risk.get("due_date") or ""
                ])
            risk_table = Table(risk_rows, repeatRows=1)
            risk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("VALIGN", (0, 0), (-1, -1), "TOP")
            ]))
            story.append(Paragraph("Priority Risks", styles["Heading2"]))
            story.append(risk_table)
            story.append(Spacer(1, 12))

        actions = scorecard.get("action_items") or []
        if actions:
            action_rows = [["Priority", "Description", "Owner", "Due Date", "Status"]]
            for item in actions:
                action_rows.append([
                    item.get("priority"),
                    item.get("description"),
                    item.get("assigned_to"),
                    item.get("due_date"),
                    item.get("status")
                ])
            action_table = Table(action_rows, repeatRows=1)
            action_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("VALIGN", (0, 0), (-1, -1), "TOP")
            ]))
            story.append(Paragraph("Action Items", styles["Heading2"]))
            story.append(action_table)
            story.append(Spacer(1, 12))

        if fraud_row:
            story.append(Paragraph("Fraud Detection Summary", styles["Heading2"]))
            fraud_table = Table([
                ["Overall Risk Level", fraud_row[0]],
                ["Benford Chi Square", fraud_row[1]],
                ["Round Number %", fraud_row[2]],
                ["Duplicate Payments", fraud_row[3]],
                ["Cash Conversion Ratio", fraud_row[4]],
                ["Red Flags Found", fraud_row[5]]
            ])
            fraud_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica")
            ]))
            story.append(fraud_table)
            story.append(Spacer(1, 12))

        if covenant_row:
            story.append(Paragraph("Covenant Compliance", styles["Heading2"]))
            covenant_table = Table([
                ["DSCR", covenant_row[0], "Status", covenant_row[1]],
                ["LTV", covenant_row[3], "Status", covenant_row[4]],
                ["Interest Coverage", covenant_row[6], "", ""],
                ["Current Ratio", covenant_row[7], "Quick Ratio", covenant_row[8]]
            ])
            covenant_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica")
            ]))
            story.append(covenant_table)
            story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)
        filename = f"{file_base}.pdf".replace(" ", "_")
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export audit report: {str(e)}"
        )


@router.get("/audit-history/{property_id}",
            response_model=List[AuditHistoryItem],
            summary="Get Audit History for Trend Analysis")
def get_audit_history(
    property_id: int,
    limit: int = Query(12, ge=1, le=60, description="Number of periods to return"),
    db: Session = Depends(get_db)
):
    """
    Get historical audit scorecards for trend analysis.

    Returns up to 60 periods of historical data including:

    - Overall health scores over time
    - DSCR trends
    - Occupancy rate trends
    - Critical issues count by period
    - Audit opinion history

    Perfect for board presentations and management reporting.
    """

    try:
        query = text("""
            SELECT
                a.period_id,
                CONCAT(fp.period_year, '-', LPAD(CAST(fp.period_month AS TEXT), 2, '0')) as period_label,
                a.created_at as audit_date,
                a.overall_health_score,
                a.traffic_light_status,
                a.audit_opinion,
                cc.dscr,
                COALESCE(rr.occupancy_rate, 0) as occupancy_rate,
                a.critical_issues_count
            FROM audit_scorecard_summary a
            JOIN financial_periods fp ON fp.id = a.period_id
            LEFT JOIN covenant_compliance_tracking cc ON cc.period_id = a.period_id
            LEFT JOIN (
                SELECT period_id,
                       MAX(occupancy_rate) as occupancy_rate
                FROM tenant_risk_analysis
                GROUP BY period_id
            ) rr ON rr.period_id = a.period_id
            WHERE a.property_id = :property_id
            ORDER BY fp.period_year DESC, fp.period_month DESC
            LIMIT :limit
        """)

        result = db.execute(
            query,
            {"property_id": str(property_id), "limit": limit}
        )
        rows = result.fetchall()

        history = []
        for row in rows:
            traffic_status = row[4] if row[4] in ["GREEN", "YELLOW", "RED"] else "YELLOW"
            opinion = row[5] if row[5] in ["UNQUALIFIED", "QUALIFIED", "ADVERSE"] else "QUALIFIED"

            history.append(AuditHistoryItem(
                period_id=row[0],
                period_label=row[1],
                audit_date=row[2],
                overall_health_score=row[3] or 0,
                traffic_light_status=TrafficLightStatus(traffic_status),
                audit_opinion=AuditOpinion(opinion),
                dscr=float(row[6]) if row[6] is not None else None,
                occupancy_rate=float(row[7]) if row[7] is not None else None,
                critical_issues=row[8] or 0
            ))

        return history

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit history: {str(e)}"
        )


@router.get("/audit-status/{task_id}", summary="Check Audit Task Status")
def get_audit_task_status(
    task_id: str
):
    """
    Check status of a background audit task.

    Returns:
    - **QUEUED** - Task is waiting to start
    - **IN_PROGRESS** - Audit is running (includes progress percentage)
    - **COMPLETED** - Audit finished successfully
    - **FAILED** - Audit encountered an error

    Use this endpoint to poll for completion after calling `/run-audit`.
    """
    task = AsyncResult(task_id, app=celery_app)

    if task.state == 'PENDING':
        return {
            "task_id": task_id,
            "state": task.state,
            "current_phase": "Waiting",
            "progress": 0,
            "message": "Task is queued and waiting to start"
        }
    if task.state == 'PROGRESS':
        info = task.info or {}
        return {
            "task_id": task_id,
            "state": task.state,
            "current_phase": info.get("current_phase", "Unknown"),
            "phase_number": info.get("phase_number", 0),
            "progress": info.get("progress", 0),
            "message": info.get("message", "Processing...")
        }
    if task.state == 'SUCCESS':
        info = task.info or {}
        return {
            "task_id": task_id,
            "state": task.state,
            "current_phase": "Complete",
            "progress": 100,
            "message": "Audit completed successfully",
            "results": info.get("results", {})
        }
    if task.state == 'FAILURE':
        info = task.info or {}
        return {
            "task_id": task_id,
            "state": task.state,
            "current_phase": "Error",
            "progress": 0,
            "message": info.get("message", "Audit failed"),
            "error": str(info) if info else "Unknown error"
        }

    return {
        "task_id": task_id,
        "state": task.state,
        "current_phase": "Unknown",
        "progress": 0,
        "message": f"Task in state: {task.state}"
    }
