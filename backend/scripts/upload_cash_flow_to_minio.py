#!/usr/bin/env python3
"""
Upload Cash Flow PDFs to MinIO

Uploads Cash Flow Statement PDFs to MinIO with organized folder structure
matching the Balance Sheet pattern.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.minio_client import upload_file
from app.core.config import settings
from minio import Minio

# Define Cash Flow PDFs to upload with their MinIO paths
CASH_FLOW_FILES = [
    {
        'local_path': '/tmp/ESP 2023 Cash Flow Statement.pdf',
        'minio_path': 'ESP001-Eastern-Shore-Plaza/2023/cash-flow/ESP_2023_Cash_Flow_Statement.pdf',
        'property_code': 'ESP001',
        'year': 2023
    },
    {
        'local_path': '/tmp/ESP 2024 Cash Flow Statement.pdf',
        'minio_path': 'ESP001-Eastern-Shore-Plaza/2024/cash-flow/ESP_2024_Cash_Flow_Statement.pdf',
        'property_code': 'ESP001',
        'year': 2024
    },
    {
        'local_path': '/tmp/Hammond Aire 2023 Cash Flow Statement.pdf',
        'minio_path': 'HMND001-Hammond-Aire/2023/cash-flow/HMND_2023_Cash_Flow_Statement.pdf',
        'property_code': 'HMND001',
        'year': 2023
    },
    {
        'local_path': '/tmp/Hammond Aire 2024 Cash Flow Statement.pdf',
        'minio_path': 'HMND001-Hammond-Aire/2024/cash-flow/HMND_2024_Cash_Flow_Statement.pdf',
        'property_code': 'HMND001',
        'year': 2024
    },
    {
        'local_path': '/tmp/TCSH 2023 Cash FLow Statement.pdf',  # Note: typo in filename
        'minio_path': 'TCSH001-The-Crossings/2023/cash-flow/TCSH_2023_Cash_Flow_Statement.pdf',
        'property_code': 'TCSH001',
        'year': 2023
    },
    {
        'local_path': '/tmp/TCSH 2024 Cash Flow Statement.pdf',
        'minio_path': 'TCSH001-The-Crossings/2024/cash-flow/TCSH_2024_Cash_Flow_Statement.pdf',
        'property_code': 'TCSH001',
        'year': 2024
    },
    {
        'local_path': '/tmp/Wendover Commons 2023 Cash Flow Statement.pdf',
        'minio_path': 'WEND001-Wendover-Commons/2023/cash-flow/WEND_2023_Cash_Flow_Statement.pdf',
        'property_code': 'WEND001',
        'year': 2023
    },
    {
        'local_path': '/tmp/Wendover Commons 2024 Cash Flow Statement.pdf',
        'minio_path': 'WEND001-Wendover-Commons/2024/cash-flow/WEND_2024_Cash_Flow_Statement.pdf',
        'property_code': 'WEND001',
        'year': 2024
    },
]

def main():
    """Upload all Cash Flow PDFs to MinIO"""
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║     UPLOADING CASH FLOW STATEMENTS TO MINIO                          ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    
    uploaded = 0
    skipped = 0
    failed = 0
    
    for file_info in CASH_FLOW_FILES:
        local_path = file_info['local_path']
        minio_path = file_info['minio_path']
        property_code = file_info['property_code']
        year = file_info['year']
        
        print(f"📄 {property_code} {year}")
        print(f"   Local:  {os.path.basename(local_path)}")
        print(f"   MinIO:  {minio_path}")
        
        # Check if file exists locally
        if not os.path.exists(local_path):
            print(f"   ❌ File not found: {local_path}")
            failed += 1
            print()
            continue
        
        # Check if already in MinIO
        try:
            minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_USE_SSL
            )
            
            try:
                minio_client.stat_object(settings.MINIO_BUCKET_NAME, minio_path)
                print(f"   ℹ️  Already exists in MinIO, skipping")
                skipped += 1
                print()
                continue
            except:
                pass  # File doesn't exist, continue with upload
        except Exception as e:
            print(f"   ⚠️  Could not check existence: {e}")
        
        # Upload to MinIO
        try:
            file_size = os.path.getsize(local_path)
            print(f"   📤 Uploading ({file_size:,} bytes)...")
            
            with open(local_path, 'rb') as f:
                file_data = f.read()
            
            upload_file(
                file_data=file_data,
                object_name=minio_path,
                bucket_name=settings.MINIO_BUCKET_NAME,
                content_type="application/pdf"
            )
            
            print(f"   ✅ Uploaded successfully!")
            uploaded += 1
        except Exception as e:
            print(f"   ❌ Upload failed: {str(e)}")
            failed += 1
        
        print()
    
    print("=" * 70)
    print(f"📊 UPLOAD SUMMARY")
    print(f"   Uploaded: {uploaded}")
    print(f"   Skipped:  {skipped} (already exist)")
    print(f"   Failed:   {failed}")
    print(f"   Total:    {len(CASH_FLOW_FILES)}")
    print()
    
    if uploaded + skipped == len(CASH_FLOW_FILES):
        print("✅ All Cash Flow PDFs are now in MinIO!")
    else:
        print(f"⚠️  {failed} file(s) failed to upload")
    
    print("=" * 70)

if __name__ == "__main__":
    main()

