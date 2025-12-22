# AI/ML Models Guide for REIMS2

## Overview

REIMS2 uses multiple AI/ML models for document extraction and OCR. These models are downloaded on-demand when first used and cached in a Docker volume for subsequent use.

---

## Model Cache Location

**Docker Volume**: `reims2_ai-models-cache`  
**Container Path**: `/app/.cache/huggingface`  
**Host Path**: `/var/lib/docker/volumes/reims2_ai-models-cache/_data`

This volume is shared between:
- `reims-backend` (FastAPI application)
- `reims-celery-worker` (Background tasks)

---

## Models Used

### 1. LayoutLMv3 (Document Understanding)

**Model**: `microsoft/layoutlmv3-base`  
**Purpose**: Document layout analysis and token classification  
**Used For**: 
- Extracting structured data from financial documents
- Understanding document layout (tables, headers, values)
- Token-level classification

**Size**: ~500MB (approximate)

**Components Downloaded**:
- Model weights (`pytorch_model.bin`)
- Configuration (`config.json`)
- Tokenizer files
- Processor configuration

**First Download Trigger**:
- First document extraction via `/api/v1/extraction/extract`
- Automatic download on first import of `LayoutLMv3Processor`

**Cache Structure**:
```
.cache/huggingface/
└── hub/
    └── models--microsoft--layoutlmv3-base/
        ├── blobs/
        │   └── [large binary files]
        ├── refs/
        └── snapshots/
```

---

### 2. EasyOCR Models

**Purpose**: Optical Character Recognition for scanned documents  
**Used For**: 
- Text extraction from PDFs without text layer
- Image-based documents
- Scanned financial statements

**Models Downloaded**:
- `craft_mlt_25k.pth` (~90MB) - Text detection
- `english_g2.pth` (~45MB) - English text recognition
- Character set files

**Size**: ~150MB total

**First Download Trigger**:
- First OCR extraction when `easyocr.Reader(['en'])` is initialized
- Typically during PDF processing with no text layer

**Cache Structure**:
```
.cache/huggingface/
└── easyocr/
    ├── craft_mlt_25k.pth
    ├── english_g2.pth
    └── character/
```

---

### 3. Tesseract OCR (System Binary)

**Purpose**: Alternative OCR engine  
**Installation**: System package (pre-installed in Docker image)  
**Used For**: Backup OCR when EasyOCR is not suitable

**No Download Required**: Installed via `apt-get install tesseract-ocr`

---

## Total Storage Requirements

| Component | Size | Status |
|-----------|------|--------|
| LayoutLMv3 | ~500MB | Downloaded on first use |
| EasyOCR Models | ~150MB | Downloaded on first use |
| Tesseract (system) | ~5MB | Pre-installed |
| **Total** | **~655MB** | |

---

## Model Download Process

### First Extraction Timeline

When you trigger the first document extraction:

1. **T+0s**: API request received
2. **T+1s**: LayoutLMv3 import triggered
3. **T+2s**: Download starts from Hugging Face Hub
4. **T+30-60s**: LayoutLMv3 download completes (~500MB @ 10MB/s)
5. **T+60s**: Model loaded into memory
6. **T+65s**: Extraction processing begins
7. **T+70-90s**: Extraction complete

**First extraction**: 1-2 minutes (with download)  
**Subsequent extractions**: 10-30 seconds (cached)

---

## Checking Model Cache

### View Cache Contents

```bash
# Check if models are cached
docker exec reims-backend ls -lh /app/.cache/huggingface/hub/

# Check cache size
docker exec reims-backend du -sh /app/.cache/huggingface/

# View LayoutLMv3 cache
docker exec reims-backend find /app/.cache/huggingface/ -name "*layoutlmv3*" -type d
```

### View Volume Size

```bash
# Check Docker volume size
docker system df -v | grep ai-models-cache

# Detailed volume inspection
docker volume inspect reims2_ai-models-cache
```

---

## Model Download Monitoring

### Backend Logs During First Download

```bash
# Watch real-time logs
docker compose logs -f backend

# Example output:
# INFO:     Downloading model from https://huggingface.co/microsoft/layoutlmv3-base
# INFO:     Download progress: 25%
# INFO:     Download progress: 50%
# INFO:     Download progress: 75%
# INFO:     Download complete
# INFO:     Loading model into memory...
# INFO:     Model ready
```

### Celery Worker Logs

```bash
# Watch worker logs
docker compose logs -f celery-worker

# Example output during extraction task:
# [INFO] Starting document extraction task
# [INFO] Loading LayoutLMv3 model...
# [INFO] Model loaded successfully
# [INFO] Processing document...
```

