# MinIO - S3-Compatible Object Storage

MinIO is a high-performance, S3-compatible object storage system for storing files, images, videos, and any other unstructured data.

## What is MinIO?

MinIO provides:
- **S3-Compatible API** - Works with AWS S3 SDKs and tools
- **File Storage** - Store and retrieve files of any size
- **Presigned URLs** - Generate temporary URLs for secure file access
- **Bucket Management** - Organize files in buckets (like folders)
- **Web Console** - User-friendly interface for file management

## Access Information

### MinIO API
- **Endpoint**: http://localhost:9000
- **Access Key**: `minioadmin`
- **Secret Key**: `minioadmin`

### MinIO Console (Web UI)
- **URL**: http://localhost:9001
- **Username**: `minioadmin`
- **Password**: `minioadmin`

### Default Bucket
- **Name**: `reims`

## API Endpoints

### Upload File
```bash
POST /api/v1/storage/upload
Content-Type: multipart/form-data

# With curl:
curl -X POST http://localhost:8000/api/v1/storage/upload \
  -F "file=@/path/to/your/file.pdf" \
  -F "custom_name=document.pdf"
```

### Download File
```bash
GET /api/v1/storage/download/{filename}

# Example:
curl http://localhost:8000/api/v1/storage/download/document.pdf -O
```

### List Files
```bash
GET /api/v1/storage/files?prefix=folder/

# Example:
curl http://localhost:8000/api/v1/storage/files
```

Response:
```json
{
    "files": ["test.txt", "images/photo.jpg", "docs/report.pdf"],
    "count": 3
}
```

### Get File Info
```bash
GET /api/v1/storage/info/{filename}

# Example:
curl http://localhost:8000/api/v1/storage/info/test.txt
```

Response:
```json
{
    "object_name": "test.txt",
    "size": 1024,
    "content_type": "text/plain",
    "last_modified": "2025-11-03T10:30:00",
    "etag": "abc123..."
}
```

### Get Presigned URL
```bash
GET /api/v1/storage/url/{filename}?expires=3600

# Example (URL valid for 1 hour):
curl http://localhost:8000/api/v1/storage/url/test.txt
```

Response:
```json
{
    "url": "http://localhost:9000/reims/test.txt?X-Amz-Algorithm=...",
    "expires_in": 3600
}
```

### Delete File
```bash
DELETE /api/v1/storage/{filename}

# Example:
curl -X DELETE http://localhost:8000/api/v1/storage/test.txt
```

### Storage Health Check
```bash
GET /api/v1/storage/health

# Example:
curl http://localhost:8000/api/v1/storage/health
```

## Using the Python Client Directly

### Upload File
```python
from app.db.minio_client import upload_file

# Upload file
file_data = b"File content here"
success = upload_file(
    file_data=file_data,
    object_name="folder/filename.txt",
    content_type="text/plain"
)
```

### Download File
```python
from app.db.minio_client import download_file

# Download file
file_data = download_file("folder/filename.txt")
if file_data:
    with open("local_file.txt", "wb") as f:
        f.write(file_data)
```

### List Files
```python
from app.db.minio_client import list_files

# List all files
all_files = list_files()

# List files in a folder
folder_files = list_files(prefix="folder/")
```

### Get File URL
```python
from app.db.minio_client import get_file_url

# Get presigned URL (valid for 1 hour)
url = get_file_url("filename.txt", expires_seconds=3600)
```

### Delete File
```python
from app.db.minio_client import delete_file

# Delete file
success = delete_file("filename.txt")
```

## Managing Buckets

### Create New Bucket
```python
from app.db.minio_client import minio_client

# Create bucket
minio_client.make_bucket("new-bucket-name")
```

### List Buckets
```python
from app.db.minio_client import minio_client

# List all buckets
buckets = minio_client.list_buckets()
for bucket in buckets:
    print(bucket.name)
```

## Using MinIO Console

1. Open http://localhost:9001 in your browser
2. Login with `minioadmin` / `minioadmin`
3. Features:
   - Browse files and folders
   - Upload/download files via drag-and-drop
   - Create buckets
   - Set access policies
   - Monitor storage usage

## Docker Commands

### Start MinIO
```bash
sudo docker start minio
```

### Stop MinIO
```bash
sudo docker stop minio
```

### Restart MinIO
```bash
sudo docker restart minio
```

### View Logs
```bash
sudo docker logs minio
sudo docker logs -f minio  # Follow logs
```

### Remove Container (keeps data)
```bash
sudo docker rm minio
```

