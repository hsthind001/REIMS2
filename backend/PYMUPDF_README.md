# PyMuPDF - Advanced PDF Processing

PyMuPDF (fitz) is a Python binding for MuPDF - a lightweight, high-performance PDF library for PDF manipulation, extraction, and conversion.

## What is PyMuPDF?

PyMuPDF provides:
- **Fast PDF Processing** - Much faster than other PDF libraries
- **Text Extraction** - Extract text with formatting and layout
- **PDF to Images** - Convert PDF pages to high-quality images
- **Image Extraction** - Extract embedded images from PDFs
- **PDF Manipulation** - Split, merge, compress PDFs
- **Watermarking** - Add text/image watermarks
- **Metadata** - Read and modify PDF metadata

## Installation

**Installed**: PyMuPDF 1.26.5
**Import as**: `import fitz`

## API Endpoints

### Extract Text from PDF
```bash
POST /api/v1/pdf/extract-text

curl -X POST http://localhost:8000/api/v1/pdf/extract-text \
  -F "file=@document.pdf"
```

**Response:**
```json
{
    "text": "Full extracted text...",
    "pages": [
        {
            "page": 1,
            "text": "Page 1 text...",
            "char_count": 500,
            "word_count": 85
        }
    ],
    "total_pages": 5,
    "total_chars": 2500,
    "total_words": 425,
    "success": true
}
```

### Get PDF Metadata
```bash
POST /api/v1/pdf/metadata

curl -X POST http://localhost:8000/api/v1/pdf/metadata \
  -F "file=@document.pdf"
```

**Response:**
```json
{
    "title": "Document Title",
    "author": "Author Name",
    "subject": "Document Subject",
    "creator": "Microsoft Word",
    "producer": "PDF Library",
    "creation_date": "D:20251103120000",
    "modification_date": "D:20251103120000",
    "page_count": 5,
    "is_encrypted": false,
    "is_pdf": true,
    "permissions": -1,
    "success": true
}
```

### Get PDF Info
```bash
POST /api/v1/pdf/info

curl -X POST http://localhost:8000/api/v1/pdf/info \
  -F "file=@document.pdf"
```

### Convert PDF to Images
```bash
POST /api/v1/pdf/to-images?dpi=150&format=png

curl -X POST "http://localhost:8000/api/v1/pdf/to-images?dpi=150&format=png" \
  -F "file=@document.pdf" \
  -O
```

Returns the first page as an image (PNG or JPG).

### Extract Images from PDF
```bash
POST /api/v1/pdf/extract-images

curl -X POST http://localhost:8000/api/v1/pdf/extract-images \
  -F "file=@document.pdf"
```

Returns information about all embedded images.

### Split PDF
```bash
POST /api/v1/pdf/split?start_page=1&end_page=3

curl -X POST "http://localhost:8000/api/v1/pdf/split?start_page=1&end_page=3" \
  -F "file=@document.pdf" \
  -O
```

Returns a new PDF with only pages 1-3.

### Merge PDFs
```bash
POST /api/v1/pdf/merge

curl -X POST http://localhost:8000/api/v1/pdf/merge \
  -F "files=@file1.pdf" \
  -F "files=@file2.pdf" \
  -F "files=@file3.pdf" \
  -O
```

Returns a single merged PDF.

### Compress PDF
```bash
POST /api/v1/pdf/compress?quality=75

curl -X POST "http://localhost:8000/api/v1/pdf/compress?quality=75" \
  -F "file=@large.pdf" \
  -O
```

Returns a compressed PDF (quality: 1-100).

### Add Watermark
```bash
POST /api/v1/pdf/watermark?text=CONFIDENTIAL&opacity=0.3

curl -X POST "http://localhost:8000/api/v1/pdf/watermark?text=CONFIDENTIAL&opacity=0.3" \
  -F "file=@document.pdf" \
  -O
```

Returns a watermarked PDF.

### PDF Health Check
```bash
GET /api/v1/pdf/health

curl http://localhost:8000/api/v1/pdf/health
```

## Using PyMuPDF Directly

### Extract Text
```python
from app.utils.pdf import extract_text_from_pdf

with open("document.pdf", "rb") as f:
    pdf_data = f.read()

result = extract_text_from_pdf(pdf_data)

print(result["text"])
print(f"Pages: {result['total_pages']}")
print(f"Words: {result['total_words']}")
```

