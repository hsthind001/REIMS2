# Tesseract OCR - Optical Character Recognition

Tesseract is an open-source OCR engine for extracting text from images and PDFs.

## What is Tesseract OCR?

Tesseract OCR provides:
- **Text Extraction** - Extract text from images (JPG, PNG, TIFF, etc.)
- **PDF OCR** - Convert scanned PDFs to searchable text
- **Multi-Language Support** - Supports 100+ languages
- **Bounding Boxes** - Get coordinates of detected text
- **High Accuracy** - Industry-leading OCR accuracy

## Installation

### System Package
**Installed**: Tesseract OCR 5.5.0
**Location**: `/usr/bin/tesseract`

### Python Libraries
- `pytesseract` - Python wrapper for Tesseract
- `Pillow` - Image processing library
- `pdf2image` - PDF to image conversion

## API Endpoints

### Extract Text from Image
```bash
POST /api/v1/ocr/image
Content-Type: multipart/form-data

# Example with curl:
curl -X POST http://localhost:8000/api/v1/ocr/image \
  -F "file=@document.jpg" \
  -F "lang=eng"
```

**Response:**
```json
{
    "text": "Extracted text content...",
    "language": "eng",
    "confidence": 89.5,
    "word_count": 150,
    "char_count": 850,
    "success": true
}
```

### Extract Text with Bounding Boxes
```bash
POST /api/v1/ocr/image/boxes
Content-Type: multipart/form-data

curl -X POST http://localhost:8000/api/v1/ocr/image/boxes \
  -F "file=@receipt.png"
```

**Response:**
```json
{
    "words": [
        {
            "text": "Hello",
            "confidence": 95,
            "left": 10,
            "top": 20,
            "width": 50,
            "height": 15
        }
    ],
    "total_words": 42,
    "image_width": 800,
    "image_height": 600,
    "success": true
}
```

### Extract Text from PDF
```bash
POST /api/v1/ocr/pdf
Content-Type: multipart/form-data

curl -X POST http://localhost:8000/api/v1/ocr/pdf \
  -F "file=@scanned.pdf" \
  -F "dpi=300"
```

**Response:**
```json
{
    "text": "Full text from all pages...",
    "pages": [
        {
            "page": 1,
            "text": "Page 1 content...",
            "confidence": 92.5,
            "word_count": 200
        }
    ],
    "total_pages": 5,
    "avg_confidence": 90.3,
    "success": true
}
```

### List Supported Languages
```bash
GET /api/v1/ocr/languages

curl http://localhost:8000/api/v1/ocr/languages
```

**Response:**
```json
{
    "languages": ["eng", "fra", "deu", "spa"],
    "count": 4
}
```

### Get Tesseract Version
```bash
GET /api/v1/ocr/version

curl http://localhost:8000/api/v1/ocr/version
```

### OCR Health Check
```bash
GET /api/v1/ocr/health

curl http://localhost:8000/api/v1/ocr/health
```

## Using the OCR Module Directly

### Extract Text from Image
```python
from app.utils.ocr import extract_text_from_image

# Load image file
with open("document.jpg", "rb") as f:
    image_data = f.read()

# Extract text
result = extract_text_from_image(
    image_data=image_data,
    lang="eng",
    config="--psm 6"  # Page segmentation mode
)

print(result["text"])
print(f"Confidence: {result['confidence']}%")
```

### Extract Text with Bounding Boxes
```python
from app.utils.ocr import extract_text_with_boxes

result = extract_text_with_boxes(image_data, lang="eng")

for word in result["words"]:
    print(f"Text: {word['text']}")
    print(f"Position: ({word['left']}, {word['top']})")
    print(f"Confidence: {word['confidence']}%")
```

