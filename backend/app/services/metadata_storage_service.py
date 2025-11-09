from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from app.models.extraction_field_metadata import ExtractionFieldMetadata
from app.utils.engines.base_extractor import ExtractionResult
from app.services.confidence_engine import ConfidenceEngine


class MetadataStorageService:
    """
    Service to save extraction metadata to the database after extraction completes.
    
    Handles multiple engine results, flags low-confidence fields automatically,
    and ensures transaction integrity with rollback on error.
    """
    
    def __init__(self, db_session: Session, confidence_engine: Optional[ConfidenceEngine] = None):
        """
        Initialize the Metadata Storage Service.
        
        Args:
            db_session: SQLAlchemy database session
            confidence_engine: Optional ConfidenceEngine instance (creates default if not provided)
        """
        self.db_session = db_session
        self.confidence_engine = confidence_engine or ConfidenceEngine()
        self.confidence_threshold_low = Decimal('0.70')  # Below this = needs review
        self.confidence_threshold_critical = Decimal('0.50')  # Below this = critical review
    
    def save_field_metadata(
        self,
        document_id: int,
        table_name: str,
        record_id: int,
        field_name: str,
        extraction_results: List[ExtractionResult],
        field_values: List[Any]
    ) -> ExtractionFieldMetadata:
        """
        Save metadata for a single field from multiple extraction engines.
        
        Args:
            document_id: ID of the document
            table_name: Name of the database table (e.g., 'balance_sheet_data')
            record_id: ID of the record in that table
            field_name: Name of the field
            extraction_results: List of ExtractionResult objects
            field_values: Values extracted by each engine (same order)
        
        Returns:
            Created ExtractionFieldMetadata object
        
        Raises:
            SQLAlchemyError: If database operation fails
        """
        # Calculate aggregate confidence
        confidence, resolution_method, conflicting_values = \
            self.confidence_engine.calculate_field_confidence(
                extraction_results,
                field_name,
                field_values
            )
        
        # Determine which engine to credit
        # Use highest confidence engine or consensus
        if conflicting_values:
            best_value, best_conf, best_engine = \
                self.confidence_engine.get_best_value_from_conflict(conflicting_values)
            extraction_engine = best_engine
        else:
            # Get engine with highest confidence
            best_result = max(extraction_results, key=lambda r: r.confidence_score)
            extraction_engine = best_result.engine_name
        
        # Determine if review needed
        needs_review, review_priority, flagged_reason = \
            self.confidence_engine.should_flag_for_review(
                confidence,
                conflicting_values is not None,
                [w for r in extraction_results for w in r.warnings]
            )
        
        # Create metadata record
        metadata = ExtractionFieldMetadata(
            document_id=document_id,
            table_name=table_name,
            record_id=record_id,
            field_name=field_name,
            confidence_score=confidence,
            extraction_engine=extraction_engine,
            conflicting_values=conflicting_values if conflicting_values else None,
            resolution_method=resolution_method,
            needs_review=needs_review,
            review_priority=review_priority,
            flagged_reason=flagged_reason
        )
        
        # Add to session (not committed yet)
        self.db_session.add(metadata)
        
        return metadata
    
    def save_document_metadata(
        self,
        document_id: int,
        field_metadata_list: List[Dict[str, Any]]
    ) -> List[ExtractionFieldMetadata]:
        """
        Save metadata for all fields in a document.
        
        Args:
            document_id: ID of the document
            field_metadata_list: List of dicts with field metadata info
                Each dict should have: table_name, record_id, field_name,
                extraction_results, field_values
        
        Returns:
            List of created ExtractionFieldMetadata objects
        
        Raises:
            SQLAlchemyError: If database operation fails (will trigger rollback)
        """
        created_metadata = []
        
        try:
            for field_info in field_metadata_list:
                metadata = self.save_field_metadata(
                    document_id=document_id,
                    table_name=field_info['table_name'],
                    record_id=field_info['record_id'],
                    field_name=field_info['field_name'],
                    extraction_results=field_info['extraction_results'],
                    field_values=field_info['field_values']
                )
                created_metadata.append(metadata)
            
            # Commit all metadata at once
            self.db_session.commit()
            
            return created_metadata
        
        except SQLAlchemyError as e:
            # Rollback on any error
            self.db_session.rollback()
            raise e
    
    def save_extraction_result_metadata(
        self,
        document_id: int,
        extraction_results: List[ExtractionResult],
        extracted_records: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Save metadata for entire extraction result.
        
        Args:
            document_id: ID of the document
            extraction_results: List of ExtractionResult from all engines
            extracted_records: Dict mapping table names to lists of records
                Example: {
                    'balance_sheet_data': [
                        {'id': 1, 'account_name': 'Cash', 'amount': 1000, ...},
                        ...
                    ]
                }
        
        Returns:
            Dict with summary statistics
        """
        total_fields = 0
        flagged_fields = 0
        critical_fields = 0
        
        try:
            for table_name, records in extracted_records.items():
                for record in records:
                    record_id = record.get('id')
                    if not record_id:
                        continue
                    
                    # Save metadata for each field in the record
                    for field_name, value in record.items():
                        if field_name == 'id':
                            continue
                        
                        # Get field values from all engines
                        # Note: In real implementation, this would extract field-specific
                        # values from each engine's result. For now, we use a simplified approach.
                        field_values = [value] * len(extraction_results)  # Simplified
                        
                        metadata = self.save_field_metadata(
                            document_id=document_id,
                            table_name=table_name,
                            record_id=record_id,
                            field_name=field_name,
                            extraction_results=extraction_results,
                            field_values=field_values
                        )
                        
                        total_fields += 1
                        
                        if metadata.needs_review:
                            flagged_fields += 1
                            if metadata.review_priority == 'critical':
                                critical_fields += 1
            
            # Commit all metadata
            self.db_session.commit()
            
            return {
                "success": True,
                "total_fields": total_fields,
                "flagged_for_review": flagged_fields,
                "critical_fields": critical_fields,
                "review_percentage": (flagged_fields / total_fields * 100) if total_fields > 0 else 0
            }
        
        except SQLAlchemyError as e:
            # Rollback on error
            self.db_session.rollback()
            return {
                "success": False,
                "error": str(e),
                "total_fields": total_fields,
                "error_message": "Failed to save metadata - transaction rolled back"
            }
    
    def flag_low_confidence_fields(
        self,
        document_id: int,
        threshold: Optional[Decimal] = None
    ) -> int:
        """
        Automatically flag fields with confidence below threshold.
        
        This can be run after initial metadata save to update flags.
        
        Args:
            document_id: ID of the document
            threshold: Confidence threshold (default: 0.70)
        
        Returns:
            Number of fields flagged
        """
        if threshold is None:
            threshold = self.confidence_threshold_low
        
        try:
            # Query fields below threshold
            low_conf_fields = self.db_session.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.document_id == document_id,
                ExtractionFieldMetadata.confidence_score < threshold,
                ExtractionFieldMetadata.needs_review == False
            ).all()
            
            flagged_count = 0
            
            for field in low_conf_fields:
                field.needs_review = True
                
                # Determine priority based on confidence
                if field.confidence_score < self.confidence_threshold_critical:
                    field.review_priority = 'critical'
                    field.flagged_reason = f'Critical: Confidence {field.confidence_score:.2%} < 50%'
                else:
                    field.review_priority = 'high'
                    field.flagged_reason = f'Low confidence: {field.confidence_score:.2%} < 70%'
                
                flagged_count += 1
            
            self.db_session.commit()
            
            return flagged_count
        
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise e
    
    def get_review_statistics(self, document_id: int) -> Dict[str, Any]:
        """
        Get statistics on fields needing review for a document.
        
        Args:
            document_id: ID of the document
        
        Returns:
            Dict with review statistics
        """
        try:
            # Total fields
            total = self.db_session.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.document_id == document_id
            ).count()
            
            # Fields needing review
            review_needed = self.db_session.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.document_id == document_id,
                ExtractionFieldMetadata.needs_review == True
            ).count()
            
            # By priority
            critical = self.db_session.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.document_id == document_id,
                ExtractionFieldMetadata.review_priority == 'critical'
            ).count()
            
            high = self.db_session.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.document_id == document_id,
                ExtractionFieldMetadata.review_priority == 'high'
            ).count()
            
            medium = self.db_session.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.document_id == document_id,
                ExtractionFieldMetadata.review_priority == 'medium'
            ).count()
            
            low = self.db_session.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.document_id == document_id,
                ExtractionFieldMetadata.review_priority == 'low'
            ).count()
            
            # Fields with conflicts
            conflicts = self.db_session.query(ExtractionFieldMetadata).filter(
                ExtractionFieldMetadata.document_id == document_id,
                ExtractionFieldMetadata.conflicting_values.isnot(None)
            ).count()
            
            return {
                "total_fields": total,
                "needs_review": review_needed,
                "review_percentage": (review_needed / total * 100) if total > 0 else 0,
                "by_priority": {
                    "critical": critical,
                    "high": high,
                    "medium": medium,
                    "low": low
                },
                "fields_with_conflicts": conflicts
            }
        
        except SQLAlchemyError as e:
            return {
                "error": str(e)
            }
    
    def bulk_save_metadata(
        self,
        metadata_records: List[ExtractionFieldMetadata],
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """
        Save multiple metadata records in batches for better performance.
        
        Args:
            metadata_records: List of ExtractionFieldMetadata objects to save
            batch_size: Number of records per batch
        
        Returns:
            Dict with success status and statistics
        """
        total_saved = 0
        
        try:
            # Process in batches
            for i in range(0, len(metadata_records), batch_size):
                batch = metadata_records[i:i + batch_size]
                self.db_session.bulk_save_objects(batch)
                total_saved += len(batch)
            
            # Commit all batches
            self.db_session.commit()
            
            return {
                "success": True,
                "total_saved": total_saved,
                "batches": (len(metadata_records) + batch_size - 1) // batch_size
            }
        
        except SQLAlchemyError as e:
            self.db_session.rollback()
            return {
                "success": False,
                "error": str(e),
                "total_saved": 0,
                "error_message": "Bulk save failed - transaction rolled back"
            }

