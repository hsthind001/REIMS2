"""
Document Service - Business logic for document upload workflow
"""
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
from typing import Optional, Dict
from datetime import datetime, date
import hashlib
import os

from app.models.property import Property
from app.models.financial_period import FinancialPeriod
from app.models.document_upload import DocumentUpload
from app.db.minio_client import upload_file, get_minio_client
from app.core.config import settings


# Property name mapping for MinIO folder structure
PROPERTY_NAME_MAPPING = {
    'ESP001': 'Eastern-Shore-Plaza',
    'HMND001': 'Hammond-Aire',
    'TCSH001': 'The-Crossings',
    'WEND001': 'Wendover-Commons'
}


class DocumentService:
    """Handle document upload workflow and storage"""
    
    def __init__(self, db: Session):
        self.db = db
        self.minio_client = get_minio_client()
    
    async def upload_document(
        self,
        property_code: str,
        period_year: int,
        period_month: int,
        document_type: str,
        file: UploadFile,
        uploaded_by: Optional[int] = None,
        force_overwrite: bool = False
    ) -> Dict:
        """
        Complete document upload workflow
        
        Steps:
        1. Validate property exists
        2. Get/create financial period
        3. Calculate file hash for deduplication
        4. Check for duplicate uploads
        5. Upload to MinIO
        6. Create DocumentUpload record
        
        Args:
            property_code: Property code (e.g., WEND001)
            period_year: Financial period year
            period_month: Financial period month (1-12)
            document_type: Type of document (balance_sheet, income_statement, etc.)
            file: Uploaded PDF file
            uploaded_by: User ID (optional)
        
        Returns:
            dict: Upload result with upload_id and file_path
        
        Raises:
            HTTPException: If validation fails or upload errors occur
        """
        # Step 1: Validate property exists
        property_obj = self.get_property_by_code(property_code)
        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property '{property_code}' not found"
            )
        
        # Step 2: Get or create period
        period = self.get_or_create_period(
            property_obj.id,
            period_year,
            period_month
        )
        
        # Step 3: Read file and calculate hash
        file_content = await file.read()
        file_hash = self.calculate_file_hash(file_content)
        file_size = len(file_content)
        
        # Step 3.5: Intelligent document validation (property, type, year)
        print(f"🔍 Validating property, document type, and year from PDF content...")
        from app.utils.extraction_engine import MultiEngineExtractor
        detector = MultiEngineExtractor()
        
        # Get all properties for property detection
        all_properties = self.db.query(Property).all()
        available_props = [{
            'property_code': p.property_code,
            'property_name': p.property_name,
            'city': p.city
        } for p in all_properties]
        
        # Detect property
        property_detection = detector.detect_property_name(file_content, available_props)
        detected_property_code = property_detection.get("detected_property_code")
        property_confidence = property_detection.get("confidence", 0)
        
        # Property validation DISABLED - caused false positives with A/R cross-references
        # Financial documents often reference multiple properties in A/R accounts
        # This was incorrectly flagging valid documents
        # Users should ensure they select correct property manually
        
        print(f"ℹ️  Property detected: {detected_property_code or 'N/A'} (confidence: {property_confidence}%) - validation disabled")
        
        # Detect document type
        type_detection = detector.detect_document_type(file_content)
        detected_type = type_detection.get("detected_type", "unknown")
        type_confidence = type_detection.get("confidence", 0)
        
        # Detect year and period
        period_detection = detector.detect_year_and_period(file_content)
        detected_year = period_detection.get("year")
        detected_month = period_detection.get("month")
        period_confidence = period_detection.get("confidence", 0)
        
        # Check document type mismatch
        if detected_type != "unknown" and detected_type != document_type and type_confidence >= 30:
            type_names = {
                "balance_sheet": "Balance Sheet",
                "income_statement": "Income Statement",
                "cash_flow": "Cash Flow Statement",
                "rent_roll": "Rent Roll"
            }
            
            print(f"⚠️  Document type mismatch detected!")
            print(f"   Selected: {document_type} | Detected: {detected_type} (confidence: {type_confidence}%)")
            
            return {
                "type_mismatch": True,
                "selected_type": document_type,
                "detected_type": detected_type,
                "confidence": type_confidence,
                "keywords_found": type_detection.get("keywords_found", []),
                "message": f"Document type mismatch! You selected '{type_names.get(document_type, document_type)}' but the PDF appears to be a '{type_names.get(detected_type, detected_type)}' (confidence: {type_confidence}%)."
            }
        
        # Check year mismatch
        # SKIP for rent_roll: contains future lease dates that interfere with "As of Date" detection
        if (document_type != "rent_roll" and 
            detected_year and detected_year != period_year and period_confidence >= 50):
            print(f"⚠️  Year mismatch detected!")
            print(f"   Selected: {period_year} | Detected: {detected_year} (confidence: {period_confidence}%)")
            
            return {
                "year_mismatch": True,
                "selected_year": period_year,
                "detected_year": detected_year,
                "period_text": period_detection.get("period_text", ""),
                "confidence": period_confidence,
                "message": f"Year mismatch! You selected {period_year} but the PDF appears to be for {detected_year}. Period found: {period_detection.get('period_text', 'unknown')}"
            }
        
        # Month validation DISABLED per user request
        # Users can select any month - only year and type are validated
        
        print(f"✅ Document validated: {detected_type} | Year: {detected_year or 'N/A'} | Month: {detected_month or 'N/A'} (month check disabled)")
        
        # Step 4: Check for duplicate and auto-replace
        existing_upload = self.check_duplicate(
            property_obj.id,
            period.id,
            document_type,
            file_hash
        )
        if existing_upload:
            # Auto-replace: Delete old upload (cascade deletes all related data)
            print(f"🔄 Duplicate detected (ID {existing_upload.id}). Auto-replacing with new upload...")
            
            # Delete old file from MinIO if exists
            if existing_upload.file_path:
                try:
                    from app.db.minio_client import delete_file
                    delete_file(existing_upload.file_path, settings.MINIO_BUCKET_NAME)
                    print(f"🗑️  Deleted old file from MinIO: {existing_upload.file_path}")
                except Exception as e:
                    print(f"⚠️  Warning: Could not delete old file from MinIO: {e}")
            
            # Delete old database record (cascades to all related financial data)
            self.db.delete(existing_upload)
            self.db.commit()
            print(f"✅ Old upload deleted. Proceeding with new upload...")
        
        # Step 5: Generate file path and check if exists
        file_path = await self.generate_file_path(
            property_obj,
            period_year,
            period_month,
            document_type,
            file.filename
        )
        
        # Check if file already exists at this path (not hash duplicate)
        if not force_overwrite:
            existing_file = self.check_file_exists(file_path)
            if existing_file:
                return {
                    "file_exists": True,
                    "existing_file": existing_file,
                    "message": "File already exists at this location",
                    "requires_confirmation": True
                }
        
        # Upload to MinIO
        print(f"📤 Uploading to MinIO: {file_path}")
        success = upload_file(
            file_data=file_content,
            object_name=file_path,
            content_type="application/pdf",
            bucket_name=settings.MINIO_BUCKET_NAME
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )
        
        print(f"✅ File uploaded to MinIO successfully")
        
        # Step 6: Create document_uploads record with status: uploaded_to_minio
        upload = DocumentUpload(
            property_id=property_obj.id,
            period_id=period.id,
            document_type=document_type,
            file_name=file.filename,
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=file_size,
            uploaded_by=uploaded_by,
            extraction_status='uploaded_to_minio',  # Granular status
            version=self._get_next_version(property_obj.id, period.id, document_type),
            is_active=True
        )
        
        self.db.add(upload)
        self.db.commit()
        self.db.refresh(upload)
        
        return {
            "is_duplicate": False,
            "upload_id": upload.id,
            "file_path": file_path,
            "message": "Document uploaded successfully"
        }
    
    def get_property_by_code(self, property_code: str) -> Optional[Property]:
        """Get property by code"""
        return self.db.query(Property).filter(
            Property.property_code == property_code
        ).first()
    
    def get_or_create_period(
        self,
        property_id: int,
        period_year: int,
        period_month: int
    ) -> FinancialPeriod:
        """
        Get existing period or create new one
        
        Args:
            property_id: Property ID
            period_year: Year (e.g., 2024)
            period_month: Month (1-12)
        
        Returns:
            FinancialPeriod: Existing or newly created period
        """
        # Try to find existing period
        period = self.db.query(FinancialPeriod).filter(
            FinancialPeriod.property_id == property_id,
            FinancialPeriod.period_year == period_year,
            FinancialPeriod.period_month == period_month
        ).first()
        
        if period:
            return period
        
        # Create new period
        period_start_date = date(period_year, period_month, 1)
        
        # Calculate end date (last day of month)
        if period_month == 12:
            period_end_date = date(period_year, 12, 31)
        else:
            # First day of next month minus one day
            from calendar import monthrange
            last_day = monthrange(period_year, period_month)[1]
            period_end_date = date(period_year, period_month, last_day)
        
        # Calculate fiscal quarter
        fiscal_quarter = ((period_month - 1) // 3) + 1
        
        period = FinancialPeriod(
            property_id=property_id,
            period_year=period_year,
            period_month=period_month,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            fiscal_year=period_year,
            fiscal_quarter=fiscal_quarter,
            is_closed=False
        )
        
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        
        return period
    
    def calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate MD5 hash of file content"""
        return hashlib.md5(file_content).hexdigest()
    
    def check_duplicate(
        self,
        property_id: int,
        period_id: int,
        document_type: str,
        file_hash: str
    ) -> Optional[DocumentUpload]:
        """
        Check if duplicate file already exists
        
        Checks for same property, period, document type, and file hash
        """
        return self.db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.period_id == period_id,
            DocumentUpload.document_type == document_type,
            DocumentUpload.file_hash == file_hash,
            DocumentUpload.is_active == True
        ).first()
    
    async def generate_file_path(
        self,
        property_obj: Property,
        period_year: int,
        period_month: int,
        document_type: str,
        original_filename: str
    ) -> str:
        """
        Generate MinIO file path using new organized structure
        
        Path format: {property_code}-{property_name}/{year}/{doc_type}/{standardized_file}.pdf
        Example: ESP001-Eastern-Shore-Plaza/2025/rent-roll/ESP_2025_Rent_Roll_April.pdf
        
        Args:
            property_obj: Property object (includes code and name)
            period_year: Year
            period_month: Month
            document_type: Document type
            original_filename: Original filename
        
        Returns:
            str: Standardized file path for MinIO
        """
        # Get property folder name
        property_code = property_obj.property_code
        prop_folder = PROPERTY_NAME_MAPPING.get(property_code, property_obj.property_name.replace(' ', '-'))
        
        # Map document types to folder names (with hyphens)
        doc_type_folders = {
            'balance_sheet': 'balance-sheet',
            'income_statement': 'income-statement',
            'cash_flow': 'cash-flow',
            'rent_roll': 'rent-roll'
        }
        doc_folder = doc_type_folders.get(document_type, document_type)
        
        # Generate standardized filename
        prop_abbr = property_code[:property_code.find('0')] if '0' in property_code else property_code[:4]
        
        # Month name for rent rolls
        month_name = datetime(period_year, period_month, 1).strftime('%B') if document_type == 'rent_roll' else ''
        
        if document_type == 'rent_roll' and month_name:
            filename = f"{prop_abbr}_{period_year}_Rent_Roll_{month_name}.pdf"
        else:
            doc_type_map = {
                'balance_sheet': 'Balance_Sheet',
                'income_statement': 'Income_Statement',
                'cash_flow': 'Cash_Flow_Statement'
            }
            type_name = doc_type_map.get(document_type, document_type)
            filename = f"{prop_abbr}_{period_year}_{type_name}.pdf"
        
        # Build structured path
        file_path = f"{property_code}-{prop_folder}/{period_year}/{doc_folder}/{filename}"
        
        return file_path
    
    def check_file_exists(self, file_path: str) -> Optional[Dict]:
        """
        Check if file already exists in MinIO at the given path
        
        Args:
            file_path: MinIO object path to check
        
        Returns:
            dict with file info if exists, None if not found
        """
        try:
            stat = self.minio_client.stat_object(settings.MINIO_BUCKET_NAME, file_path)
            return {
                'exists': True,
                'path': file_path,
                'size': stat.size,
                'last_modified': stat.last_modified.isoformat(),
                'etag': stat.etag
            }
        except:
            return None
    
    def _get_next_version(
        self,
        property_id: int,
        period_id: int,
        document_type: str
    ) -> int:
        """Get next version number for document type in this period"""
        max_version = self.db.query(DocumentUpload).filter(
            DocumentUpload.property_id == property_id,
            DocumentUpload.period_id == period_id,
            DocumentUpload.document_type == document_type
        ).count()
        
        return max_version + 1
    
    def get_upload_by_id(self, upload_id: int) -> Optional[DocumentUpload]:
        """Get upload by ID"""
        return self.db.query(DocumentUpload).filter(
            DocumentUpload.id == upload_id
        ).first()
    
    def update_extraction_status(
        self,
        upload_id: int,
        status: str,
        extraction_id: Optional[int] = None
    ):
        """Update extraction status for an upload"""
        upload = self.get_upload_by_id(upload_id)
        if not upload:
            return False
        
        upload.extraction_status = status
        
        if status == "processing":
            upload.extraction_started_at = datetime.now()
        elif status in ["completed", "failed"]:
            upload.extraction_completed_at = datetime.now()
        
        if extraction_id:
            upload.extraction_id = extraction_id
        
        self.db.commit()
        return True

