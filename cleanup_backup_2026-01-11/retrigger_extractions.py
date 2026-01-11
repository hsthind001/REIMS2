#!/usr/bin/env python3
"""
Retrigger extraction for failed rent roll documents
"""
import sys
sys.path.insert(0, '/home/gurpyar/Documents/R/REIMS2/backend')

from celery_worker import extract_document

# Failed document IDs
upload_ids = [29, 30, 31, 32]

print("🔄 Triggering extraction for 4 failed rent roll documents...")
for upload_id in upload_ids:
    print(f"   Triggering extraction for upload_id={upload_id}")
    task = extract_document.delay(upload_id)
    print(f"   ✅ Task ID: {task.id}")

print("\n✅ All 4 extraction tasks triggered successfully!")
print("Monitor progress at: http://localhost:5555 (Flower)")

