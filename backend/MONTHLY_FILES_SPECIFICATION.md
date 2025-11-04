# Monthly Financial Files Specification

Complete specification for monthly financial document uploads in REIMS2.

## Overview

REIMS2 requires **monthly** financial documents for accurate tracking and reporting. Currently, we have **annual** files (28 files for 2023-2024). For full monthly coverage, we need **288 monthly files** (4 properties × 2 years × 12 months × 3 document types).

---

## File Naming Convention

### Standard Format

```
{PropertyCode}_{Year}_{Month:02d}_{DocumentType}.pdf
```

### Components

| Component | Format | Description | Examples |
|-----------|--------|-------------|----------|
| PropertyCode | XXXNNN | 3-5 uppercase letters + 3 digits | ESP001, HMND001, TCSH001, WEND001 |
| Year | YYYY | 4-digit year | 2023, 2024, 2025 |
| Month | MM | 2-digit month (zero-padded) | 01, 02, ..., 12 |
| DocumentType | string | Document type | balance_sheet, income_statement, cash_flow, rent_roll |

### Examples

**Correct:**
```
ESP001_2024_01_balance_sheet.pdf
ESP001_2024_01_income_statement.pdf
ESP001_2024_01_cash_flow.pdf
ESP001_2024_02_balance_sheet.pdf
HMND001_2024_12_balance_sheet.pdf
TCSH001_2024_06_income_statement.pdf
WEND001_2024_03_cash_flow.pdf
```

**Incorrect:**
```
❌ ESP_2024_1_balance_sheet.pdf          # Month not zero-padded
❌ esp001_2024_01_balance_sheet.pdf      # Lowercase property code
❌ ESP001-2024-01-balance_sheet.pdf      # Wrong separator (dash instead of underscore)
❌ ESP001_2024_01_BalanceSheet.pdf       # Document type has capitals
❌ 2024_01_ESP001_balance_sheet.pdf      # Wrong order
❌ ESP001_24_01_balance_sheet.pdf        # 2-digit year
```

---

## Document Types

### Required Monthly Documents

| Document Type | Filename Value | Required | Frequency |
|---------------|---------------|----------|-----------|
| Balance Sheet | `balance_sheet` | Yes | Monthly |
| Income Statement | `income_statement` | Yes | Monthly |
| Cash Flow Statement | `cash_flow` | Yes | Monthly |
| Rent Roll | `rent_roll` | Optional | Monthly or Quarterly |

### Minimum Requirements

Each property must have **3 files per month**:
1. Balance Sheet
2. Income Statement  
3. Cash Flow Statement

**Total per property per year:** 36 files (12 months × 3 documents)

**Total for 4 properties per year:** 144 files

**Total for 2 years (2023-2024):** 288 files

---

## Directory Structure

### Recommended Organization

```
monthly_files/
├── 2023/
│   ├── ESP001/
│   │   ├── ESP001_2023_01_balance_sheet.pdf
│   │   ├── ESP001_2023_01_income_statement.pdf
│   │   ├── ESP001_2023_01_cash_flow.pdf
│   │   ├── ESP001_2023_02_balance_sheet.pdf
│   │   ├── ESP001_2023_02_income_statement.pdf
│   │   ├── ESP001_2023_02_cash_flow.pdf
│   │   └── ...
│   ├── HMND001/
│   │   ├── HMND001_2023_01_balance_sheet.pdf
│   │   └── ...
│   ├── TCSH001/
│   │   └── ...
│   └── WEND001/
│       └── ...
└── 2024/
    ├── ESP001/
    │   └── ...
    ├── HMND001/
    │   └── ...
    ├── TCSH001/
    │   └── ...
    └── WEND001/
        └── ...
```

### Flat Structure (Also Supported)

```
monthly_files/
├── ESP001_2023_01_balance_sheet.pdf
├── ESP001_2023_01_income_statement.pdf
├── ESP001_2023_01_cash_flow.pdf
├── ESP001_2023_02_balance_sheet.pdf
├── ...
├── HMND001_2023_01_balance_sheet.pdf
├── ...
```

