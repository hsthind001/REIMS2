# MinIO File Organization - REIMS2

**Created**: November 5, 2025  
**Structure**: Property → Year → Document Type  
**Total Files**: 28 PDFs

---

## Folder Structure

MinIO Bucket: `reims`

```
reims/
├── ESP001-Eastern-Shore-Plaza/
│   ├── 2023/
│   │   ├── balance-sheet/
│   │   │   └── ESP_2023_Balance_Sheet.pdf (3.5 KB)
│   │   ├── income-statement/
│   │   │   └── ESP_2023_Income_Statement.pdf (8.5 KB)
│   │   └── cash-flow/
│   │       └── ESP_2023_Cash_Flow_Statement.pdf (24.9 KB)
│   ├── 2024/
│   │   ├── balance-sheet/
│   │   │   └── ESP_2024_Balance_Sheet.pdf (8.2 KB)
│   │   ├── income-statement/
│   │   │   └── ESP_2024_Income_Statement.pdf (13.7 KB)
│   │   └── cash-flow/
│   │       └── ESP_2024_Cash_Flow_Statement.pdf (25.0 KB)
│   └── 2025/
│       └── rent-roll/
│           └── ESP_2025_Rent_Roll_April.pdf (40.4 KB)
│
├── HMND001-Hammond-Aire/
│   ├── 2023/ (3 files: balance-sheet, income-statement, cash-flow)
│   ├── 2024/ (3 files: balance-sheet, income-statement, cash-flow)
│   └── 2025/ (rent-roll)
│
├── TCSH001-The-Crossings/
│   ├── 2023/ (3 files: balance-sheet, income-statement, cash-flow)
│   ├── 2024/ (3 files: balance-sheet, income-statement, cash-flow)
│   └── 2025/ (rent-roll)
│
└── WEND001-Wendover-Commons/
    ├── 2023/ (3 files: balance-sheet, income-statement, cash-flow)
    ├── 2024/ (3 files: balance-sheet, income-statement, cash-flow)
    └── 2025/ (rent-roll)
```

---

## Naming Conventions

### Property Folder Format:
`{PROPERTY_CODE}-{ABBREVIATED_NAME}`

Examples:
- `ESP001-Eastern-Shore-Plaza`
- `HMND001-Hammond-Aire`
- `TCSH001-The-Crossings`
- `WEND001-Wendover-Commons`

### Year Folders:
- Simple numeric: `2023`, `2024`, `2025`

### Document Type Folders:
- `balance-sheet/`
- `income-statement/`
- `cash-flow/`
- `rent-roll/`

### File Naming:
`{PROPERTY_ABBR}_{YEAR}_{TYPE}.pdf`

Examples:
- `ESP_2023_Balance_Sheet.pdf`
- `HMND_2024_Cash_Flow_Statement.pdf`
- `TCSH_2025_Rent_Roll_April.pdf`

---

## File Inventory

### ESP001 - Eastern Shore Plaza (7 files)
| Year | Document Type | Filename | Size |
|------|---------------|----------|------|
| 2023 | Balance Sheet | ESP_2023_Balance_Sheet.pdf | 3.5 KB |
| 2023 | Income Statement | ESP_2023_Income_Statement.pdf | 8.5 KB |
| 2023 | Cash Flow | ESP_2023_Cash_Flow_Statement.pdf | 24.9 KB |
| 2024 | Balance Sheet | ESP_2024_Balance_Sheet.pdf | 8.2 KB |
| 2024 | Income Statement | ESP_2024_Income_Statement.pdf | 13.7 KB |
| 2024 | Cash Flow | ESP_2024_Cash_Flow_Statement.pdf | 25.0 KB |
| 2025 | Rent Roll | ESP_2025_Rent_Roll_April.pdf | 40.4 KB |

### HMND001 - Hammond Aire Shopping Center (7 files)
| Year | Document Type | Filename | Size |
|------|---------------|----------|------|
| 2023 | Balance Sheet | HMND_2023_Balance_Sheet.pdf | 3.5 KB |
| 2023 | Income Statement | HMND_2023_Income_Statement.pdf | 8.6 KB |
| 2023 | Cash Flow | HMND_2023_Cash_Flow_Statement.pdf | 24.9 KB |
| 2024 | Balance Sheet | HMND_2024_Balance_Sheet.pdf | 8.2 KB |
| 2024 | Income Statement | HMND_2024_Income_Statement.pdf | 13.8 KB |
| 2024 | Cash Flow | HMND_2024_Cash_Flow_Statement.pdf | 25.2 KB |
| 2025 | Rent Roll | HMND_2025_Rent_Roll_April.pdf | 59.0 KB |

### TCSH001 - The Crossings of Spring Hill (7 files)
| Year | Document Type | Filename | Size |
|------|---------------|----------|------|
| 2023 | Balance Sheet | TCSH_2023_Balance_Sheet.pdf | 3.6 KB |
| 2023 | Income Statement | TCSH_2023_Income_Statement.pdf | 8.0 KB |
| 2023 | Cash Flow | TCSH_2023_Cash_Flow_Statement.pdf | 24.6 KB |
| 2024 | Balance Sheet | TCSH_2024_Balance_Sheet.pdf | 3.7 KB |
| 2024 | Income Statement | TCSH_2024_Income_Statement.pdf | 7.4 KB |
| 2024 | Cash Flow | TCSH_2024_Cash_Flow_Statement.pdf | 24.8 KB |
| 2025 | Rent Roll | TCSH_2025_Rent_Roll_April.pdf | 60.2 KB |