---

## Pre-downloading Models (Optional)

To download models before first use:

### Option 1: Trigger a Test Extraction

```bash
# Upload a test document via API
curl -X POST http://localhost:8000/api/v1/extraction/extract \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test-document.pdf" \
  -F "document_type=balance_sheet"
```

### Option 2: Manual Download in Container

```bash
# Enter backend container
docker exec -it reims-backend bash

# Run Python to download models
python3 << EOF
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
print("Downloading LayoutLMv3...")
processor = LayoutLMv3Processor.from_pretrained("microsoft/layoutlmv3-base")
model = LayoutLMv3ForTokenClassification.from_pretrained("microsoft/layoutlmv3-base")
print("Download complete!")
EOF

# Download EasyOCR models
python3 << EOF
import easyocr
print("Downloading EasyOCR models...")
reader = easyocr.Reader(['en'])
print("Download complete!")
EOF

# Exit container
exit
```

---

## Troubleshooting

### Issue: Model Download Fails

**Symptoms**:
- Extraction takes very long
- Error: "Connection timeout"
- Error: "Unable to download model"

**Solutions**:
1. Check internet connection
2. Check Hugging Face Hub status: https://status.huggingface.co/
3. Verify Docker has network access
4. Check proxy settings if behind corporate firewall

### Issue: Out of Disk Space

**Symptoms**:
- Error: "No space left on device"
- Docker volume full

**Solutions**:
```bash
# Check Docker disk usage
docker system df

# Clean up unused images/volumes
docker system prune -a --volumes

# Increase Docker Desktop disk allocation (Settings > Resources > Disk)
```

### Issue: Model Loading is Slow

**Symptoms**:
- Long delay before extraction starts (even after download)

**Explanation**: LayoutLMv3 is a large model (~500MB) that needs to be loaded into memory. This is normal on first use per container restart.

**Optimization**:
- Ensure sufficient RAM allocated to Docker (4GB+ recommended)
- Consider keeping containers running (don't restart frequently)

---

## Performance Considerations

### Memory Usage

| Component | RAM Required | Notes |
|-----------|-------------|-------|
| LayoutLMv3 Model | ~2GB | Loaded into memory during extraction |
| EasyOCR | ~500MB | Loaded when needed |
| PyTorch | ~1GB | Framework overhead |
| **Total** | **~3.5GB** | Per worker process |

### Recommendations

- **Minimum RAM**: 4GB allocated to Docker
- **Recommended RAM**: 8GB for smooth operation
- **Concurrent Extractions**: Limit to 2-3 simultaneous to avoid OOM

### Current Resource Allocation

Based on `docker stats`:
- **celery-worker**: 1.9GB / 3.6GB (52.67%) ✅ Good
- **backend**: 391MB / 3.6GB (10.46%) ✅ Good

---

## Model Versions

Current versions in `requirements.txt`:

```
transformers==4.44.2
tokenizers==0.19.1  # Fixed: Compatible with transformers 4.44.2
torch==2.6.0
torchvision==0.21.0
easyocr==1.7.2
```

---

## Updating Models

### Upgrade Transformers/LayoutLMv3

```bash
# 1. Update requirements.txt
# transformers==4.50.0  # New version

# 2. Rebuild base image
cd /home/singh/REIMS2/backend
docker build -f Dockerfile.base -t reims-base:latest .

# 3. Rebuild services
cd /home/singh/REIMS2
docker compose up -d --build backend celery-worker

# 4. Clear old cache (optional)
docker volume rm reims2_ai-models-cache
docker volume create reims2_ai-models-cache

# 5. Test extraction to download new models
```

---

## Best Practices

1. **First Deployment**: 
   - Allow 2-5 minutes for initial model download
   - Monitor logs during first extraction
   - Verify cache volume creation

2. **Production**:
   - Pre-download models before going live
   - Monitor disk usage regularly
   - Keep models cached between updates

3. **Development**:
   - Cache volume persists across container restarts
   - Only cleared on `docker volume rm` or system prune
   - Share cache between backend and celery-worker

4. **Monitoring**:
   - Check cache size monthly
   - Monitor memory usage during extractions
   - Log download times for performance tracking

---

## Related Documentation

- [LayoutLMv3 Model Card](https://huggingface.co/microsoft/layoutlmv3-base)
- [EasyOCR GitHub](https://github.com/JaidedAI/EasyOCR)
- [Transformers Documentation](https://huggingface.co/docs/transformers)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)

---

**Last Updated**: November 11, 2025  
**REIMS2 Version**: 1.0.0  
**Models Version**: LayoutLMv3 (base), EasyOCR 1.7.2