Both structures work with the bulk upload tool!

---

## Required Files Checklist

### ESP001 - Esplanade Shopping Center

**2023 (36 files):**
- [ ] January (3 files): balance_sheet, income_statement, cash_flow
- [ ] February (3 files)
- [ ] March (3 files)
- [ ] April (3 files)
- [ ] May (3 files)
- [ ] June (3 files)
- [ ] July (3 files)
- [ ] August (3 files)
- [ ] September (3 files)
- [ ] October (3 files)
- [ ] November (3 files)
- [ ] December (3 files)

**2024 (36 files):**
- [ ] All 12 months × 3 documents

**Total:** 72 files

### HMND001 - Hammond Aire Shopping Center

**Total:** 72 files (same structure as ESP001)

### TCSH001 - Town Center Shopping

**Total:** 72 files (same structure as ESP001)

### WEND001 - Wendover Commons

**Total:** 72 files (same structure as ESP001)

---

## Bulk Upload

### Upload All Monthly Files

```bash
python3 scripts/bulk_upload_monthly.py --directory /path/to/monthly_files
```

### Upload Specific Property

```bash
python3 scripts/bulk_upload_monthly.py --directory /path/to/monthly_files --property ESP001
```

### Upload Specific Year

```bash
python3 scripts/bulk_upload_monthly.py --directory /path/to/monthly_files --year 2024
```

### Dry Run (Analyze Without Uploading)

```bash
python3 scripts/bulk_upload_monthly.py --directory /path/to/monthly_files --dry-run
```

This shows:
- Valid file count
- Invalid filenames
- Missing months
- Missing documents per month

---

## Gap Analysis

### Current State

We have **28 annual files**:
- 6-7 files per property
- Years: 2023, 2024
- Mostly December periods + some Q1 2025 rent rolls

### Missing Files

**Per Property:**
- 2023: 36 monthly files needed (we have 3 annual = ~3 months worth)
- 2024: 36 monthly files needed (we have 3 annual = ~3 months worth)
- **Gap:** ~33 months worth of data per property

**Total Gap:** ~264 monthly files needed

### Impact of Missing Monthly Data

**Current (Annual):**
- 1 balance sheet per year
- 1 income statement per year
- 1 cash flow per year
- **Limitations:** No month-over-month comparisons, no seasonal analysis, no monthly tracking

**With Monthly Data:**
- 12 balance sheets per year
- 12 income statements per year
- 12 cash flow statements per year
- **Benefits:** Full trend analysis, seasonality tracking, accurate monthly reporting

---

## File Content Requirements

### Balance Sheet

**Required sections:**
- Assets (Current & Non-current)
- Liabilities (Current & Long-term)
- Equity

**Format:**
- PDF (digital preferred, scanned acceptable)
- Clear account codes (e.g., 1110-0000)
- Clear account names
- Dollar amounts clearly visible
- Date clearly indicated

### Income Statement

**Required sections:**
- Revenue (by category)
- Operating Expenses
- Net Operating Income (NOI)
- Net Income

**Format:**
- Period Amount column
- Year-to-Date (YTD) column (optional but recommended)
- Percentage columns (optional)

### Cash Flow Statement

**Required sections:**
- Operating Activities
- Investing Activities
- Financing Activities
- Beginning & Ending Cash Balance

---

## Quality Guidelines

### File Quality

**✓ Acceptable:**
- Digital PDFs (best)
- High-resolution scans (300+ DPI)
- Clear, readable text
- Properly formatted tables

**✗ Not Acceptable:**
- Blurry or low-resolution scans
- Handwritten documents
- Photos of documents
- Password-protected PDFs
- Corrupted files

### Content Requirements

**Each document must have:**
1. Property name or identifier
2. Period date (month/year)
3. Account codes (4-digit-4-digit format preferred)
4. Account names
5. Dollar amounts
6. Totals and subtotals

**Missing any of these?** → May result in incomplete extraction