### Get Metadata
```python
from app.utils.pdf import get_pdf_metadata

metadata = get_pdf_metadata(pdf_data)

print(f"Title: {metadata['title']}")
print(f"Author: {metadata['author']}")
print(f"Pages: {metadata['page_count']}")
```

### Convert to Images
```python
from app.utils.pdf import pdf_to_images

result = pdf_to_images(pdf_data, dpi=200, fmt="png")

for img_info in result["images"]:
    # Save image
    with open(f"page_{img_info['page']}.png", "wb") as f:
        f.write(img_info["image"])
```

### Split PDF
```python
from app.utils.pdf import split_pdf

# Extract pages 5-10
result = split_pdf(pdf_data, start_page=5, end_page=10)

if result["success"]:
    with open("pages_5_10.pdf", "wb") as f:
        f.write(result["pdf"])
```

### Merge PDFs
```python
from app.utils.pdf import merge_pdfs

# Load multiple PDFs
pdf_files = []
for filename in ["file1.pdf", "file2.pdf", "file3.pdf"]:
    with open(filename, "rb") as f:
        pdf_files.append(f.read())

# Merge
result = merge_pdfs(pdf_files)

if result["success"]:
    with open("merged.pdf", "wb") as f:
        f.write(result["pdf"])
```

### Compress PDF
```python
from app.utils.pdf import compress_pdf

result = compress_pdf(pdf_data, image_quality=60)

print(f"Original: {result['original_size']} bytes")
print(f"Compressed: {result['compressed_size']} bytes")
print(f"Saved: {result['compression_ratio']}%")

with open("compressed.pdf", "wb") as f:
    f.write(result["pdf"])
```

## Advanced Features

### Working with Pages
```python
import fitz

doc = fitz.open("document.pdf")

# Iterate through pages
for page_num in range(len(doc)):
    page = doc[page_num]
    
    # Get page dimensions
    width = page.rect.width
    height = page.rect.height
    
    # Extract text
    text = page.get_text()
    
    # Extract text with layout
    text_dict = page.get_text("dict")
    
    # Get images on page
    images = page.get_images()

doc.close()
```

### Adding Content
```python
import fitz

doc = fitz.open("document.pdf")
page = doc[0]

# Add text
page.insert_text(
    (100, 100),  # position
    "Added text",
    fontsize=12,
    color=(0, 0, 1)  # blue
)

# Add image
page.insert_image(
    fitz.Rect(100, 200, 300, 400),  # position
    filename="image.jpg"
)

# Save
doc.save("modified.pdf")
doc.close()
```

### Creating PDFs
```python
import fitz

# Create new PDF
doc = fitz.open()

# Add page
page = doc.new_page(width=595, height=842)  # A4 size

# Add content
page.insert_text((50, 50), "Hello World!", fontsize=20)

# Save
doc.save("new.pdf")
doc.close()
```

### Extracting Tables
```python
import fitz

doc = fitz.open("document.pdf")
page = doc[0]

# Get text with coordinates
text_dict = page.get_text("dict")

# Process text blocks
for block in text_dict["blocks"]:
    if "lines" in block:
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"]
                bbox = span["bbox"]  # (x0, y0, x1, y1)
                print(f"Text: {text} at {bbox}")

doc.close()
```

## Integration Examples

### PDF Processing with Celery
```python
from app.core.celery_config import celery_app
from app.utils.pdf import extract_text_from_pdf
from app.db.minio_client import download_file, upload_file
import json

@celery_app.task
def process_pdf_async(filename: str):
    # Download PDF from MinIO
    pdf_data = download_file(f"uploads/{filename}")
    
    # Extract text
    result = extract_text_from_pdf(pdf_data)
    
    # Store result
    text_json = json.dumps(result).encode()
    upload_file(text_json, f"processed/{filename}.json", "application/json")
    
    return result
```

