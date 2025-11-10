from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import io
from typing import Optional

# Create MinIO client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)


def get_minio_client():
    """Dependency to get MinIO client"""
    return minio_client


def ensure_bucket_exists(bucket_name: str = settings.MINIO_BUCKET_NAME):
    """Ensure bucket exists, create if it doesn't"""
    try:
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' created successfully")
        return True
    except S3Error as e:
        print(f"Error ensuring bucket exists: {e}")
        return False


def upload_file(
    file_data: bytes,
    object_name: str,
    content_type: str = "application/octet-stream",
    bucket_name: str = settings.MINIO_BUCKET_NAME
) -> bool:
    """
    Upload file to MinIO
    
    Args:
        file_data: File content as bytes
        object_name: Name of the object in MinIO
        content_type: MIME type of the file
        bucket_name: Target bucket name
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        ensure_bucket_exists(bucket_name)
        
        file_stream = io.BytesIO(file_data)
        file_size = len(file_data)
        
        minio_client.put_object(
            bucket_name,
            object_name,
            file_stream,
            file_size,
            content_type=content_type
        )
        return True
    except S3Error as e:
        print(f"Error uploading file: {e}")
        return False


def download_file(
    object_name: str,
    bucket_name: str = settings.MINIO_BUCKET_NAME
) -> Optional[bytes]:
    """
    Download file from MinIO
    
    Args:
        object_name: Name of the object in MinIO
        bucket_name: Source bucket name
    
    Returns:
        bytes: File content if successful, None otherwise
    """
    try:
        response = minio_client.get_object(bucket_name, object_name)
        file_data = response.read()
        response.close()
        response.release_conn()
        return file_data
    except S3Error as e:
        print(f"Error downloading file: {e}")
        return None


def delete_file(
    object_name: str,
    bucket_name: str = settings.MINIO_BUCKET_NAME
) -> bool:
    """
    Delete file from MinIO
    
    Args:
        object_name: Name of the object in MinIO
        bucket_name: Target bucket name
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        minio_client.remove_object(bucket_name, object_name)
        return True
    except S3Error as e:
        print(f"Error deleting file: {e}")
        return False


def list_files(
    bucket_name: str = settings.MINIO_BUCKET_NAME,
    prefix: str = ""
) -> list:
    """
    List files in MinIO bucket
    
    Args:
        bucket_name: Target bucket name
        prefix: Filter objects by prefix
    
    Returns:
        list: List of object names
    """
    try:
        ensure_bucket_exists(bucket_name)
        objects = minio_client.list_objects(bucket_name, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]
    except S3Error as e:
        print(f"Error listing files: {e}")
        return []


def get_file_url(
    object_name: str,
    bucket_name: str = settings.MINIO_BUCKET_NAME,
    expires_seconds: int = 3600
) -> Optional[str]:
    """
    Get presigned URL for file access
    
    Args:
        object_name: Name of the object in MinIO
        bucket_name: Target bucket name
        expires_seconds: URL expiration time in seconds (default 1 hour)
    
    Returns:
        str: Presigned URL if successful, None otherwise
    """
    try:
        from datetime import timedelta
        url = minio_client.presigned_get_object(
            bucket_name,
            object_name,
            expires=timedelta(seconds=expires_seconds)
        )
        # MinIO now generates URLs with correct external endpoint via MINIO_SERVER_URL
        return url
    except S3Error as e:
        print(f"Error generating URL: {e}")
        return None


def get_file_info(
    object_name: str,
    bucket_name: str = settings.MINIO_BUCKET_NAME
) -> Optional[dict]:
    """
    Get file metadata
    
    Args:
        object_name: Name of the object in MinIO
        bucket_name: Target bucket name
    
    Returns:
        dict: File metadata if successful, None otherwise
    """
    try:
        stat = minio_client.stat_object(bucket_name, object_name)
        return {
            "object_name": stat.object_name,
            "size": stat.size,
            "content_type": stat.content_type,
            "last_modified": stat.last_modified.isoformat(),
            "etag": stat.etag,
            "metadata": stat.metadata
        }
    except S3Error as e:
        print(f"Error getting file info: {e}")
        return None


# Initialize default bucket on startup
ensure_bucket_exists()

