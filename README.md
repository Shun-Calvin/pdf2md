# PDF2MD Converter

A comprehensive PDF to Markdown conversion framework with OCR capabilities, image processing, and a modern web interface.

## Features

- **PDF to Markdown Conversion**: Convert PDF documents to clean, structured Markdown format
- **Multiple OCR Engines**: Support for PaddleOCR, Tesseract, and cloud-based OCR services
- **Image Processing**: Extract and describe images within PDFs using AI vision models
- **Table Extraction**: Convert PDF tables to Markdown table format
- **Image Deduplication**: Automatically detect and remove duplicate images
- **Web Interface**: Modern React-based frontend for easy file upload and management
- **Real-time Processing**: WebSocket support for live progress updates
- **Batch Processing**: Handle multiple files concurrently
- **RESTful API**: Full-featured API with automatic documentation

## Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM
- **Celery**: Distributed task queue for background processing
- **Redis**: Message broker and caching
- **OCR Engines**:
  - PaddleOCR (Mobile & Server versions)
  - Tesseract OCR
  - Cloud OCR (AWS Textract)

### Frontend
- **React 18**: Modern UI library
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Zustand**: State management
- **Axios**: HTTP client
- **React Dropzone**: File upload handling

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/Shun-Calvin/pdf2md
cd pdf2md

# Start all services
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Documentation: http://localhost:8000/docs
```

### Manual Setup

#### Prerequisites

- Python 3.10+
- Node.js 18+
- Redis (optional, for task queue)
- Tesseract OCR (optional, for Tesseract engine)

#### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from app.models import init_db; init_db()"

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

#### Start Both Servers

```bash
# From project root
python start.py
```

## Configuration

Create a `.env` file in the `backend` directory:

```env
# App settings
DEBUG=false
APP_NAME=PDF2MD Converter

# Server settings
HOST=0.0.0.0
PORT=8000

# Storage
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
TEMP_DIR=temp

# Database
DATABASE_URL=sqlite:///./pdf2md.db

# Redis (for task queue)
REDIS_URL=redis://localhost:6379/0

# OCR Settings
DEFAULT_OCR_ENGINE=paddleocr_mobile
TESSERACT_CMD=/usr/bin/tesseract
PADDLEOCR_USE_GPU=false

# Cloud OCR (optional)
CLOUD_OCR_PROVIDER=aws
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Image Description (optional)
ENABLE_IMAGE_DESCRIPTION=true
IMAGE_DESCRIPTION_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4-vision-preview
```

## API Endpoints

### File Upload
- `POST /api/upload` - Upload PDF file(s)
- `POST /api/upload/batch` - Upload multiple files

### File Management
- `GET /api/files` - List all processed files
- `GET /api/files/{file_id}` - Get file details
- `DELETE /api/files/{file_id}` - Delete a file
- `GET /api/files/{file_id}/download` - Download original PDF
- `GET /api/files/{file_id}/markdown` - Download Markdown output

### Processing
- `POST /api/files/{file_id}/reprocess` - Reprocess with new options
- `GET /api/files/{file_id}/progress` - Get processing progress
- `GET /api/files/{file_id}/pages/{page_id}` - Get page details
- `GET /api/files/{file_id}/images` - List extracted images
- `GET /api/files/{file_id}/tables` - List extracted tables

### Health & Stats
- `GET /api/health` - Health check
- `GET /api/stats` - System statistics
- `GET /api/stats/storage` - Storage usage
- `GET /api/ocr/engines` - List available OCR engines

### WebSocket
- `ws://localhost:8000/ws/{file_id}` - Real-time progress updates

## Usage Guide

### Basic Conversion

1. Open the web interface at `http://localhost:3000`
2. Drag and drop PDF files or click to browse
3. Select OCR engine and processing options
4. Click "Convert" and wait for processing
5. Download the Markdown output

### Processing Options

- **OCR Engine**: Choose between PaddleOCR (fast), PaddleOCR Server (accurate), Tesseract, or Cloud OCR
- **Extract Images**: Enable to extract images from PDF
- **Describe Images**: Use AI to generate image descriptions (requires OpenAI API key)
- **Extract Tables**: Convert PDF tables to Markdown format
- **Image Deduplication**: Remove duplicate images automatically
- **Replace Text with Descriptions**: Replace page text with image/table descriptions

### Batch Processing

Upload multiple files at once:
```bash
curl -X POST -F "files=@doc1.pdf" -F "files=@doc2.pdf" \
  http://localhost:8000/api/upload/batch
```

### Using WebSocket for Progress

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}%`);
  console.log(`Status: ${data.status}`);
};
```

## OCR Engines

### PaddleOCR (Default)
- **Mobile**: Fast, lightweight, good for most documents
- **Server**: Higher accuracy, slower processing

### Tesseract OCR
- Open-source OCR engine
- Requires Tesseract installation
- Good for printed text

### Cloud OCR
- AWS Textract support
- Best for complex documents
- Requires AWS credentials

## Development

### Running Tests

```bash
cd backend
pytest

# With coverage
pytest --cov=app tests/
```

### Code Formatting

```bash
# Backend
cd backend
black app/ ocr_engines/ utils/
isort app/ ocr_engines/ utils/

# Frontend
cd frontend
npm run lint
```

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Docker Deployment

### Production Build

```bash
# Build and start all services
docker-compose -f docker-compose.yml up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Environment Variables

All configuration from `.env` can be passed to Docker containers:

```bash
# Create .env file and start
cp .env.example .env
# Edit .env with your settings
docker-compose up -d
```

## Troubleshooting

### OCR Engine Issues

**PaddleOCR not working:**
- Check if paddlepaddle is installed correctly
- For GPU support, install paddlepaddle-gpu

**Tesseract not found:**
- Install Tesseract: `apt-get install tesseract-ocr` (Linux) or `brew install tesseract` (Mac)
- Set `TESSERACT_CMD` in environment variables

### Memory Issues

For large PDFs, adjust the batch size:
```python
# In config.py or .env
MAX_WORKERS=2
BATCH_SIZE=5
```

### File Upload Issues

Check upload directory permissions:
```bash
chmod 755 uploads outputs temp
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for guidelines.

## Support

For issues and feature requests, please use the GitHub issue tracker.
