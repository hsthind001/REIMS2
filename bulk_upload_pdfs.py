#!/usr/bin/env python3
"""
Bulk upload PDFs to REIMS from /home/gurpyar/uploads/
"""
import os
import sys
import time
import requests
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000"
PDFS_DIR = "/home/gurpyar/REIMS_Uploaded"
USERNAME = "uploader"
PASSWORD = "Upload123456"  # Must be 8+ characters with uppercase
EMAIL = "uploader@example.com"  # Valid email domain

# Document type mapping based on filename
def get_document_type(filename):
    filename_lower = filename.lower()
    if "balance" in filename_lower or "balance_sheet" in filename_lower:
        return "balance_sheet"
    elif "income" in filename_lower:
        return "income_statement"
    elif "cash" in filename_lower and "flow" in filename_lower:
        return "cash_flow"
    elif "rent" in filename_lower and "roll" in filename_lower:
        return "rent_roll"
    else:
        return "balance_sheet"  # Default

# Extract property code from filename
def get_property_code(filename):
    filename_upper = filename.upper()
    if "ESP" in filename_upper or "ESPLANADE" in filename_upper:
        return "ESP001"
    elif "HMND" in filename_upper or "HAMMOND" in filename_upper:
        return "HMND001"
    elif "TCSH" in filename_upper or "TUSCANY" in filename_upper:
        return "TCSH001"
    elif "WEND" in filename_upper or "WENDOVER" in filename_upper:
        return "WEND001"
    elif "OXFD" in filename_upper or "OXFORD" in filename_upper:
        return "OXFD001"
    else:
        return "TEST001"  # Default

# Extract year and month from filename
def get_period(filename):
    # Try to extract year
    import re
    year_match = re.search(r'20(\d{2})', filename)
    year = int(f"20{year_match.group(1)}") if year_match else 2024
    
    # Try to extract month or quarter
    if "1st" in filename.lower() or "qtr" in filename.lower() or "q1" in filename.lower():
        month = 3
    elif "2nd" in filename.lower() or "q2" in filename.lower():
        month = 6
    elif "3rd" in filename.lower() or "q3" in filename.lower():
        month = 9
    elif "4th" in filename.lower() or "q4" in filename.lower():
        month = 12
    else:
        month = 12  # Default to December
    
    return year, month

def main():
    print("🚀 REIMS Bulk PDF Upload Script")
    print("=" * 60)
    
    # Get all PDF files
    pdf_files = sorted(Path(PDFS_DIR).glob("*.pdf"))
    print(f"📄 Found {len(pdf_files)} PDF files")
    
    if not pdf_files:
        print("❌ No PDF files found in", PDFS_DIR)
        return 1
    
    # Login
    print(f"\n🔐 Logging in as {USERNAME}...")
    session = requests.Session()
    
    try:
        # Try to login with JSON
        response = session.post(
            f"{API_URL}/api/v1/auth/login",
            json={
                "username": USERNAME,
                "password": PASSWORD
            }
        )
        
        if response.status_code == 200:
            print("✅ Login successful")
        else:
            # Try to register if login fails
            print("ℹ️  Login failed, trying to register...")
            response = session.post(
                f"{API_URL}/api/v1/auth/register",
                json={
                    "email": EMAIL,
                    "username": USERNAME,
                    "password": PASSWORD
                }
            )
            if response.status_code in [200, 201]:
                print("✅ Registration successful")
                # Login again with JSON
                response = session.post(
                    f"{API_URL}/api/v1/auth/login",
                    json={
                        "username": USERNAME,
                        "password": PASSWORD
                    }
                )
                if response.status_code != 200:
                    print(f"❌ Login failed after registration: {response.status_code}")
                    return 1
            else:
                print(f"❌ Registration failed: {response.status_code}")
                print(response.text)
                return 1
    except Exception as e:
        print(f"❌ Auth error: {e}")
        return 1
    
    # Get properties
    print("\n📊 Fetching properties...")
    try:
        response = session.get(f"{API_URL}/api/v1/properties")
        properties = response.json()
        property_map = {p["property_code"]: p["id"] for p in properties}
        print(f"✅ Found {len(properties)} properties: {list(property_map.keys())}")
    except Exception as e:
        print(f"❌ Error fetching properties: {e}")
        return 1
    
    # Upload each PDF
    print("\n📤 Uploading PDFs...")
    print("=" * 60)
    
    uploaded = 0
    failed = 0
    
    for pdf_file in pdf_files:
        filename = pdf_file.name
        property_code = get_property_code(filename)
        document_type = get_document_type(filename)
        year, month = get_period(filename)
        
        print(f"\n📄 {filename}")
        print(f"   Property: {property_code}, Type: {document_type}, Period: {year}/{month:02d}")
        
        if property_code not in property_map:
            print(f"   ⚠️  Skipping: Property {property_code} not found")
            failed += 1
            continue
        
        try:
            with open(pdf_file, 'rb') as f:
                files = {'file': (filename, f, 'application/pdf')}
                data = {
                    'property_code': property_code,
                    'document_type': document_type,
                    'period_year': year,
                    'period_month': month,
                    'force_overwrite': 'false'
                }
                
                response = session.post(
                    f"{API_URL}/api/v1/documents/upload",
                    files=files,
                    data=data
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    upload_id = result.get('id', 'unknown')
                    print(f"   ✅ Uploaded successfully (ID: {upload_id})")
                    uploaded += 1
                else:
                    print(f"   ❌ Upload failed: {response.status_code}")
                    print(f"      {response.text[:200]}")
                    failed += 1
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1
        
        # Small delay to avoid overwhelming the system
        time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Upload Summary")
    print("=" * 60)
    print(f"✅ Uploaded: {uploaded}")
    print(f"❌ Failed:   {failed}")
    print(f"📄 Total:    {len(pdf_files)}")
    
    if uploaded > 0:
        print("\n🔄 Extractions are now running in the background...")
        print("   Monitor progress at: http://localhost:5173")
        print("   Or check Celery: http://localhost:5555")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

