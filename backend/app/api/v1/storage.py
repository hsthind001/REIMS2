from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import io
from sqlalchemy.orm import Session
from app.db import minio_client
from app.db.database import get_db
from app.api.dependencies import get_current_user_hybrid, get_current_organization
from app.models.user import User
from app.models.organization import Organization
from app.repositories.tenant_scoped import get_upload_for_org, get_upload_by_path_for_org

router = APIRouter()


# Response models
class FileUploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str
    message: str


class FileInfo(BaseModel):
    object_name: str
    size: int
    content_type: Optional[str]
    last_modified: str
    etag: str


class FileListResponse(BaseModel):
    files: List[str]
    count: int


class FileURLResponse(BaseModel):
    url: str
    expires_in: int


@router.post("/storage/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Upload a file to MinIO storage. Requires authentication and organization context.
    Object key is generated server-side only (never accept from client).
    """
    import uuid
    import os
    import re
    try:
        # Read file content
        content = await file.read()

        # Generate server-side object key: org/{org_id}/uploads/{uuid}/{safe_filename}
        ext = os.path.splitext(file.filename or "file")[1] or ""
        safe_base = re.sub(r"[^a-zA-Z0-9._-]", "_", (file.filename or "file")[:50])
        object_name = f"org/{current_org.id}/uploads/{uuid.uuid4().hex[:12]}/{safe_base}{ext}"

        # Upload to MinIO
        success = minio_client.upload_file(
            file_data=content,
            object_name=object_name,
            content_type=file.content_type or "application/octet-stream"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file"
            )
        
        return {
            "filename": object_name,
            "size": len(content),
            "content_type": file.content_type or "application/octet-stream",
            "message": f"File '{object_name}' uploaded successfully"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/storage/document/{upload_id}/url", response_model=FileURLResponse)
async def get_document_presigned_url(
    upload_id: int,
    expires: int = Query(3600, description="URL expiration in seconds", ge=60, le=86400),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get presigned URL for a document by upload_id (E3-S2).
    Only issues URLs for documents in DB with ownership check.
    Preferred over /storage/url/{path}.
    """
    upload = get_upload_for_org(db, current_org.id, upload_id)
    if not upload or not upload.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    url = minio_client.get_file_url(upload.file_path, expires_seconds=expires)
    if not url:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate URL")
    return {"url": url, "expires_in": expires}


def _require_upload_for_path(db: Session, org_id: int, file_path: str):
    """E3-S2: Only allow access if DB record exists and belongs to org."""
    upload = get_upload_by_path_for_org(db, org_id, file_path)
    if not upload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or access denied")
    return upload


@router.get("/storage/download/{file_path:path}")
async def download_file(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Download a file. E3-S2: Requires DB record + org ownership.
    Prefer GET /storage/document/{upload_id}/url for documents.
    """
    _require_upload_for_path(db, current_org.id, file_path)
    try:
        file_data = minio_client.download_file(file_path)
        if file_data is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        file_info = minio_client.get_file_info(file_path)
        content_type = file_info.get("content_type", "application/octet-stream") if file_info else "application/octet-stream"
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={file_path.split('/')[-1]}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/storage/files", response_model=FileListResponse)
async def list_files(
    prefix: str = Query("", description="Filter files by prefix (scoped to org)"),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    List files in MinIO. E3-S2: Prefix is scoped to org/{org_id}/.
    """
    try:
        org_prefix = f"org/{current_org.id}/"
        safe_prefix = org_prefix + (prefix.strip("/") + "/" if prefix else "")
        files = minio_client.list_files(prefix=safe_prefix)
        return {"files": files, "count": len(files)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/storage/info/{file_path:path}", response_model=FileInfo)
async def get_file_info(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get file metadata. E3-S2: Requires DB record + org ownership.
    """
    _require_upload_for_path(db, current_org.id, file_path)
    file_info = minio_client.get_file_info(file_path)
    if not file_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return file_info


@router.get("/storage/url/{file_path:path}", response_model=FileURLResponse)
async def get_file_url_by_path(
    file_path: str,
    expires: int = Query(3600, ge=1, le=604800),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Get presigned URL by file path. E3-S2: Requires DB record + org ownership.
    Prefer GET /storage/document/{upload_id}/url for documents.
    """
    _require_upload_for_path(db, current_org.id, file_path)
    url = minio_client.get_file_url(file_path, expires_seconds=expires)
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return {"url": url, "expires_in": expires}


@router.delete("/storage/{file_path:path}")
async def delete_file(
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_hybrid),
    current_org: Organization = Depends(get_current_organization),
):
    """
    Delete a file. E3-S2: Requires DB record + org ownership.
    """
    _require_upload_for_path(db, current_org.id, file_path)
    success = minio_client.delete_file(file_path)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found or could not be deleted")
    return {"filename": file_path, "message": "File deleted successfully"}


@router.get("/storage/health")
async def storage_health():
    """
    Check MinIO storage health
    """
    try:
        # Try to ensure bucket exists as a health check
        bucket_exists = minio_client.ensure_bucket_exists()
        
        return {
            "status": "healthy" if bucket_exists else "unhealthy",
            "minio": "connected" if bucket_exists else "disconnected",
            "bucket": minio_client.settings.MINIO_BUCKET_NAME
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "minio": "error",
            "error": str(e)
        }