### Extract Text from PDF
```python
from app.utils.ocr import extract_text_from_pdf

with open("scanned.pdf", "rb") as f:
    pdf_data = f.read()

result = extract_text_from_pdf(
    pdf_data=pdf_data,
    lang="eng",
    dpi=300  # Higher DPI = better quality but slower
)

print(result["text"])
print(f"Pages: {result['total_pages']}")
print(f"Avg confidence: {result['avg_confidence']}%")
```

## Supported File Formats

### Images
- **JPG/JPEG** - Most common format
- **PNG** - Best for screenshots
- **TIFF** - Best for scanning
- **BMP** - Windows bitmap
- **GIF** - Limited support
- **WEBP** - Modern format

### Documents
- **PDF** - Scanned PDFs only (not text-based)

## Language Support

### Currently Installed
- `eng` - English
- `osd` - Orientation and script detection

### Install Additional Languages
```bash
# French
sudo apt install tesseract-ocr-fra

# German
sudo apt install tesseract-ocr-deu

# Spanish
sudo apt install tesseract-ocr-spa

# Chinese Simplified
sudo apt install tesseract-ocr-chi-sim

# Arabic
sudo apt install tesseract-ocr-ara

# All languages (large download)
sudo apt install tesseract-ocr-all
```

### Available Language Codes
- `eng` - English
- `fra` - French
- `deu` - German
- `spa` - Spanish
- `ita` - Italian
- `por` - Portuguese
- `rus` - Russian
- `chi_sim` - Chinese Simplified
- `chi_tra` - Chinese Traditional
- `jpn` - Japanese
- `kor` - Korean
- `ara` - Arabic
- `hin` - Hindi

