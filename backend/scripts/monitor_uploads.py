#!/usr/bin/env python3
"""
Real-time Upload Monitoring Script

Monitors the complete upload pipeline:
1. Frontend upload → Backend API
2. MinIO storage verification
3. Extraction task trigger
4. Database loading
5. Error detection and auto-fix
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.db.minio_client import get_file_info, download_file
from app.services.document_service import DocumentService
from app.tasks.extraction_tasks import extract_document
from app.core.config import settings


class UploadMonitor:
    """Monitor upload pipeline and auto-fix issues"""
    
    def __init__(self):
        self.db: Session = SessionLocal()
        self.last_checked_id = 0
        self.issues_found = []
        self.fixes_applied = []
    
    def check_minio_file(self, file_path: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            file_info = get_file_info(file_path)
            return file_info is not None
        except Exception as e:
            # If stat_object fails, file doesn't exist
            return False
    
    def verify_upload_pipeline(self, upload: DocumentUpload) -> Dict:
        """Verify complete upload pipeline for a single upload"""
        issues = []
        status = "✅ OK"
        
        # 1. Check MinIO storage
        if upload.file_path:
            if not self.check_minio_file(upload.file_path):
                issues.append(f"File not found in MinIO: {upload.file_path}")
                status = "❌ MINIO MISSING"
            else:
                print(f"   ✅ MinIO: File exists at {upload.file_path}")
        else:
            issues.append("No file_path set in upload record")
            status = "❌ NO FILE PATH"
        
        # 2. Check extraction status
        if upload.extraction_status == 'pending':
            # Check if task was triggered
            if upload.id > self.last_checked_id:
                print(f"   ⚠️  Extraction pending - checking if task needs trigger...")
                # Try to trigger if it's been pending for more than 30 seconds
                time_since_upload = (datetime.utcnow() - upload.created_at).total_seconds()
                if time_since_upload > 30:
                    issues.append(f"Extraction pending for {time_since_upload:.0f} seconds - may need trigger")
                    status = "⚠️  PENDING"
        elif upload.extraction_status == 'processing':
            # Check if it's stuck (processing for more than 10 minutes)
            time_processing = (datetime.utcnow() - upload.updated_at).total_seconds()
            if time_processing > 600:  # 10 minutes
                issues.append(f"Extraction stuck in processing for {time_processing/60:.1f} minutes")
                status = "⚠️  STUCK"
        elif upload.extraction_status == 'failed':
            issues.append(f"Extraction failed: {upload.error_message or 'Unknown error'}")
            status = "❌ FAILED"
        elif upload.extraction_status == 'completed':
            # Verify data was loaded
            data_count = self.check_data_loaded(upload)
            if data_count == 0:
                issues.append("Extraction completed but no data found in database")
                status = "⚠️  NO DATA"
            else:
                print(f"   ✅ Database: {data_count} records loaded")
        
        return {
            'upload_id': upload.id,
            'status': status,
            'issues': issues,
            'extraction_status': upload.extraction_status
        }
    
    def check_data_loaded(self, upload: DocumentUpload) -> int:
        """Check if data was loaded into appropriate tables"""
        try:
            if upload.document_type == 'balance_sheet':
                from app.models.balance_sheet_data import BalanceSheetData
                count = self.db.query(BalanceSheetData).filter(
                    BalanceSheetData.upload_id == upload.id
                ).count()
            elif upload.document_type == 'income_statement':
                from app.models.income_statement_data import IncomeStatementData
                count = self.db.query(IncomeStatementData).filter(
                    IncomeStatementData.upload_id == upload.id
                ).count()
            elif upload.document_type == 'cash_flow':
                from app.models.cash_flow_data import CashFlowData
                count = self.db.query(CashFlowData).filter(
                    CashFlowData.upload_id == upload.id
                ).count()
            elif upload.document_type == 'rent_roll':
                from app.models.rent_roll_data import RentRollData
                count = self.db.query(RentRollData).filter(
                    RentRollData.upload_id == upload.id
                ).count()
            else:
                count = 0
            return count
        except Exception as e:
            print(f"   ⚠️  Error checking data: {e}")
            return 0
    
    def auto_fix_issue(self, upload: DocumentUpload, issue: str) -> bool:
        """Attempt to auto-fix detected issues"""
        try:
            # Fix: Missing MinIO file but upload record exists
            if "not found in MinIO" in issue:
                print(f"   🔧 Cannot auto-fix: File missing from MinIO (may need re-upload)")
                return False
            
            # Fix: Pending extraction that needs trigger
            if "Extraction pending" in issue and upload.extraction_status == 'pending':
                print(f"   🔧 Auto-fixing: Triggering extraction for upload_id={upload.id}")
                upload.extraction_status = 'processing'
                self.db.commit()
                task = extract_document.delay(upload.id)
                print(f"   ✅ Extraction triggered: task_id={task.id}")
                self.fixes_applied.append(f"Triggered extraction for upload_id={upload.id}")
                return True
            
            # Fix: Stuck in processing (retry)
            if "stuck in processing" in issue:
                print(f"   🔧 Auto-fixing: Retrying extraction for stuck upload_id={upload.id}")
                upload.extraction_status = 'pending'
                self.db.commit()
                task = extract_document.delay(upload.id)
                print(f"   ✅ Retry triggered: task_id={task.id}")
                self.fixes_applied.append(f"Retried extraction for upload_id={upload.id}")
                return True
            
            # Fix: Failed extraction (retry)
            if upload.extraction_status == 'failed':
                print(f"   🔧 Auto-fixing: Retrying failed extraction for upload_id={upload.id}")
                upload.extraction_status = 'pending'
                upload.error_message = None
                self.db.commit()
                task = extract_document.delay(upload.id)
                print(f"   ✅ Retry triggered: task_id={task.id}")
                self.fixes_applied.append(f"Retried failed extraction for upload_id={upload.id}")
                return True
            
            return False
        except Exception as e:
            print(f"   ❌ Error auto-fixing: {e}")
            self.db.rollback()
            return False
    
    def monitor_new_uploads(self, limit: int = 10):
        """Monitor new uploads since last check"""
        try:
            # Get new uploads
            new_uploads = self.db.query(DocumentUpload).filter(
                DocumentUpload.id > self.last_checked_id
            ).order_by(desc(DocumentUpload.id)).limit(limit).all()
            
            if not new_uploads:
                return
            
            print(f"\n{'='*80}")
            print(f"📊 Monitoring {len(new_uploads)} new upload(s)")
            print(f"{'='*80}\n")
            
            for upload in reversed(new_uploads):  # Process oldest first
                print(f"\n📄 Upload ID: {upload.id}")
                print(f"   Type: {upload.document_type}")
                print(f"   File: {upload.file_name}")
                print(f"   Status: {upload.extraction_status}")
                print(f"   Created: {upload.created_at}")
                
                # Verify pipeline
                result = self.verify_upload_pipeline(upload)
                
                # Report issues
                if result['issues']:
                    print(f"   {result['status']}")
                    for issue in result['issues']:
                        print(f"      - {issue}")
                        self.issues_found.append({
                            'upload_id': upload.id,
                            'issue': issue
                        })
                        
                        # Try to auto-fix
                        if self.auto_fix_issue(upload, issue):
                            print(f"      ✅ Auto-fixed!")
                
                # Update last checked
                if upload.id > self.last_checked_id:
                    self.last_checked_id = upload.id
            
            # Summary
            if self.issues_found:
                print(f"\n⚠️  Found {len(self.issues_found)} issue(s)")
            if self.fixes_applied:
                print(f"✅ Applied {len(self.fixes_applied)} fix(es)")
            
        except Exception as e:
            print(f"❌ Error monitoring: {e}")
            import traceback
            traceback.print_exc()
    
    def get_recent_uploads_summary(self):
        """Get summary of recent uploads"""
        try:
            recent = self.db.query(DocumentUpload).order_by(
                desc(DocumentUpload.id)
            ).limit(5).all()
            
            print(f"\n📊 Recent Uploads Summary:")
            print(f"{'ID':<6} {'Type':<20} {'Status':<20} {'Created':<20}")
            print(f"{'-'*70}")
            
            for upload in recent:
                status_icon = {
                    'completed': '✅',
                    'processing': '⏳',
                    'pending': '⏸️',
                    'failed': '❌',
                    'uploaded_to_minio': '📤'
                }.get(upload.extraction_status, '❓')
                
                print(f"{upload.id:<6} {upload.document_type:<20} {status_icon} {upload.extraction_status:<15} {upload.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"❌ Error getting summary: {e}")
    
    def run_continuous_monitoring(self, interval: int = 10):
        """Run continuous monitoring"""
        print(f"🚀 Starting Upload Monitor")
        print(f"   Checking every {interval} seconds")
        print(f"   Monitoring uploads after ID: {self.last_checked_id}\n")
        
        try:
            while True:
                self.monitor_new_uploads()
                self.get_recent_uploads_summary()
                
                # Reset counters for next cycle
                self.issues_found = []
                self.fixes_applied = []
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
        finally:
            self.db.close()


def main():
    """Main entry point"""
    monitor = UploadMonitor()
    monitor.run_continuous_monitoring(interval=10)


if __name__ == "__main__":
    main()

