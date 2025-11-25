# Download Regenerated PDF - Quick Guide

## Method 1: Using Python Script (Easiest)

### If you know the upload_id:
```bash
cd /home/singh/REIMS2/backend
python scripts/download_regenerated_pdf.py <upload_id>
```

### If you know property/year/month:
```bash
cd /home/singh/REIMS2/backend
python scripts/download_regenerated_pdf.py --property esp --year 2023 --month 12
```

### With custom output filename:
```bash
python scripts/download_regenerated_pdf.py <upload_id> --output my_regenerated_pdf.pdf
```

## Method 2: Using curl (Direct API Call)

### Step 1: Find your upload_id
```bash
# List ESP uploads
curl "http://localhost:8000/api/v1/documents/uploads?property_code=esp&document_type=income_statement&limit=10"
```

### Step 2: Download the PDF
```bash
curl -X GET "http://localhost:8000/api/v1/documents/uploads/{upload_id}/regenerate-pdf" \
  --output regenerated_esp_2023_income_statement.pdf
```

## Method 3: Using Python Directly

```python
import requests

upload_id = 123  # Replace with your upload_id
url = f"http://localhost:8000/api/v1/documents/uploads/{upload_id}/regenerate-pdf"

response = requests.get(url)
response.raise_for_status()

with open("regenerated_income_statement.pdf", "wb") as f:
    f.write(response.content)

print("PDF downloaded successfully!")
```

## Finding Your Upload ID

### Option A: Query Database
```python
from app.db.database import SessionLocal
from app.models.document_upload import DocumentUpload
from app.models.property import Property
from app.models.financial_period import FinancialPeriod

db = SessionLocal()
upload = db.query(DocumentUpload).join(Property).join(FinancialPeriod).filter(
    Property.property_code == "ESP",
    FinancialPeriod.period_year == 2023,
    FinancialPeriod.period_month == 12,
    DocumentUpload.document_type == "income_statement"
).first()

print(f"Upload ID: {upload.id}")
```

### Option B: Use API
```bash
curl "http://localhost:8000/api/v1/documents/uploads?property_code=esp&year=2023&month=12&document_type=income_statement"
```