---

## Handling Missing Months

### Option 1: Skip Missing Months

If data for certain months doesn't exist, that's okay. Upload only available months.

**Example:**
```
✓ ESP001_2024_01_balance_sheet.pdf
✗ ESP001_2024_02_balance_sheet.pdf  # Missing
✓ ESP001_2024_03_balance_sheet.pdf
```

System will track which months have data.

### Option 2: Duplicate Adjacent Month (Not Recommended)

If you must have data for a missing month, you can duplicate an adjacent month's file.

**But:**
- Mark it clearly in notes
- Use with caution
- Understand data will be identical

### Option 3: Interpolation (Future Feature)

Future versions may support automatic interpolation for missing months.

---

## Validation

### Pre-Upload Validation

Before uploading, verify:

```bash
# Check filenames
python3 scripts/bulk_upload_monthly.py --directory /path --dry-run

# Check file sizes (should be > 1KB)
find /path -name "*.pdf" -size +1k

# Check file validity
find /path -name "*.pdf" -exec file {} \; | grep -v "PDF document"
```

### Post-Upload Validation

After uploading:

```bash
# Check upload status
python3 scripts/verify_data_quality.py --all

# Generate HTML report
python3 scripts/verify_data_quality.py --all --html

# Check specific property
python3 scripts/verify_data_quality.py --property ESP001
```

---

## Conversion from Annual to Monthly

If you have annual files and need to create monthly structure:

### Manual Method

1. Identify month represented by annual file (usually December)
2. Rename following convention:
   ```bash
   # From: ESP 2024 Balance Sheet.pdf
   # To:   ESP001_2024_12_balance_sheet.pdf
   ```

### Script (If Available)

```bash
# Future script to help with conversion
python3 scripts/convert_annual_to_monthly_names.py --directory /path
```

---

## Automation

### Watch Directory (Future Feature)

```bash
# Auto-upload new files placed in directory
python3 scripts/watch_and_upload.py --directory /path/watch
```

### Scheduled Uploads (Cron)

```bash
# Add to crontab
0 2 * * * cd /path/to/REIMS2/backend && python3 scripts/bulk_upload_monthly.py --directory /path/monthly_files
```

---

## API Integration

### Upload via API

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "property_code=ESP001" \
  -F "period_year=2024" \
  -F "period_month=6" \
  -F "document_type=balance_sheet" \
  -F "file=@ESP001_2024_06_balance_sheet.pdf"
```

### Batch Upload via Script

```python
import requests
import os

API_URL = "http://localhost:8000/api/v1"
files = [...]  # List of files

for file_path in files:
    # Parse filename
    property_code, year, month, doc_type = parse_filename(file_path)
    
    # Upload
    with open(file_path, 'rb') as f:
        response = requests.post(
            f"{API_URL}/documents/upload",
            files={'file': f},
            data={
                'property_code': property_code,
                'period_year': year,
                'period_month': month,
                'document_type': doc_type
            }
        )
```

---

## Support

### Questions?

- Review: [DATA_MANAGEMENT.md](DATA_MANAGEMENT.md)
- Check API docs: http://localhost:8000/docs
- View logs: `docker logs reims-backend -f`

### Common Issues

**Issue:** Filename not recognized

**Solution:** Verify exact format:
```
{PropertyCode}_{Year}_{Month:02d}_{DocumentType}.pdf
```

**Issue:** Duplicate file error

**Solution:** Files are deduplicated by MD5 hash. Change content or delete old upload.

**Issue:** Missing property error

**Solution:** Ensure property exists:
```bash
curl http://localhost:8000/api/v1/properties/{PropertyCode}
```

---

## Summary

**Current:** 28 annual files ✓

**Goal:** 288 monthly files

**Next Steps:**
1. Organize monthly PDFs following naming convention
2. Run bulk upload in dry-run mode
3. Review analysis output
4. Upload when ready
5. Verify data quality

**Remember:** Quality over quantity. Better to have 12 accurate months than 12 months of poor-quality data!

