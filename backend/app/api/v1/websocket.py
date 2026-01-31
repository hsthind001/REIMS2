"""
WebSocket endpoints for real-time extraction status updates

E1-S2: Auth handshake - token and org_id required in query params before accept.
"""
from typing import Dict, List, Tuple, Optional
from urllib.parse import parse_qs
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.user import User
from app.models.organization import Organization
from app.models.organization import OrganizationMember
from app.models.balance_sheet_data import BalanceSheetData
from app.models.income_statement_data import IncomeStatementData
from app.models.cash_flow_data import CashFlowData
from app.models.batch_reprocessing_job import BatchReprocessingJob
from app.models.property import Property
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# WebSocket close codes (1008 = policy violation for auth failures)
WS_CLOSE_UNAUTHORIZED = 1008


async def _validate_websocket_auth(websocket: WebSocket) -> Tuple[User, int]:
    """
    Validate JWT token and org membership from query params before accepting.
    Connect with ?token=<jwt>&org_id=<id>. Closes with 1008 if invalid.
    Returns (user, org_id) or raises after closing connection.
    """
    from app.core.jwt_auth import get_jwt_service

    query_string = websocket.scope.get("query_string", b"").decode()
    params = parse_qs(query_string)
    token = (params.get("token") or [None])[0]
    org_id_str = (params.get("org_id") or params.get("x_organization_id") or [None])[0]

    async def _reject(reason: str) -> None:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED, reason=reason)

    if not token:
        await _reject("Missing token")
        raise WebSocketDisconnect(code=WS_CLOSE_UNAUTHORIZED)

    try:
        jwt_service = get_jwt_service()
        user_info = jwt_service.get_user_from_token(token)
        user_id = user_info["user_id"]
    except Exception:
        await _reject("Invalid or expired token")
        raise WebSocketDisconnect(code=WS_CLOSE_UNAUTHORIZED)

    if not org_id_str:
        await _reject("Missing org_id")
        raise WebSocketDisconnect(code=WS_CLOSE_UNAUTHORIZED)

    try:
        org_id = int(org_id_str)
    except ValueError:
        await _reject("Invalid org_id")
        raise WebSocketDisconnect(code=WS_CLOSE_UNAUTHORIZED)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await _reject("User not found")
            raise WebSocketDisconnect(code=WS_CLOSE_UNAUTHORIZED)

        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == org_id
        ).first()
        if not membership and not user.is_superuser:
            await _reject("Not a member of this organization")
            raise WebSocketDisconnect(code=WS_CLOSE_UNAUTHORIZED)

        if user.is_superuser and not membership:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if not org:
                await _reject("Organization not found")
                raise WebSocketDisconnect(code=WS_CLOSE_UNAUTHORIZED)

        return user, org_id
    finally:
        db.close()