### PDF + OCR for Scanned Documents
```python
from app.utils.pdf import pdf_to_images
from app.utils.ocr import extract_text_from_image

def extract_text_from_scanned_pdf(pdf_data: bytes) -> dict:
    # Convert PDF to images
    images_result = pdf_to_images(pdf_data, dpi=300)
    
    pages_text = []
    
    # OCR each page
    for img_info in images_result["images"]:
        ocr_result = extract_text_from_image(img_info["image"])
        pages_text.append({
            "page": img_info["page"],
            "text": ocr_result["text"],
            "confidence": ocr_result["confidence"]
        })
    
    return {
        "pages": pages_text,
        "total_pages": len(pages_text)
    }
```

### Store PDFs in MinIO
```python
from app.db.minio_client import upload_file, download_file
from app.utils.pdf import get_pdf_metadata

# Upload PDF
with open("document.pdf", "rb") as f:
    pdf_data = f.read()

upload_file(pdf_data, "documents/doc001.pdf", "application/pdf")

# Download and process
pdf_data = download_file("documents/doc001.pdf")
metadata = get_pdf_metadata(pdf_data)
```

## Performance Considerations

### Memory Management
```python
import fitz

# For large PDFs, process page by page
doc = fitz.open("large.pdf")

for page_num in range(len(doc)):
    page = doc[page_num]
    
    # Process page
    text = page.get_text()
    
    # Clear page from memory
    page = None

doc.close()
```

### Optimization Tips
1. **Lower DPI** - Use 150 DPI instead of 300 for images
2. **Compress Images** - Set lower quality for compression
3. **Process in Batches** - Use Celery for large files
4. **Cache Results** - Store extracted text in database
5. **Stream Processing** - Process pages one at a time

## Use Cases

1. **Document Management** - Extract and index PDF content
2. **Data Extraction** - Extract structured data from PDFs
3. **Report Generation** - Create PDFs programmatically
4. **Document Conversion** - Convert PDFs to images/text
5. **PDF Optimization** - Compress and optimize PDFs
6. **Content Protection** - Add watermarks
7. **Document Assembly** - Merge/split PDFs

## Comparison with Other Libraries

| Feature | PyMuPDF | PyPDF2 | PDFPlumber |
|---------|---------|--------|------------|
| **Speed** | ⚡ Very Fast | Slow | Medium |
| **Text Extraction** | ✅ Excellent | ✅ Good | ✅ Excellent |
| **Image Handling** | ✅ Excellent | ❌ Limited | ❌ Limited |
| **PDF Creation** | ✅ Yes | ❌ No | ❌ No |
| **Compression** | ✅ Yes | ❌ Limited | ❌ No |
| **License** | AGPL/Commercial | MIT | MIT |

## Troubleshooting

### Import Error
```python
# Correct import
import fitz  # Not 'import PyMuPDF'

# Check version
print(fitz.VersionBind)
```

### Memory Issues
```python
# Close documents explicitly
doc = fitz.open("file.pdf")
# ... process ...
doc.close()  # Important!
```

### Encrypted PDFs
```python
doc = fitz.open("encrypted.pdf")

if doc.is_encrypted:
    # Try to decrypt
    if doc.authenticate("password"):
        # Process document
        text = doc[0].get_text()
    else:
        print("Wrong password")

doc.close()
```

## Command Line Usage

PyMuPDF includes a command-line tool:

```bash
# Extract text
python -m fitz extract document.pdf

# Get info
python -m fitz info document.pdf

# Convert to images
python -m fitz getpix document.pdf

# More commands
python -m fitz --help
```

## Resources

- PyMuPDF Documentation: https://pymupdf.readthedocs.io/
- GitHub: https://github.com/pymupdf/PyMuPDF
- MuPDF: https://mupdf.com/
- Examples: https://github.com/pymupdf/PyMuPDF-Utilities

## Best Practices

1. **Always close documents** - Prevent memory leaks
2. **Handle exceptions** - PDFs can be corrupted
3. **Validate input** - Check file is actually a PDF
4. **Set limits** - Limit page count for processing
5. **Use async processing** - Process large files with Celery
6. **Cache results** - Don't reprocess same files
7. **Monitor memory** - Large PDFs use significant memory

## Security Considerations

1. **Validate PDFs** - Check file type before processing
2. **Size Limits** - Set max file size
3. **Timeout Limits** - Set processing timeouts
4. **Sanitize Output** - Clean extracted text
5. **Encrypted PDFs** - Handle password-protected files safely

