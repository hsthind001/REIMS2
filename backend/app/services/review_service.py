"""
ReviewService - Data Review and Correction Workflow

Handles approval and correction of extracted financial data
with full audit trail tracking and smart metrics recalculation
"""
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import logging

from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.audit_trail import AuditTrail
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.models.review_approval_chain import ReviewApprovalChain, ApprovalStatus
from app.services.anomaly_impact_calculator import AnomalyImpactCalculator
from app.services.dscr_monitoring_service import DSCRMonitoringService
from functools import wraps

logger = logging.getLogger(__name__)


# Map table names to SQLAlchemy models
TABLE_MODEL_MAP = {
    "balance_sheet_data": BalanceSheetData,
    "income_statement_data": IncomeStatementData,
    "cash_flow_data": CashFlowData,
    "rent_roll_data": RentRollData,
}

# Define which tables trigger which metric recalculations
TABLE_METRIC_DEPENDENCIES = {
    "balance_sheet_data": ["balance_sheet"],
    "income_statement_data": ["income_statement", "performance"],
    "cash_flow_data": ["cash_flow"],
    "rent_roll_data": ["rent_roll", "performance"],
}


class ReviewService:
    """
    Service for reviewing and correcting extracted financial data
    
    Features:
    - Query review queue across all financial tables
    - Approve records (mark as reviewed)
    - Correct field values with validation
    - Track all changes in audit_trail
    - Smart metrics recalculation based on table
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.impact_calculator = AnomalyImpactCalculator(db)
        self.high_risk_threshold = Decimal('10000')  # $10,000 variance threshold
    
    def get_review_queue(
        self,
        property_code: Optional[str] = None,
        document_type: Optional[str] = None,
        severity: Optional[str] = None,
        period_year: Optional[int] = None,
        period_month: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all records needing review across all financial tables

        Args:
            property_code: Filter by property code (optional)
            document_type: Filter by document type (optional)
            severity: Filter by severity - 'critical' (<85%), 'warning' (85-95%), or 'all' (optional)
            period_year: Filter by fiscal year (optional)
            period_month: Filter by fiscal month (optional, requires year)
            skip: Pagination offset
            limit: Maximum records to return

        Returns:
            Dict with review queue items and counts
        """
        review_items = []
        total_count = 0

        # Query each financial table
        for table_name, model in TABLE_MODEL_MAP.items():
            query = self.db.query(
                model,
                Property.property_code,
                Property.property_name,
                FinancialPeriod.period_year,
                FinancialPeriod.period_month,
                DocumentUpload.file_name
            ).join(
                Property, model.property_id == Property.id
            ).join(
                FinancialPeriod, model.period_id == FinancialPeriod.id
            ).join(
                DocumentUpload, model.upload_id == DocumentUpload.id
            )

            # Apply severity filter
            if severity == 'critical':
                # Critical: needs_review = True OR extraction_confidence < 85
                query = query.filter(
                    (model.needs_review == True) | (model.extraction_confidence < 85)
                )
            elif severity == 'warning':
                # Warning: extraction_confidence 85-95%
                query = query.filter(
                    model.extraction_confidence >= 85,
                    model.extraction_confidence < 95
                )
            else:
                # Default: only show items with needs_review = True
                query = query.filter(model.needs_review == True)
            
            # Apply property filter
            if property_code:
                query = query.filter(Property.property_code == property_code)
            
            # Apply period filter
            if period_year:
                query = query.filter(FinancialPeriod.period_year == period_year)
            if period_month:
                query = query.filter(FinancialPeriod.period_month == period_month)
            
            # Apply document type filter (map to table)
            if document_type:
                doc_table_map = {
                    "balance_sheet": "balance_sheet_data",
                    "income_statement": "income_statement_data",
                    "cash_flow": "cash_flow_data",
                    "rent_roll": "rent_roll_data",
                }
                if doc_table_map.get(document_type) != table_name:
                    continue
            
            # Get results
            results = query.all()
            total_count += len(results)
            
            for record, prop_code, prop_name, year, month, file_name in results:
                # Get primary key field
                mapper = inspect(model)
                pk_field = mapper.primary_key[0].name
                record_id = getattr(record, pk_field)
                
                # Build review item
                item = {
                    "record_id": record_id,
                    "table_name": table_name,
                    "property_code": prop_code,
                    "property_name": prop_name,
                    "period_year": year,
                    "period_month": month,
                    "file_name": file_name,
                    "account_code": getattr(record, "account_code", None),
                    "account_name": getattr(record, "account_name", None),
                    "unit_number": getattr(record, "unit_number", None),
                    "extraction_confidence": float(record.extraction_confidence) if record.extraction_confidence else None,
                    "match_confidence": float(getattr(record, "match_confidence")) if getattr(record, "match_confidence", None) is not None else None,
                    "needs_review": record.needs_review,
                    "reviewed": record.reviewed,
                    "created_at": record.created_at,
                }
                
                # Add relevant amount fields
                if hasattr(record, "amount"):
                    item["amount"] = float(record.amount) if record.amount else None
                if hasattr(record, "period_amount"):
                    item["period_amount"] = float(record.period_amount) if record.period_amount else None
                if hasattr(record, "monthly_rent"):
                    item["monthly_rent"] = float(record.monthly_rent) if record.monthly_rent else None
                
                # Generate human-readable review reason
                item["needs_review_reason"] = self._generate_review_reason(record)
                
                review_items.append(item)
        
        # Apply pagination
        paginated_items = review_items[skip:skip + limit]
        
        return {
            "items": paginated_items,
            "total": total_count,
            "skip": skip,
            "limit": limit,
            "has_more": total_count > (skip + limit)
        }
    
    def approve_record(
        self,
        record_id: int,
        table_name: str,
        user_id: int,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a record (mark as reviewed without changes)
        
        Supports dual approval for high-risk items.
        
        Args:
            record_id: Record ID
            table_name: Table name (balance_sheet_data, etc.)
            user_id: User performing the approval
            notes: Optional approval notes
        
        Returns:
            Success status and record info
        """
        # Validate table name
        if table_name not in TABLE_MODEL_MAP:
            raise ValueError(f"Invalid table name: {table_name}")
        
        model = TABLE_MODEL_MAP[table_name]
        
        # Get record
        record = self.db.query(model).filter(model.id == record_id).first()
        
        if not record:
            raise ValueError(f"Record {record_id} not found in {table_name}")
        
        # Check if high-risk (requires dual approval)
        requires_dual_approval = self._requires_dual_approval(record, table_name)
        
        if requires_dual_approval:
            return self._handle_dual_approval(record_id, table_name, user_id, notes, record)
        
        # Single approval for low-risk items
        # Already reviewed?
        if record.reviewed:
            return {
                "success": True,
                "message": "Record already reviewed",
                "record_id": record_id,
                "table_name": table_name,
                "already_reviewed": True
            }
        
        # Mark as reviewed
        record.needs_review = False
        record.reviewed = True
        record.reviewed_by = user_id
        record.reviewed_at = datetime.utcnow()
        if notes:
            record.review_notes = notes
        
        # Create audit trail entry
        audit_entry = AuditTrail(
            table_name=table_name,
            record_id=record_id,
            action="approve",
            changed_by=user_id,
            reason=notes or "Record approved without changes"
        )
        self.db.add(audit_entry)
        
        # Commit
        self.db.commit()
        self.db.refresh(record)
        
        return {
            "success": True,
            "message": "Record approved",
            "record_id": record_id,
            "table_name": table_name,
            "reviewed_at": record.reviewed_at,
            "audit_trail_id": audit_entry.id,
            "dual_approval_required": False
        }
    
    def correct_record(
        self,
        record_id: int,
        table_name: str,
        corrections: Dict[str, Any],
        user_id: int,
        notes: Optional[str] = None,
        recalculate_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        Correct field values in a record and mark as reviewed
        
        Supports dual approval for high-risk corrections.
        
        Args:
            record_id: Record ID
            table_name: Table name
            corrections: Dict of field_name: new_value
            user_id: User making the correction
            notes: Correction notes
            recalculate_metrics: Whether to trigger metrics recalculation
        
        Returns:
            Success status, old values, new values, audit trail ID
        """
        # Validate table name
        if table_name not in TABLE_MODEL_MAP:
            raise ValueError(f"Invalid table name: {table_name}")
        
        model = TABLE_MODEL_MAP[table_name]
        
        # Get record
        record = self.db.query(model).filter(model.id == record_id).first()
        
        if not record:
            raise ValueError(f"Record {record_id} not found in {table_name}")
        
        # Capture old values
        old_values = {}
        changed_fields = []
        
        for field_name, new_value in corrections.items():
            if not hasattr(record, field_name):
                raise ValueError(f"Field '{field_name}' does not exist in {table_name}")
            
            old_value = getattr(record, field_name)
            old_values[field_name] = old_value
            
            # Skip if no change
            if old_value == new_value:
                continue
            
            # Validate and convert numeric fields
            if isinstance(new_value, (int, float, str)):
                # Get column type
                mapper = inspect(model)
                column = mapper.columns.get(field_name)
                
                if column is not None:
                    # Handle Decimal columns
                    if str(column.type).startswith('DECIMAL'):
                        new_value = Decimal(str(new_value))
            
            # Update field
            setattr(record, field_name, new_value)
            changed_fields.append(field_name)
        
        # If no changes, just approve
        if not changed_fields:
            return self.approve_record(record_id, table_name, user_id, notes)
        
        # Calculate impact to determine if dual approval needed
        impact = self._calculate_correction_impact(old_values, corrections, record)
        requires_dual_approval = impact.get('requires_dual_approval', False)
        
        if requires_dual_approval:
            # Use dual approval workflow for corrections
            return self._handle_dual_approval_correction(
                record_id, table_name, corrections, old_values, changed_fields,
                user_id, notes, record, recalculate_metrics
            )
        
        # Single approval for low-impact corrections
        # Mark as reviewed
        record.needs_review = False
        record.reviewed = True
        record.reviewed_by = user_id
        record.reviewed_at = datetime.utcnow()
        if notes:
            record.review_notes = notes
        
        # Create audit trail entry
        audit_entry = AuditTrail(
            table_name=table_name,
            record_id=record_id,
            action="correct",
            old_values=old_values,
            new_values=corrections,
            changed_fields=changed_fields,
            changed_by=user_id,
            reason=notes or f"Corrected {len(changed_fields)} field(s)"
        )
        self.db.add(audit_entry)
        
        # Commit changes
        self.db.commit()
        self.db.refresh(record)
        
        result = {
            "success": True,
            "message": f"Corrected {len(changed_fields)} field(s)",
            "record_id": record_id,
            "table_name": table_name,
            "changed_fields": changed_fields,
            "old_values": old_values,
            "new_values": corrections,
            "reviewed_at": record.reviewed_at,
            "audit_trail_id": audit_entry.id,
            "metrics_recalculated": False,
            "dual_approval_required": False
        }
        
        # Trigger metrics recalculation if needed
        if recalculate_metrics and changed_fields:
            try:
                metrics_result = self._recalculate_metrics(
                    property_id=record.property_id,
                    period_id=record.period_id,
                    table_name=table_name
                )
                result["metrics_recalculated"] = metrics_result.get("success", False)
                result["metrics_calculated"] = metrics_result.get("metrics_count", 0)
            except Exception as e:
                result["metrics_error"] = str(e)
        
        return result
    
    def _calculate_correction_impact(
        self,
        old_values: Dict[str, Any],
        corrections: Dict[str, Any],
        record: Any
    ) -> Dict[str, Any]:
        """
        Calculate financial impact of corrections.
        
        Determines:
        - Total variance amount
        - Whether dual approval is required
        - If corrections affect DSCR
        - If corrections affect covenant compliance
        """
        total_variance = Decimal('0')
        is_dscr_affecting = False
        is_covenant_impacting = False
        
        # Calculate total variance
        for field_name, new_value in corrections.items():
            old_value = old_values.get(field_name)
            if old_value and new_value:
                try:
                    variance = abs(Decimal(str(new_value)) - Decimal(str(old_value)))
                    total_variance += variance
                except (ValueError, TypeError):
                    pass
        
        # Check if exceeds threshold
        requires_dual_approval = total_variance > self.high_risk_threshold
        
        # Check for DSCR and covenant impact
        try:
            # Get property and period from record
            property_id = getattr(record, 'property_id', None)
            period_id = getattr(record, 'period_id', None)
            
            if property_id and period_id:
                # Check if corrections affect DSCR-related accounts
                dscr_affecting_accounts = self._get_dscr_affecting_accounts(record)
                covenant_affecting_accounts = self._get_covenant_affecting_accounts(record)
                
                # Check if any corrected field affects DSCR
                for field_name in corrections.keys():
                    if field_name in dscr_affecting_accounts:
                        is_dscr_affecting = True
                        break
                
                # Check if any corrected field affects covenants
                for field_name in corrections.keys():
                    if field_name in covenant_affecting_accounts:
                        is_covenant_impacting = True
                        break
                
                # If DSCR-affecting, calculate actual DSCR impact
                if is_dscr_affecting:
                    dscr_impact = self._calculate_dscr_impact(
                        property_id, period_id, old_values, corrections, record
                    )
                    is_dscr_affecting = dscr_impact.get('affects_dscr', False)
                
                # If covenant-affecting, check threshold proximity
                if is_covenant_impacting:
                    covenant_impact = self._calculate_covenant_impact(
                        property_id, period_id, old_values, corrections, record
                    )
                    is_covenant_impacting = covenant_impact.get('affects_covenant', False)
        
        except Exception as e:
            logger.warning(f"Error calculating DSCR/covenant impact: {e}")
            # Default to safe values if calculation fails
            is_dscr_affecting = False
            is_covenant_impacting = False
        
        return {
            'total_variance': float(total_variance),
            'requires_dual_approval': requires_dual_approval,
            'is_covenant_impacting': is_covenant_impacting,
            'is_dscr_affecting': is_dscr_affecting
        }
    
    def _get_dscr_affecting_accounts(self, record: Any) -> List[str]:
        """
        Get list of field names that affect DSCR calculation.
        
        DSCR = NOI / Total Debt Service
        - NOI = Revenue (4xxx) - Operating Expenses (5xxx, 6xxx)
        - Debt Service = Mortgage Interest (7010-0000)
        """
        dscr_fields = []
        
        # Check if record has account_code attribute
        account_code = getattr(record, 'account_code', None)
        
        if account_code:
            # Revenue accounts (affect NOI numerator)
            if account_code.startswith('4'):
                dscr_fields.append('period_amount')  # Revenue amount
            # Operating expense accounts (affect NOI numerator)
            elif account_code.startswith('5') or account_code.startswith('6'):
                dscr_fields.append('period_amount')  # Expense amount
            # Mortgage interest (affects debt service denominator)
            elif account_code == '7010-0000' or 'mortgage' in str(account_code).lower():
                dscr_fields.append('period_amount')  # Debt service amount
        
        # Also check common field names
        if hasattr(record, 'net_operating_income'):
            dscr_fields.append('net_operating_income')
        if hasattr(record, 'total_debt_service'):
            dscr_fields.append('total_debt_service')
        
        return dscr_fields
    
    def _get_covenant_affecting_accounts(self, record: Any) -> List[str]:
        """
        Get list of field names that affect covenant compliance.
        
        Covenant-affecting accounts include:
        - DSCR-related accounts (already covered)
        - LTV-related accounts (loan balance, property value)
        - Occupancy-related accounts
        - Key financial ratios
        """
        covenant_fields = []
        
        # Get DSCR-affecting accounts (covenants often include DSCR requirements)
        covenant_fields.extend(self._get_dscr_affecting_accounts(record))
        
        account_code = getattr(record, 'account_code', None)
        
        if account_code:
            # Loan balance accounts (affect LTV covenant)
            if account_code.startswith('26') or account_code.startswith('24'):  # Debt accounts
                covenant_fields.append('period_amount')
            # Property value accounts
            if account_code.startswith('1') and 'value' in str(account_code).lower():
                covenant_fields.append('period_amount')
        
        # Common covenant-related fields
        covenant_related_fields = [
            'loan_balance', 'property_value', 'occupancy_rate',
            'debt_to_equity', 'current_ratio', 'debt_service_coverage_ratio'
        ]
        
        for field in covenant_related_fields:
            if hasattr(record, field):
                covenant_fields.append(field)
        
        return covenant_fields
    
    def _calculate_dscr_impact(
        self,
        property_id: int,
        period_id: int,
        old_values: Dict[str, Any],
        corrections: Dict[str, Any],
        record: Any
    ) -> Dict[str, Any]:
        """
        Calculate if corrections would affect DSCR and cross thresholds.
        
        Returns:
            Dict with 'affects_dscr' boolean and impact details
        """
        try:
            dscr_service = DSCRMonitoringService(self.db)
            
            # Calculate current DSCR
            current_dscr_result = dscr_service.calculate_dscr(property_id, period_id)
            
            if not current_dscr_result.get('success'):
                return {'affects_dscr': False, 'reason': 'Could not calculate current DSCR'}
            
            current_dscr = Decimal(str(current_dscr_result.get('dscr', 0)))
            threshold = DSCRMonitoringService.CRITICAL_THRESHOLD  # 1.25
            
            # Check if current DSCR is near threshold (within 10% buffer)
            threshold_buffer = threshold * Decimal('0.10')  # 10% buffer
            near_threshold = abs(current_dscr - threshold) <= threshold_buffer
            
            # Calculate impact of corrections
            # For simplicity, if corrections affect NOI or debt service accounts,
            # and we're near threshold, consider it DSCR-affecting
            account_code = getattr(record, 'account_code', None)
            is_noi_affecting = account_code and (
                account_code.startswith('4') or  # Revenue
                account_code.startswith('5') or  # Operating expenses
                account_code.startswith('6')     # Additional operating expenses
            )
            is_debt_service_affecting = account_code and (
                account_code == '7010-0000' or 'mortgage' in str(account_code).lower()
            )
            
            # Calculate variance impact
            total_variance = Decimal('0')
            for field_name, new_value in corrections.items():
                old_value = old_values.get(field_name)
                if old_value and new_value:
                    try:
                        variance = abs(Decimal(str(new_value)) - Decimal(str(old_value)))
                        total_variance += variance
                    except (ValueError, TypeError):
                        pass
            
            # Significant variance (>$10,000) on DSCR-affecting accounts
            significant_variance = total_variance > Decimal('10000')
            
            affects_dscr = (
                (is_noi_affecting or is_debt_service_affecting) and
                (near_threshold or significant_variance)
            )
            
            return {
                'affects_dscr': affects_dscr,
                'current_dscr': float(current_dscr),
                'threshold': float(threshold),
                'near_threshold': near_threshold,
                'variance': float(total_variance),
                'significant_variance': significant_variance
            }
        
        except Exception as e:
            logger.error(f"Error calculating DSCR impact: {e}", exc_info=True)
            return {'affects_dscr': False, 'error': str(e)}
    
    def _calculate_covenant_impact(
        self,
        property_id: int,
        period_id: int,
        old_values: Dict[str, Any],
        corrections: Dict[str, Any],
        record: Any
    ) -> Dict[str, Any]:
        """
        Calculate if corrections would affect covenant compliance.
        
        Covenants typically include:
        - DSCR requirements
        - LTV (Loan-to-Value) requirements
        - Occupancy requirements
        - Debt service requirements
        """
        try:
            # DSCR is a common covenant, so check that first
            dscr_impact = self._calculate_dscr_impact(property_id, period_id, old_values, corrections, record)
            
            if dscr_impact.get('affects_dscr'):
                return {
                    'affects_covenant': True,
                    'covenant_type': 'DSCR',
                    'details': dscr_impact
                }
            
            # Check for other covenant types
            account_code = getattr(record, 'account_code', None)
            
            # LTV-related (loan balance or property value changes)
            is_ltv_affecting = account_code and (
                account_code.startswith('26') or  # Debt accounts
                (account_code.startswith('1') and 'value' in str(account_code).lower())
            )
            
            # Occupancy-related
            is_occupancy_affecting = account_code and (
                'occupancy' in str(account_code).lower() or
                'rent' in str(account_code).lower()
            )
            
            # Calculate variance
            total_variance = Decimal('0')
            for field_name, new_value in corrections.items():
                old_value = old_values.get(field_name)
                if old_value and new_value:
                    try:
                        variance = abs(Decimal(str(new_value)) - Decimal(str(old_value)))
                        total_variance += variance
                    except (ValueError, TypeError):
                        pass
            
            # Significant variance on covenant-related accounts
            significant_variance = total_variance > Decimal('10000')
            
            affects_covenant = (
                (is_ltv_affecting or is_occupancy_affecting) and
                significant_variance
            )
            
            return {
                'affects_covenant': affects_covenant,
                'covenant_types': {
                    'ltv': is_ltv_affecting,
                    'occupancy': is_occupancy_affecting,
                    'dscr': dscr_impact.get('affects_dscr', False)
                },
                'variance': float(total_variance)
            }
        
        except Exception as e:
            logger.error(f"Error calculating covenant impact: {e}", exc_info=True)
            return {'affects_covenant': False, 'error': str(e)}
    
    def _handle_dual_approval_correction(
        self,
        record_id: int,
        table_name: str,
        corrections: Dict[str, Any],
        old_values: Dict[str, Any],
        changed_fields: List[str],
        user_id: int,
        notes: Optional[str],
        record: Any,
        recalculate_metrics: bool
    ) -> Dict[str, Any]:
        """Handle dual approval for high-risk corrections."""
        # Similar to _handle_dual_approval but for corrections
        # Store corrections temporarily until second approval
        
        approval_chain = self.db.query(ReviewApprovalChain).filter(
            ReviewApprovalChain.table_name == table_name,
            ReviewApprovalChain.record_id == record_id
        ).first()
        
        if not approval_chain:
            approval_chain = ReviewApprovalChain(
                table_name=table_name,
                record_id=record_id,
                status=ApprovalStatus.PENDING
            )
            self.db.add(approval_chain)
        
        # Store pending corrections in metadata (would use JSONB field)
        # For now, create audit trail entry for first approval
        if approval_chain.status == ApprovalStatus.PENDING:
            approval_chain.first_approver_id = user_id
            approval_chain.first_approved_at = datetime.utcnow()
            approval_chain.first_approval_notes = notes or f"First approval for correction: {', '.join(changed_fields)}"
            approval_chain.status = ApprovalStatus.FIRST_APPROVED
            
            # Store corrections in audit trail (pending)
            audit_entry = AuditTrail(
                table_name=table_name,
                record_id=record_id,
                action="correct_pending",
                old_values=old_values,
                new_values=corrections,
                changed_fields=changed_fields,
                changed_by=user_id,
                reason=notes or f"Correction pending second approval: {', '.join(changed_fields)}"
            )
            self.db.add(audit_entry)
            self.db.commit()
            
            return {
                "success": True,
                "message": "Correction submitted. Second approval required.",
                "approval_chain_id": approval_chain.id,
                "status": "pending_second_approval",
                "requires_second_approval": True,
                "changed_fields": changed_fields,
                "audit_trail_id": audit_entry.id
            }
        
        elif approval_chain.status == ApprovalStatus.FIRST_APPROVED:
            if approval_chain.first_approver_id == user_id:
                return {
                    "success": False,
                    "message": "Cannot provide both approvals. Different user required."
                }
            
            # Apply corrections
            for field_name, new_value in corrections.items():
                if isinstance(new_value, (int, float, str)):
                    mapper = inspect(type(record))
                    column = mapper.columns.get(field_name)
                    if column and str(column.type).startswith('DECIMAL'):
                        new_value = Decimal(str(new_value))
                setattr(record, field_name, new_value)
            
            # Mark as reviewed
            record.needs_review = False
            record.reviewed = True
            record.reviewed_by = user_id
            record.reviewed_at = datetime.utcnow()
            
            # Complete approval chain
            approval_chain.second_approver_id = user_id
            approval_chain.second_approved_at = datetime.utcnow()
            approval_chain.second_approval_notes = notes or "Second approval - corrections applied"
            approval_chain.status = ApprovalStatus.SECOND_APPROVED
            
            # Create final audit trail
            audit_entry = AuditTrail(
                table_name=table_name,
                record_id=record_id,
                action="correct",
                old_values=old_values,
                new_values=corrections,
                changed_fields=changed_fields,
                changed_by=user_id,
                reason=notes or f"Correction approved and applied: {', '.join(changed_fields)}"
            )
            self.db.add(audit_entry)
            self.db.commit()
            
            result = {
                "success": True,
                "message": "Dual approval completed. Corrections applied.",
                "approval_chain_id": approval_chain.id,
                "status": "fully_approved",
                "changed_fields": changed_fields,
                "reviewed_at": record.reviewed_at,
                "audit_trail_id": audit_entry.id,
                "metrics_recalculated": False
            }
            
            # Recalculate metrics
            if recalculate_metrics:
                try:
                    metrics_result = self._recalculate_metrics(
                        property_id=record.property_id,
                        period_id=record.period_id,
                        table_name=table_name
                    )
                    result["metrics_recalculated"] = metrics_result.get("success", False)
                except Exception as e:
                    result["metrics_error"] = str(e)
            
            return result
        
        return {
            "success": False,
            "message": f"Invalid approval status: {approval_chain.status}"
        }
    
    def _recalculate_metrics(
        self,
        property_id: int,
        period_id: int,
        table_name: str
    ) -> Dict[str, Any]:
        """
        Smart metrics recalculation based on which table was corrected
        
        Args:
            property_id: Property ID
            period_id: Financial Period ID
            table_name: Table that was corrected
        
        Returns:
            Metrics recalculation result
        """
        from app.services.metrics_service import MetricsService
        
        # Get which metrics to recalculate
        metrics_to_calc = TABLE_METRIC_DEPENDENCIES.get(table_name, [])
        
        if not metrics_to_calc:
            return {"success": False, "message": "No metrics to recalculate"}
        
        # Recalculate all metrics (simplest approach - always correct)
        metrics_service = MetricsService(self.db)
        metrics = metrics_service.calculate_all_metrics(property_id, period_id)
        
        # Count non-null metrics
        metrics_count = 0
        for attr in dir(metrics):
            if not attr.startswith('_') and hasattr(metrics, attr):
                value = getattr(metrics, attr)
                if value is not None and attr not in ['id', 'property_id', 'period_id', 'calculated_at', 'created_at', 'updated_at']:
                    metrics_count += 1
        
        return {
            "success": True,
            "metrics_count": metrics_count,
            "affected_categories": metrics_to_calc
        }
    
    def _generate_review_reason(self, record: Any) -> str:
        """
        Generate a human-readable explanation for why a record needs review
        
        Args:
            record: The financial data record
        
        Returns:
            Clear, actionable one-line description
        """
        account_code = getattr(record, "account_code", None)
        account_name = getattr(record, "account_name", None)
        extraction_conf = float(record.extraction_confidence) if record.extraction_confidence else 0.0
        account_id = getattr(record, "account_id", None)
        
        # Check for UNMATCHED accounts (most common issue)
        if account_code == "UNMATCHED" or account_id is None:
            if account_name:
                return f"Account '{account_name}' not found in Chart of Accounts - needs manual mapping or creation"
            else:
                return "Account not matched - missing account name or code"
        
        # Check for low extraction confidence
        if extraction_conf < 75:
            return f"Low PDF extraction quality ({extraction_conf:.0f}%) - manual verification recommended"
        
        # Check for moderate extraction confidence
        if extraction_conf < 85:
            return f"Moderate extraction confidence ({extraction_conf:.0f}%) - please verify amounts and account details"
        
        # Check for low match confidence (matched but uncertain)
        if extraction_conf < 95:
            return "Account matched with moderate confidence - verify mapping is correct"
        
        # Default (shouldn't usually reach here if needs_review is True)
        return "Flagged for review - please verify all details are correct"
    
    def get_record_details(
        self,
        record_id: int,
        table_name: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a record
        
        Args:
            record_id: Record ID
            table_name: Table name
        
        Returns:
            Record details with related information
        """
        if table_name not in TABLE_MODEL_MAP:
            raise ValueError(f"Invalid table name: {table_name}")
        
        model = TABLE_MODEL_MAP[table_name]
        
        # Query with joins
        result = self.db.query(
            model,
            Property.property_code,
            Property.property_name,
            FinancialPeriod.period_year,
            FinancialPeriod.period_month
        ).join(
            Property, model.property_id == Property.id
        ).join(
            FinancialPeriod, model.period_id == FinancialPeriod.id
        ).filter(
            model.id == record_id
        ).first()
        
        if not result:
            raise ValueError(f"Record {record_id} not found in {table_name}")
        
        record, prop_code, prop_name, year, month = result
        
        # Convert record to dict
        record_dict = {
            "record_id": record_id,
            "table_name": table_name,
            "property_code": prop_code,
            "property_name": prop_name,
            "period_year": year,
            "period_month": month,
            "needs_review": record.needs_review,
            "reviewed": record.reviewed,
            "reviewed_by": record.reviewed_by,
            "reviewed_at": record.reviewed_at,
            "review_notes": record.review_notes,
            "extraction_confidence": float(record.extraction_confidence) if record.extraction_confidence else None,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
        
        # Add all model fields
        mapper = inspect(model)
        for column in mapper.columns:
            field_name = column.name
            if field_name not in record_dict:
                value = getattr(record, field_name)
                # Convert Decimal to float for JSON serialization
                if isinstance(value, Decimal):
                    value = float(value)
                record_dict[field_name] = value
        
        return record_dict
