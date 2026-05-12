# Docling & Open Data Loader Integration Guide

This guide explains how to integrate **Docling** and **Open Data Loader** into the PDF2MD converter for enhanced document parsing capabilities.

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [API Endpoints](#api-endpoints)
6. [Examples](#examples)
7. [Troubleshooting](#troubleshooting)

## Overview

### Docling

**Docling** is an advanced document understanding library that provides:

- **Layout Analysis**: Understands document structure (headers, paragraphs, lists)
- **Table Detection**: Extracts tables with structure preservation
- **Figure Extraction**: Identifies and extracts images and figures
- **OCR Integration**: Supports multiple OCR engines (Tesseract, EasyOCR)
- **Structured Output**: Returns semantically meaningful document elements

### Open Data Loader

**Open Data Loader** is a data loading framework that provides:

- **Batch Processing**: Efficient parallel processing of multiple documents
- **Streaming**: Real-time document processing with job queues
- **Progress Tracking**: Built-in progress callbacks and monitoring
- **Caching**: Optional result caching for improved performance
- **Memory Efficiency**: Handles large document sets with limited memory

## Installation

### Install Dependencies

Add the following to `backend/requirements.txt`:

```bash
# Docling
docling>=2.0.0

# Open Data Loader
open-dataset-loader>=0.1.0
```

Then install:

```bash
cd backend
pip install -r requirements.txt
```

### Verify Installation

```bash
python -c "import docling; print('Docling installed:', docling.__version__)"
python -c "import open_data_loader; print('Open Data Loader installed')"
```

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# ============================================
# Docling Settings
# ============================================
USE_DOCLING=true
DOCLING_OCR_ENGINE=tesseract
DOCLING_ENABLE_TABLE_DETECTION=true
DOCLING_ENABLE_FIGURE_DETECTION=true
DOCLING_ENABLE_LAYOUT_ANALYSIS=true

# ============================================
# Open Data Loader Settings
# ============================================
USE_OPEN_DATA_LOADER=true
ODL_BATCH_SIZE=4
ODL_NUM_WORKERS=2
ODL_ENABLE_STREAMING=false

# ============================================
# OCR Engine (now includes 'docling' option)
# ============================================
DEFAULT_OCR_ENGINE=docling
```

### Configuration Options

#### Docling Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_DOCLING` | `false` | Enable Docling parser |
| `DOCLING_OCR_ENGINE` | `tesseract` | OCR engine: `tesseract` or `easyocr` |
| `DOCLING_ENABLE_TABLE_DETECTION` | `true` | Extract tables with structure |
| `DOCLING_ENABLE_FIGURE_DETECTION` | `true` | Extract images and figures |
| `DOCLING_ENABLE_LAYOUT_ANALYSIS` | `true` | Analyze document layout |

#### Open Data Loader Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_OPEN_DATA_LOADER` | `false` | Enable batch processing |
| `ODL_BATCH_SIZE` | `4` | Documents per batch |
| `ODL_NUM_WORKERS` | `2` | Parallel workers |
| `ODL_ENABLE_STREAMING` | `false` | Enable streaming mode |

## Usage

### 1. Basic Document Parsing with Docling

```python
from parsers.docling_parser import DoclingParser

# Create parser
parser = DoclingParser(
    enable_ocr=True,
    enable_table_detection=True,
    enable_figure_detection=True
)

# Parse document
elements = parser.parse_document(
    "path/to/document.pdf",
    extract_images=True,
    extract_tables=True
)

# Convert to markdown
markdown = parser.convert_to_markdown(elements)
print(markdown)
```

### 2. Batch Processing with Open Data Loader

```python
from parsers.open_data_loader import BatchDocumentProcessor

# Create batch processor
processor = BatchDocumentProcessor(
    batch_size=4,
    num_workers=2,
    use_docling=True,
    extract_images=True,
    extract_tables=True
)

# Define progress callback
def on_progress(current, total, file_path, status):
    print(f"Progress: {current}/{total} - {status}")

# Process files
file_paths = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
for result in processor.process_files(file_paths, on_progress):
    if result.success:
        print(f"✓ {result.file_path}")
        print(f"  Elements: {len(result.elements)}")
        print(f"  Time: {result.processing_time:.2f}s")
```

### 3. Unified Parser Interface

```python
from parsers import create_parser, ParserType

# Create different parsers
standard_parser = create_parser(ParserType.STANDARD)
docling_parser = create_parser(ParserType.DOCLING)
batch_parser = create_parser(ParserType.ODL_BATCH)

# Use any parser consistently
result = docling_parser.parse_single("document.pdf")
print(f"Success: {result['success']}")
print(f"Markdown: {result['markdown'][:500]}")
```

### 4. Using Docling as OCR Engine

```python
from ocr_engines import OCREngineFactory

# Create Docling OCR engine
ocr_engine = OCREngineFactory.get_engine(
    'docling',
    config={'ocr_engine': 'tesseract'}
)

# Use with existing PDF processor
from utils.pdf_processor import PDFProcessor

processor = PDFProcessor()
pages = processor.process_pdf(
    "document.pdf",
    use_ocr=True,
    ocr_engine=ocr_engine
)
```

### 5. Streaming Document Processing

```python
from parsers.open_data_loader import (
    BatchDocumentProcessor,
    StreamingDocumentProcessor,
    ProcessingJob
)

# Create processor
processor = BatchDocumentProcessor(use_docling=True)
streaming = StreamingDocumentProcessor(processor, max_queue_size=10)

# Start streaming
streaming.start()

# Submit jobs
for i, file_path in enumerate(["doc1.pdf", "doc2.pdf"]):
    job = ProcessingJob(
        file_path=file_path,
        file_id=f"file_{i}",
        callback=lambda r: print(f"Done: {r.file_path}")
    )
    streaming.submit(job)

# Collect results
while True:
    result = streaming.get_result(timeout=5.0)
    if result is None:
        break
    print(f"Result: {result.file_path}")

# Stop streaming
streaming.stop()
```

## API Endpoints

The following REST API endpoints are available:

### List Available Parsers

```http
GET /api/parsers/available
```

Response:
```json
{
  "standard": {
    "name": "Standard",
    "available": true,
    "description": "PyMuPDF + pdfplumber with OCR support",
    "features": ["text_extraction", "table_extraction", "image_extraction", "ocr"]
  },
  "docling": {
    "name": "Docling",
    "available": true,
    "description": "Advanced document understanding with layout analysis",
    "features": ["layout_analysis", "table_structure", "figure_extraction", "ocr"]
  },
  "odl_batch": {
    "name": "Open Data Loader",
    "available": true,
    "description": "Batch processing with parallel execution",
    "features": ["batch_processing", "parallel_execution", "streaming"]
  }
}
```

### Parse Single Document

```http
POST /api/parsers/parse/{file_id}?parser_type=docling&extract_images=true&extract_tables=true
```

Response:
```json
{
  "success": true,
  "file_id": 123,
  "parser_type": "docling",
  "elements_count": 45,
  "markdown_length": 15420,
  "processing_time": 3.45,
  "metadata": {
    "element_count": 45
  }
}
```

### Parse Batch

```http
POST /api/parsers/parse-batch?parser_type=odl_batch&extract_images=true
Content-Type: application/json

{
  "file_ids": [1, 2, 3]
}
```

Response:
```json
{
  "success": true,
  "parser_type": "odl_batch",
  "total_files": 3,
  "processed_files": 3,
  "results": [
    {
      "file_id": "1",
      "success": true,
      "elements_count": 45,
      "processing_time": 2.1
    }
  ]
}
```

### Get Parser Settings

```http
GET /api/parsers/settings
```

Response:
```json
{
  "docling": {
    "enabled": true,
    "ocr_engine": "tesseract",
    "enable_table_detection": true,
    "enable_figure_detection": true,
    "enable_layout_analysis": true
  },
  "open_data_loader": {
    "enabled": true,
    "batch_size": 4,
    "num_workers": 2,
    "enable_streaming": false
  }
}
```

### Reprocess File

```http
POST /api/parsers/reprocess/{file_id}?parser_type=docling&extract_images=true
```

### Compare Parsers

```http
GET /api/parsers/compare/{file_id}?parsers=standard&parsers=docling
```

Response:
```json
{
  "file_id": 123,
  "filename": "document.pdf",
  "comparisons": [
    {
      "parser_type": "standard",
      "success": true,
      "elements_count": 32,
      "markdown_length": 12400,
      "processing_time": 1.2
    },
    {
      "parser_type": "docling",
      "success": true,
      "elements_count": 45,
      "markdown_length": 15420,
      "processing_time": 3.4
    }
  ]
}
```

## Examples

See `backend/examples/docling_odl_examples.py` for complete working examples:

```bash
cd backend
python examples/docling_odl_examples.py
```

Available examples:

1. **Basic Docling Parsing** - Parse a document with layout analysis
2. **Batch Processing** - Process multiple documents with progress tracking
3. **Unified Parser Interface** - Compare different parsers
4. **Streaming Processing** - Real-time document processing
5. **Available Parsers** - Check installed parsers
6. **Configuration** - Environment setup examples

## Troubleshooting

### Docling Not Available

**Problem**: `ImportError: No module named 'docling'`

**Solution**:
```bash
pip install docling>=2.0.0
```

### Open Data Loader Not Available

**Problem**: `ImportError: No module named 'open_data_loader'`

**Solution**:
```bash
pip install open-dataset-loader>=0.1.0
```

### Tesseract Not Found (Docling OCR)

**Problem**: Docling fails with Tesseract not found error

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

Then set the path in `.env`:
```env
TESSERACT_CMD=/usr/bin/tesseract
```

### Memory Issues with Large Documents

**Problem**: Out of memory errors with large PDFs

**Solution**:
1. Reduce batch size:
```env
ODL_BATCH_SIZE=2
```

2. Reduce workers:
```env
ODL_NUM_WORKERS=1
```

3. Enable streaming:
```env
ODL_ENABLE_STREAMING=true
```

4. Process documents one at a time using the unified parser interface

### Slow Processing

**Problem**: Document processing is slow

**Solutions**:
1. Use GPU for PaddleOCR:
```env
PADDLEOCR_USE_GPU=true
```

2. Increase batch size (if memory allows):
```env
ODL_BATCH_SIZE=8
```

3. Increase workers:
```env
ODL_NUM_WORKERS=4
```

4. Disable unnecessary features:
```env
DOCLING_ENABLE_LAYOUT_ANALYSIS=false
DOCLING_ENABLE_FIGURE_DETECTION=false
```

### Table Detection Not Working

**Problem**: Tables not being detected

**Solution**:
1. Ensure table detection is enabled:
```env
DOCLING_ENABLE_TABLE_DETECTION=true
```

2. Use Docling parser instead of standard:
```python
parser = create_parser(ParserType.DOCLING, extract_tables=True)
```

### Image Deduplication Issues

**Problem**: Duplicate images not being detected

**Solution**:
1. Enable deduplication:
```env
ENABLE_IMAGE_DEDUPLICATION=true
```

2. Adjust threshold (lower = more strict):
```env
IMAGE_DEDUP_THRESHOLD=0.85
```

## Performance Comparison

| Parser | Speed | Accuracy | Features | Memory |
|--------|-------|----------|----------|---------|
| Standard | Fast | Good | Basic | Low |
| Docling | Medium | Excellent | Advanced | Medium |
| ODL Batch | Fast (parallel) | Good/Excellent* | All | Medium/High |

*Depends on underlying parser used with ODL

## Best Practices

1. **Choose the Right Parser**:
   - Use **Standard** for simple PDFs with text only
   - Use **Docling** for complex documents with tables, figures, and layout
   - Use **ODL Batch** for processing large numbers of documents

2. **Enable Features Selectively**:
   - Disable OCR if PDFs have embedded text
   - Disable image extraction if not needed
   - Disable layout analysis for speed-critical applications

3. **Monitor Resources**:
   - Start with lower batch sizes and increase gradually
   - Monitor memory usage with large documents
   - Use streaming for very large document sets

4. **Error Handling**:
   - Always check `result['success']` before using output
   - Implement fallback parsers for critical applications
   - Log errors for debugging

5. **Caching**:
   - Enable caching for repeated processing of same documents
   - Clear cache periodically to prevent disk space issues

## Migration Guide

### From Standard to Docling

```python
# Before (Standard)
from utils.pdf_processor import PDFProcessor
processor = PDFProcessor()
pages = processor.process_pdf("doc.pdf", use_ocr=True)

# After (Docling)
from parsers import create_parser, ParserType
parser = create_parser(ParserType.DOCLING, use_ocr=True)
result = parser.parse_single("doc.pdf")
elements = result['elements']
markdown = result['markdown']
```

### Adding Batch Processing

```python
# Single file processing
result = parser.parse_single("doc.pdf")

# Batch processing
results = parser.parse_batch(["doc1.pdf", "doc2.pdf", "doc3.pdf"])
```

## Support

For issues and questions:

1. Check the examples: `backend/examples/docling_odl_examples.py`
2. Review API documentation: `/docs` (FastAPI auto-generated)
3. Enable debug logging:
```env
DEBUG=true
```

## License

The Docling and Open Data Loader integration follows the same MIT license as the PDF2MD Converter project.
