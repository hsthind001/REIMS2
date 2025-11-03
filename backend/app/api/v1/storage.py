from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import io
from app.db import minio_client

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
    custom_name: Optional[str] = Query(None, description="Custom name for the file")
):
    """
    Upload a file to MinIO storage
    """
    try:
        # Read file content
        content = await file.read()
        
        # Use custom name if provided, otherwise use original filename
        object_name = custom_name if custom_name else file.filename
        
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


@router.get("/storage/download/{filename}")
async def download_file(filename: str):
    """
    Download a file from MinIO storage
    """
    try:
        # Download file from MinIO
        file_data = minio_client.download_file(filename)
        
        if file_data is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' not found"
            )
        
        # Get file info for content type
        file_info = minio_client.get_file_info(filename)
        content_type = file_info.get("content_type", "application/octet-stream") if file_info else "application/octet-stream"
        
        # Return file as streaming response
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading file: {str(e)}"
        )


@router.get("/storage/files", response_model=FileListResponse)
async def list_files(prefix: str = Query("", description="Filter files by prefix")):
    """
    List all files in MinIO storage
    """
    try:
        files = minio_client.list_files(prefix=prefix)
        return {
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing files: {str(e)}"
        )


@router.get("/storage/info/{filename}", response_model=FileInfo)
async def get_file_info(filename: str):
    """
    Get information about a specific file
    """
    try:
        file_info = minio_client.get_file_info(filename)
        
        if file_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' not found"
            )
        
        return file_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting file info: {str(e)}"
        )


@router.get("/storage/url/{filename}", response_model=FileURLResponse)
async def get_file_url(
    filename: str,
    expires: int = Query(3600, description="URL expiration time in seconds", ge=1, le=604800)
):
    """
    Get a presigned URL for direct file access
    
    The URL will be valid for the specified number of seconds (default: 1 hour, max: 7 days)
    """
    try:
        url = minio_client.get_file_url(filename, expires_seconds=expires)
        
        if url is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' not found"
            )
        
        return {
            "url": url,
            "expires_in": expires
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating URL: {str(e)}"
        )


@router.delete("/storage/{filename}")
async def delete_file(filename: str):
    """
    Delete a file from MinIO storage
    """
    try:
        success = minio_client.delete_file(filename)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' not found or could not be deleted"
            )
        
        return {
            "filename": filename,
            "message": f"File '{filename}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting file: {str(e)}"
        )


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

