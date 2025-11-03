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
        uploaded_by: Optional[int] = None
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
        
        # Step 4: Check for duplicate
        existing_upload = self.check_duplicate(
            property_obj.id,
            period.id,
            document_type,
            file_hash
        )
        if existing_upload:
            return {
                "is_duplicate": True,
                "upload_id": existing_upload.id,
                "message": "Duplicate file already exists",
                "file_path": existing_upload.file_path
            }
        
        # Step 5: Upload to MinIO
        file_path = await self.upload_to_storage(
            file_content,
            property_code,
            period_year,
            period_month,
            document_type,
            file.filename
        )
        
        # Step 6: Create document_uploads record
        upload = DocumentUpload(
            property_id=property_obj.id,
            period_id=period.id,
            document_type=document_type,
            file_name=file.filename,
            file_path=file_path,
            file_hash=file_hash,
            file_size_bytes=file_size,
            uploaded_by=uploaded_by,
            extraction_status='pending',
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
    
    async def upload_to_storage(
        self,
        file_content: bytes,
        property_code: str,
        period_year: int,
        period_month: int,
        document_type: str,
        original_filename: str
    ) -> str:
        """
        Upload file to MinIO with organized path structure
        
        Path format: {property_code}/{year}/{month}/{document_type}_{timestamp}.pdf
        
        Args:
            file_content: File content as bytes
            property_code: Property code
            period_year: Year
            period_month: Month
            document_type: Document type
            original_filename: Original filename
        
        Returns:
            str: File path in MinIO
        
        Raises:
            HTTPException: If upload fails
        """
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get file extension
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = '.pdf'
        
        # Build file path
        file_path = f"{property_code}/{period_year}/{period_month:02d}/{document_type}_{timestamp}{ext}"
        
        # Upload to MinIO
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
        
        return file_path
    
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

