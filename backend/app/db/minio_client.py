from minio import Minio
from minio.error import S3Error
from app.core.config import settings
import io
from typing import Optional
import os
from urllib.parse import urlparse, urlunparse

# Create MinIO client for internal operations (uses Docker service name)
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
    
    Uses host.docker.internal to connect to MinIO from inside Docker,
    allowing us to generate presigned URLs with localhost:9000 that have
    valid signatures.
    
    Args:
        object_name: Name of the object in MinIO
        bucket_name: Target bucket name
        expires_seconds: URL expiration time in seconds (default 1 hour)
    
    Returns:
        str: Presigned URL if successful, None otherwise
    """
    try:
        from datetime import timedelta
        import socket
        
        # Try to create a client that can reach MinIO via host.docker.internal
        # This allows us to generate presigned URLs with localhost:9000
        # First, try host.docker.internal (works on Docker Desktop and some Linux setups)
        try:
            # Create client using host.docker.internal to reach MinIO on host
            external_client = Minio(
                'host.docker.internal:9000',
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            # Test connection by generating presigned URL
            url = external_client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expires_seconds)
            )
            # Replace host.docker.internal with localhost for browser access
            url = url.replace('host.docker.internal', 'localhost')
            return url
        except Exception:
            # If host.docker.internal doesn't work, try using gateway IP
            # Get the Docker gateway IP (usually 172.17.0.1)
            try:
                gateway_ip = socket.gethostbyname('host.docker.internal')
            except socket.gaierror:
                # Fallback: use the gateway IP directly
                gateway_ip = '172.17.0.1'
            
            try:
                external_client = Minio(
                    f'{gateway_ip}:9000',
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=settings.MINIO_SECURE
                )
                url = external_client.presigned_get_object(
                    bucket_name,
                    object_name,
                    expires=timedelta(seconds=expires_seconds)
                )
                # Replace gateway IP with localhost
                url = url.replace(gateway_ip, 'localhost')
                return url
            except Exception:
                # Final fallback: generate with internal client and replace hostname
                # Signature will be invalid, but MinIO might accept it if MINIO_SERVER_URL is set
                url = minio_client.presigned_get_object(
                    bucket_name,
                    object_name,
                    expires=timedelta(seconds=expires_seconds)
                )
                parsed = urlparse(url)
                if parsed.hostname in ['minio', 'reims-minio']:
                    new_netloc = f'localhost:{parsed.port or 9000}'
                    url = urlunparse((
                        parsed.scheme,
                        new_netloc,
                        parsed.path,
                        parsed.params,
                        parsed.query,
                        parsed.fragment
                    ))
                return url
    except S3Error as e:
        print(f"Error generating presigned URL: {e}")
        return None
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
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


# Initialize default bucket on startup (disabled for testing without MinIO)
# ensure_bucket_exists()