## File Organization Best Practices

### Use Folders
```python
# Organize files in folders using forward slashes
upload_file(data, "users/123/profile.jpg")
upload_file(data, "documents/2025/report.pdf")
upload_file(data, "images/products/product-001.png")
```

### Naming Conventions
```python
# Good names
"invoice-2025-001.pdf"
"user-avatar-123.jpg"
"export-2025-11-03.csv"

# Avoid
"my file.txt"  # spaces
"../../../etc/passwd"  # path traversal
```

## Configuration

All MinIO settings are in `app/core/config.py`:

```python
MINIO_ENDPOINT: str = "localhost:9000"
MINIO_ACCESS_KEY: str = "minioadmin"
MINIO_SECRET_KEY: str = "minioadmin"
MINIO_SECURE: bool = False  # True for HTTPS
MINIO_BUCKET_NAME: str = "reims"
```

These can be overridden with environment variables in `.env`:

```env
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_SECURE=true
MINIO_BUCKET_NAME=my-bucket
```

## Integration Examples

### Upload User Avatar
```python
from fastapi import UploadFile
from app.db.minio_client import upload_file

async def update_avatar(user_id: int, file: UploadFile):
    content = await file.read()
    filename = f"avatars/{user_id}.jpg"
    
    success = upload_file(
        file_data=content,
        object_name=filename,
        content_type="image/jpeg"
    )
    
    return {"avatar_url": f"/api/v1/storage/download/{filename}"}
```

### Generate Report and Store
```python
from app.db.minio_client import upload_file
import io

def generate_and_store_report(data):
    # Generate report
    report_content = create_pdf_report(data)
    
    # Upload to MinIO
    filename = f"reports/{data['id']}/report.pdf"
    upload_file(
        file_data=report_content,
        object_name=filename,
        content_type="application/pdf"
    )
    
    # Generate shareable link
    url = get_file_url(filename, expires_seconds=86400)  # 24 hours
    return url
```

### Store Celery Task Results
```python
from app.tasks import celery_app
from app.db.minio_client import upload_file
import json

@celery_app.task
def process_and_store_data(data):
    # Process data
    result = process_data(data)
    
    # Store result in MinIO
    filename = f"results/{celery_task.request.id}.json"
    upload_file(
        file_data=json.dumps(result).encode(),
        object_name=filename,
        content_type="application/json"
    )
    
    return {"result_file": filename}
```

## Security Considerations

### Production Setup

1. **Change Default Credentials**
```bash
sudo docker run -d \
  --name minio \
  -e "MINIO_ROOT_USER=your-secure-username" \
  -e "MINIO_ROOT_PASSWORD=your-secure-password-min-8-chars" \
  ...
```

2. **Enable HTTPS**
```python
MINIO_ENDPOINT = "minio.example.com:9000"
MINIO_SECURE = True
```

3. **Use IAM Policies**
- Create service accounts with limited permissions
- Don't use root credentials in application

4. **Set Bucket Policies**
```python
# Make bucket public (read-only)
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::reims/*"]
        }
    ]
}
minio_client.set_bucket_policy("reims", json.dumps(policy))
```

## Troubleshooting

### Connection Refused
```bash
# Check if MinIO is running
sudo docker ps | grep minio

# Start if stopped
sudo docker start minio
```

### Bucket Access Denied
```python
# Ensure bucket exists
from app.db.minio_client import ensure_bucket_exists
ensure_bucket_exists("bucket-name")
```

### File Not Found
```python
# List all files to verify
from app.db.minio_client import list_files
files = list_files()
print(files)
```

## Advanced Features

### Set Object Metadata
```python
from app.db.minio_client import minio_client

metadata = {
    "X-Amz-Meta-User-Id": "123",
    "X-Amz-Meta-Upload-Date": "2025-11-03"
}

minio_client.put_object(
    "reims",
    "file.txt",
    io.BytesIO(b"content"),
    length=7,
    metadata=metadata
)
```

### Server-Side Encryption
```python
from minio import Minio
from minio.sse import SseCustomerKey

# Use customer-provided encryption key
key = SseCustomerKey(b"your-32-byte-encryption-key")

minio_client.put_object(
    "reims",
    "encrypted-file.txt",
    data,
    length,
    sse=key
)
```

## Resources

- MinIO Documentation: https://min.io/docs/
- MinIO Python Client: https://min.io/docs/minio/linux/developers/python/minio-py.html
- S3 API Reference: https://docs.aws.amazon.com/s3/