### WEND001 - Wendover Commons (7 files)
| Year | Document Type | Filename | Size |
|------|---------------|----------|------|
| 2023 | Balance Sheet | WEND_2023_Balance_Sheet.pdf | 3.3 KB |
| 2023 | Income Statement | WEND_2023_Income_Statement.pdf | 7.6 KB |
| 2023 | Cash Flow | WEND_2023_Cash_Flow_Statement.pdf | 24.4 KB |
| 2024 | Balance Sheet | WEND_2024_Balance_Sheet.pdf | 3.5 KB |
| 2024 | Income Statement | WEND_2024_Income_Statement.pdf | 7.4 KB |
| 2024 | Cash Flow | WEND_2024_Cash_Flow_Statement.pdf | 24.7 KB |
| 2025 | Rent Roll | WEND_2025_Rent_Roll_April.pdf | 28.9 KB |

**Total Size**: ~540 KB across 28 files

---

## Benefits of This Organization

### 1. Property-Centric Access
- Quick access to all documents for a specific property
- Natural hierarchy matching business workflow
- Easy to see complete financial history per property

### 2. Year-Based Timeline
- Chronological organization within each property
- Easy to compare year-over-year performance
- Supports multi-year analysis

### 3. Document Type Segmentation
- Separate folders for each financial statement type
- Quick access to specific document categories
- Prevents file clutter

### 4. Standardized Naming
- Consistent file names across all properties
- No spaces (URL-friendly)
- Predictable patterns for programmatic access

---

## Accessing Files

### Via MinIO Console (Web UI)
**URL**: http://localhost:9001  
**Username**: minioadmin  
**Password**: minioadmin

Navigate: Buckets → reims → Select property folder

### Via MinIO Python SDK (Programmatic)

```python
from minio import Minio

client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

# Get specific file
file_data = client.get_object(
    "reims",
    "ESP001-Eastern-Shore-Plaza/2023/cash-flow/ESP_2023_Cash_Flow_Statement.pdf"
)

# List all files for a property
objects = client.list_objects("reims", prefix="ESP001-Eastern-Shore-Plaza/", recursive=True)
```

### Via REIMS2 Backend

Files are accessible through the MinIO client configured in:
- `backend/app/db/minio_client.py`
- Endpoint: `minio:9000` (internal Docker network)
- Bucket: `reims`

---

## Adding New Files

### For New Documents:
1. Upload to MinIO Console (http://localhost:9001)
2. Navigate to: `{PROPERTY_CODE}-{NAME}/{YEAR}/{DOC_TYPE}/`
3. Click "Upload" and select file
4. Use naming convention: `{PROP}_{YEAR}_{TYPE}.pdf`

### For New Properties:
1. Create folder structure: `{CODE}-{NAME}/`
2. Create year subfolders: `2023/`, `2024/`, etc.
3. Create document type subfolders in each year
4. Upload files following naming convention

### Automated Upload:
Use the included scripts:
- `/home/gurpyar/Documents/R/REIMS2/upload_to_minio.py` (Python)
- `/home/gurpyar/Documents/R/REIMS2/organize_minio.sh` (Bash)

---

## Maintenance

### Verification:
Check folder structure and file count:
```bash
docker exec reims-backend python3 -c "
from minio import Minio
client = Minio('minio:9000', access_key='minioadmin', secret_key='minioadmin', secure=False)
objects = list(client.list_objects('reims', recursive=True))
print(f'Total objects: {len(objects)}')
for obj in objects:
    print(f'  {obj.object_name}')
"
```

### Backup:
MinIO data is persisted in Docker volume: `reims2_minio-data`

To backup:
```bash
docker run --rm -v reims2_minio-data:/data -v $(pwd):/backup alpine tar czf /backup/minio-backup.tar.gz /data
```

### Cleanup:
To remove all files (if needed):
```bash
# Use MinIO Console or:
docker exec reims-backend python3 -c "
from minio import Minio
client = Minio('minio:9000', access_key='minioadmin', secret_key='minioadmin', secure=False)
objects = client.list_objects('reims', recursive=True)
for obj in objects:
    client.remove_object('reims', obj.object_name)
print('All files removed')
"
```

---

## Migration Notes

**Previous Storage**: `/home/gurpyar/REIMS_Uploaded` (flat directory)  
**New Storage**: MinIO bucket with hierarchical structure  
**Original Files**: Preserved in `/home/gurpyar/REIMS_Uploaded`  
**Migration Date**: November 5, 2025  
**Files Migrated**: 28 PDFs

---

## Future Enhancements

- [ ] Integrate MinIO upload in REIMS2 UI
- [ ] Add automatic folder creation for new properties
- [ ] Implement file versioning for updated documents
- [ ] Add metadata tags (upload date, user, document version)
- [ ] Create API endpoints for MinIO file operations
- [ ] Add thumbnail generation for PDF previews
- [ ] Implement access controls per property

---

**Last Updated**: November 5, 2025  
**Status**: ✅ Active and Organized