# Store active WebSocket connections for batch jobs (for broadcasting)
active_batch_job_connections: Dict[int, List[WebSocket]] = {}


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
    WebSocket endpoint for real-time extraction status updates.

    E1-S2: Requires ?token=<jwt>&org_id=<id> in query string before connect.
    Sends updates every 2 seconds until extraction completes or fails.
    """
    user, org_id = await _validate_websocket_auth(websocket)
    await websocket.accept()
    db = SessionLocal()
    last_status = None

    try:
        while True:
            # Query current upload status (org-scoped)
            from app.repositories.tenant_scoped import get_upload_for_org
            upload = get_upload_for_org(db, org_id, upload_id)
            
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
        except (WebSocketDisconnect, RuntimeError):
            # Client already disconnected, ignore send failure
            pass
    finally:
        db.close()


@router.websocket("/ws/batch-job/{job_id}")
async def websocket_batch_job_status(websocket: WebSocket, job_id: int):
    """
    WebSocket endpoint for real-time batch job progress updates.

    E1-S2: Requires ?token=<jwt>&org_id=<id> in query string before connect.
    Sends updates every 2 seconds with:
    - Status (pending, running, completed, failed, cancelled)
    - Progress percentage (0-100)
    - Processed documents count
    - Total documents count
    - ETA (estimated completion time)
    - Current document being processed (if available)
    
    Supports multiple clients per job (broadcasts to all).
    """
    user, org_id = await _validate_websocket_auth(websocket)
    await websocket.accept()
    db = SessionLocal()

    # Register this connection for broadcasting
    if job_id not in active_batch_job_connections:
        active_batch_job_connections[job_id] = []
    active_batch_job_connections[job_id].append(websocket)

    logger.info(f"WebSocket connected for batch job {job_id} (total clients: {len(active_batch_job_connections[job_id])})")

    last_status = None
    last_progress = None
    start_time = None
    last_processed = 0
    last_update_time = None

    try:
        while True:
            # Query current job status (org-scoped)
            from app.repositories.tenant_scoped import get_batch_job_for_org
            job = get_batch_job_for_org(db, org_id, job_id)
            
            if not job:
                await websocket.send_json({
                    "job_id": job_id,
                    "status": "not_found",
                    "error": "Batch job not found"
                })
                break
            
            # Calculate progress percentage
            progress_pct = 0
            if job.total_documents > 0:
                progress_pct = int((job.processed_documents / job.total_documents) * 100)
            
            # Calculate ETA
            eta = None
            if job.status == 'running' and job.processed_documents > 0 and job.total_documents > 0:
                if start_time is None:
                    start_time = datetime.now()
                    last_processed = job.processed_documents
                    last_update_time = datetime.now()
                else:
                    # Calculate processing rate
                    time_elapsed = (datetime.now() - start_time).total_seconds()
                    if time_elapsed > 0:
                        processing_rate = job.processed_documents / time_elapsed  # documents per second
                        remaining_documents = job.total_documents - job.processed_documents
                        if processing_rate > 0:
                            eta_seconds = remaining_documents / processing_rate
                            eta = (datetime.now() + timedelta(seconds=eta_seconds)).isoformat()
            
            # Prepare update data
            status_data = {
                "job_id": job_id,
                "job_name": job.job_name,
                "status": job.status,
                "progress_pct": progress_pct,
                "processed_documents": job.processed_documents,
                "total_documents": job.total_documents,
                "successful_count": job.successful_count,
                "failed_count": job.failed_count,
                "skipped_count": job.skipped_count,
                "eta": eta,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "estimated_completion_at": job.estimated_completion_at.isoformat() if job.estimated_completion_at else None,
                "current_document": None  # Would be populated from Celery task if available
            }
            
            # Get current document from Celery task if available
            if job.celery_task_id:
                try:
                    from celery import current_app
                    task_result = current_app.AsyncResult(job.celery_task_id)
                    if task_result.state == 'PROCESSING':
                        meta = task_result.info or {}
                        if isinstance(meta, dict):
                            status_data["current_document"] = meta.get('current_document')
                except Exception as e:
                    logger.debug(f"Could not get Celery task info: {e}")
            
            # Send update if status or progress changed
            if (status_data["status"] != last_status or 
                status_data["progress_pct"] != last_progress or
                status_data["processed_documents"] != last_processed):
                
                # Broadcast to all connected clients for this job
                disconnected_clients = []
                for client in active_batch_job_connections.get(job_id, []):
                    try:
                        await client.send_json(status_data)
                    except Exception as e:
                        logger.debug(f"Error sending to client: {e}")
                        disconnected_clients.append(client)
                
                # Remove disconnected clients
                for client in disconnected_clients:
                    if job_id in active_batch_job_connections:
                        active_batch_job_connections[job_id].remove(client)
                
                last_status = status_data["status"]
                last_progress = status_data["progress_pct"]
                last_processed = status_data["processed_documents"]
            
            # Close if job completed, failed, or cancelled
            if job.status in ['completed', 'failed', 'cancelled']:
                # Send final update
                await websocket.send_json(status_data)
                break
            
            # Check every 2 seconds
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for batch job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for batch job {job_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "job_id": job_id,
                "status": "error",
                "error": str(e)
            })
        except (WebSocketDisconnect, RuntimeError):
            # Client already disconnected, ignore send failure
            pass
    finally:
        # Remove this connection from active connections
        if job_id in active_batch_job_connections:
            if websocket in active_batch_job_connections[job_id]:
                active_batch_job_connections[job_id].remove(websocket)
            # Clean up empty lists
            if not active_batch_job_connections[job_id]:
                del active_batch_job_connections[job_id]
        db.close()

