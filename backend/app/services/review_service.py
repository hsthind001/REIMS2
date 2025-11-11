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

from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.rent_roll_data import RentRollData
from app.models.audit_trail import AuditTrail
from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload


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
    
    def get_review_queue(
        self,
        property_code: Optional[str] = None,
        document_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all records needing review across all financial tables
        
        Args:
            property_code: Filter by property code (optional)
            document_type: Filter by document type (optional)
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
            ).filter(
                model.needs_review == True
            )
            
            # Apply property filter
            if property_code:
                query = query.filter(Property.property_code == property_code)
            
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
            "audit_trail_id": audit_entry.id
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
            "metrics_recalculated": False
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