[Full list: https://github.com/tesseract-ocr/tessdata]

## Configuration Options

### Page Segmentation Modes (PSM)
Use the `config` parameter to set PSM:

```python
# Assume single column of text
config="--psm 6"

# Treat image as a single text line
config="--psm 7"

# Treat image as a single word
config="--psm 8"

# Sparse text with OSD
config="--psm 1"
```

**PSM Values:**
- 0 = Orientation and script detection (OSD) only
- 1 = Automatic page segmentation with OSD
- 3 = Fully automatic page segmentation (default)
- 6 = Assume a single uniform block of text
- 7 = Treat the image as a single text line
- 8 = Treat the image as a single word
- 11 = Sparse text (find as much text as possible)

### OCR Engine Modes (OEM)
```python
# Use LSTM engine (best accuracy)
config="--oem 1"

# Use legacy engine (faster)
config="--oem 0"

# Use both engines
config="--oem 2"
```

### Combined Configuration
```python
config="--psm 6 --oem 1"  # Single column + LSTM engine
```

## Integration Examples

### Process Uploaded Image
```python
from fastapi import UploadFile
from app.utils.ocr import extract_text_from_image

async def process_document(file: UploadFile):
    image_data = await file.read()
    result = extract_text_from_image(image_data, lang="eng")
    
    # Save to database
    document = Document(
        filename=file.filename,
        text_content=result["text"],
        confidence=result["confidence"]
    )
    db.add(document)
    db.commit()
    
    return result
```

### OCR with MinIO Storage
```python
from app.db.minio_client import download_file, upload_file
from app.utils.ocr import extract_text_from_image
import json

# Download image from MinIO
image_data = download_file("documents/scan001.jpg")

# Perform OCR
result = extract_text_from_image(image_data)

# Store extracted text
text_data = json.dumps(result).encode()
upload_file(text_data, "ocr-results/scan001.json", "application/json")
```

### Async OCR with Celery
```python
from app.core.celery_config import celery_app
from app.utils.ocr import extract_text_from_image
from app.db.minio_client import download_file

@celery_app.task
def process_document_async(filename: str):
    # Download from storage
    image_data = download_file(f"uploads/{filename}")
    
    # Perform OCR
    result = extract_text_from_image(image_data)
    
    # Process result
    # ... save to database, send notification, etc.
    
    return result
```

## Best Practices

### Image Preprocessing
For best results, preprocess images:

```python
from PIL import Image, ImageEnhance
import io

def preprocess_image(image_data: bytes) -> bytes:
    # Open image
    img = Image.open(io.BytesIO(image_data))
    
    # Convert to grayscale
    img = img.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    
    # Increase resolution (if small)
    if img.width < 1000:
        img = img.resize((img.width * 2, img.height * 2))
    
    # Save back to bytes
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()
```

### Image Quality Guidelines
- **Resolution**: Minimum 300 DPI
- **Format**: PNG or TIFF preferred
- **Contrast**: High contrast between text and background
- **Orientation**: Correct orientation (use --psm 0 for auto-detect)
- **Size**: Larger images give better results

### Performance Tips
1. **Use appropriate PSM mode** - Faster and more accurate
2. **Preprocess images** - Remove noise, increase contrast
3. **Lower DPI for PDFs** - Use 200 DPI instead of 300 for speed
4. **Use async processing** - Process large batches with Celery
5. **Cache results** - Store OCR results to avoid reprocessing

## Troubleshooting

### Low Confidence / Poor Results
```python
# Try different PSM modes
result = extract_text_from_image(img, config="--psm 6")

# Try different languages
result = extract_text_from_image(img, lang="eng+fra")

# Preprocess image
img = preprocess_image(img)
result = extract_text_from_image(img)
```

### Tesseract Not Found
```bash
# Check if installed
which tesseract

# Reinstall if needed
sudo apt install --reinstall tesseract-ocr
```

### Language Not Found
```bash
# List installed languages
tesseract --list-langs

# Install missing language
sudo apt install tesseract-ocr-LANG
```

### PDF Conversion Fails
```bash
# Install poppler-utils (required for pdf2image)
sudo apt install poppler-utils
```

## Command Line Usage

```bash
# Basic OCR
tesseract input.jpg output

# With specific language
tesseract input.jpg output -l fra

# With configuration
tesseract input.jpg output --psm 6 --oem 1

# Output to stdout
tesseract input.jpg stdout

# Get bounding boxes
tesseract input.jpg output tsv

# Get confidence data
tesseract input.jpg output -c save_best_choices=True
```

## Advanced Features

### Multi-Language OCR
```python
# English and French
result = extract_text_from_image(img, lang="eng+fra")

# Multiple languages
result = extract_text_from_image(img, lang="eng+fra+deu+spa")
```

### Custom Training
For specialized text (handwriting, special fonts):
1. Create training data
2. Train custom model
3. Use custom model with `--tessdata-dir`

See: https://github.com/tesseract-ocr/tesseract/wiki/TrainingTesseract-5

## Resources

- Tesseract Documentation: https://tesseract-ocr.github.io/
- pytesseract GitHub: https://github.com/madmaze/pytesseract
- Tesseract Language Data: https://github.com/tesseract-ocr/tessdata
- Best Practices: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html

## Testing

Test OCR with a sample image:
```bash
# Create test image
curl -o test.jpg https://tesseract-ocr.github.io/docs/basic-example.png

# Test OCR API
curl -X POST http://localhost:8000/api/v1/ocr/image \
  -F "file=@test.jpg"
```

## Performance Metrics

- **Simple Text**: ~0.5-2 seconds per image
- **Complex Layout**: ~2-5 seconds per image
- **PDF (per page)**: ~3-8 seconds per page
- **Accuracy**: 85-95% on good quality images

## Security Considerations

1. **File Size Limits** - Set max upload size
2. **File Type Validation** - Verify image format
3. **Timeout Limits** - Set processing timeouts
4. **Rate Limiting** - Limit OCR requests per user
5. **Content Sanitization** - Sanitize extracted text

## Production Deployment

- Use Celery for async processing
- Enable result caching in Redis
- Set up dedicated OCR workers
- Monitor resource usage (CPU/Memory intensive)
- Scale horizontally for high volume

