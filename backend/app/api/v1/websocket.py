"""
WebSocket endpoints for real-time extraction status updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_extraction_progress(upload: DocumentUpload) -> int:
    """Get extraction progress percentage from Celery task state"""
    try:
        from celery import current_app
        if upload.extraction_task_id:
            task_result = current_app.AsyncResult(upload.extraction_task_id)
            if task_result.state == 'PROCESSING':
                meta = task_result.info or {}
                return meta.get('progress', 0)
            elif task_result.state == 'SUCCESS':
                return 100
            elif task_result.state == 'FAILURE':
                return 0
    except Exception as e:
        logger.debug(f"Could not get task progress: {e}")
    return 0


def get_records_count(upload: DocumentUpload, db: Session) -> int:
    """Get count of records loaded for this upload"""
    try:
        if upload.document_type == 'balance_sheet':
            return db.query(BalanceSheetData).filter(
                BalanceSheetData.upload_id == upload.id
            ).count()
        elif upload.document_type == 'income_statement':
            return db.query(IncomeStatementData).filter(
                IncomeStatementData.upload_id == upload.id
            ).count()
        elif upload.document_type == 'cash_flow':
            return db.query(CashFlowData).filter(
                CashFlowData.upload_id == upload.id
            ).count()
    except Exception as e:
        logger.debug(f"Could not get records count: {e}")
    return 0


@router.websocket("/ws/extraction-status/{upload_id}")
async def websocket_extraction_status(websocket: WebSocket, upload_id: int):
    """
    WebSocket endpoint for real-time extraction status updates
    
    Sends updates every 2 seconds until extraction completes or fails
    """
    await websocket.accept()
    db = SessionLocal()
    last_status = None
    
    try:
        while True:
            # Query current upload status
            upload = db.query(DocumentUpload).filter(
                DocumentUpload.id == upload_id
            ).first()
            
            if not upload:
                await websocket.send_json({
                    "upload_id": upload_id,
                    "status": "not_found",
                    "error": "Upload not found"
                })
                break
            
            # Get progress and records count
            progress = get_extraction_progress(upload)
            records_loaded = get_records_count(upload, db)
            
            # Send update
            status_data = {
                "upload_id": upload_id,
                "status": upload.extraction_status,
                "progress": progress,
                "records_loaded": records_loaded,
                "error": upload.notes if upload.extraction_status == 'failed' else None
            }
            
            # Only send if status changed or every 5th iteration (to reduce traffic)
            if status_data["status"] != last_status or progress > 0:
                await websocket.send_json(status_data)
                last_status = status_data["status"]
            
            # Close if completed or failed
            if upload.extraction_status in ['completed', 'failed']:
                # Send final update
                await websocket.send_json(status_data)
                break
            
            # Check every 2 seconds
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for upload_id={upload_id}")
    except Exception as e:
        logger.error(f"WebSocket error for upload_id={upload_id}: {e}")
        try:
            await websocket.send_json({
                "upload_id": upload_id,
                "status": "error",
                "error": str(e)
            })
        except:
            pass
    finally:
        db.close()

