from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
import logging
import asyncio
from datetime import datetime
import json

from app.models import (
    get_db, init_db, PDFFile, PDFPage, ExtractedImage, 
    ExtractedTable, OutputFile, ProcessingOptions, OCRStatus
)
from app.config import settings
from ocr_engines import OCREngineFactory
from utils.pdf_processor import PDFProcessor
from utils.image_description import ImageDescriptionService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Comprehensive PDF to Markdown conversion framework",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "message": "Validation error - check your input data"
        }
    )

# Static files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

# Initialize database
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")

# WebSocket connections
websocket_connections = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    websocket_connections[client_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong or other messages
            if data == "ping":
                await websocket.send_text("pong")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Safely remove the connection
        if client_id in websocket_connections:
            del websocket_connections[client_id]

async def send_progress(client_id: str, message: dict):
    """Send progress update via WebSocket"""
    if client_id in websocket_connections:
        await websocket_connections[client_id].send_json(message)

@app.post("/api/upload")
async def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    use_ocr: bool = Form(default=True),
    ocr_engine: str = Form(default="paddleocr_mobile"),
    cloud_ocr_provider: Optional[str] = Form(default=None),
    aws_access_key_id: Optional[str] = Form(default=None),
    aws_secret_access_key: Optional[str] = Form(default=None),
    aws_region: Optional[str] = Form(default="us-east-1"),
    extract_images: bool = Form(default=True),
    extract_tables: bool = Form(default=True),
    extract_drawings: bool = Form(default=True),
    deduplicate_images: bool = Form(default=False),
    describe_images: bool = Form(default=False),
    describe_tables: bool = Form(default=False),
    replace_text_with_description: bool = Form(default=False),
    image_description_provider: str = Form(default="openai_compatible"),
    image_description_concurrent: int = Form(default=5),
    image_description_prompt: Optional[str] = Form(default=None),
    openai_compatible_api_key: Optional[str] = Form(default=None),
    openai_compatible_base_url: Optional[str] = Form(default=None),
    openai_compatible_model: Optional[str] = Form(default=None),
    enable_vector_embedding: bool = Form(default=False),
    vector_embedding_model: Optional[str] = Form(default="clip"),
    client_id: Optional[str] = Form(default=None),
    db: Session = Depends(get_db)
):
    """
    Upload and process PDF files in batch
    """
    uploaded_files = []
    
    for file in files:
        if not file.filename.endswith('.pdf'):
            continue
            
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        original_filename = file.filename
        filename = f"{unique_id}_{original_filename}"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create database entry
        pdf_file = PDFFile(
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            status=OCRStatus.PENDING,
            use_ocr=use_ocr,
            ocr_engine=ocr_engine
        )
        db.add(pdf_file)
        db.commit()
        db.refresh(pdf_file)
        
        uploaded_files.append({
            "id": pdf_file.id,
            "filename": original_filename,
            "status": "pending"
        })
        
        # Process in background
        background_tasks.add_task(
            process_pdf_task,
            pdf_file.id,
            {
                "use_ocr": use_ocr,
                "ocr_engine": ocr_engine,
                "cloud_ocr_provider": cloud_ocr_provider if cloud_ocr_provider else None,
                "aws_access_key_id": aws_access_key_id if aws_access_key_id else None,
                "aws_secret_access_key": aws_secret_access_key if aws_secret_access_key else None,
                "aws_region": aws_region,
                "extract_images": extract_images,
                "extract_tables": extract_tables,
                "extract_drawings": extract_drawings,
                "deduplicate_images": deduplicate_images,
                "describe_images": describe_images,
                "describe_tables": describe_tables,
                "replace_text_with_description": replace_text_with_description,
                "image_description_provider": image_description_provider,
                "image_description_concurrent": image_description_concurrent,
                "openai_compatible_api_key": openai_compatible_api_key if openai_compatible_api_key else None,
                "openai_compatible_base_url": openai_compatible_base_url if openai_compatible_base_url else None,
                "openai_compatible_model": openai_compatible_model if openai_compatible_model else None,
                "enable_vector_embedding": enable_vector_embedding,
                "vector_embedding_model": vector_embedding_model,
            },
            client_id
        )
    
    return {
        "message": f"Uploaded {len(uploaded_files)} files",
        "files": uploaded_files
    }

def extract_images_from_page(page, page_number: int, processor) -> list:
    """Extract images from a PDF page using PyMuPDF"""
    from PIL import Image
    import io
    import hashlib
    from utils.pdf_processor import ExtractedImage
    
    images = []
    image_list = page.get_images(full=True)
    
    logger.info(f"Found {len(image_list)} raw images on page {page_number}")
    
    for img_index, img in enumerate(image_list, start=1):
        try:
            xref = img[0]
            base_image = page.parent.extract_image(xref)
            
            if not base_image:
                logger.warning(f"Could not extract image {img_index} from page {page_number}")
                continue
                
            image_bytes = base_image["image"]
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Calculate hash for deduplication
            img_hash = hashlib.md5(image.tobytes()).hexdigest()
            
            # Create proper ExtractedImage object
            extracted_img = ExtractedImage(
                image=image,
                page_number=page_number,
                bbox=(0, 0, image.width, image.height),
                image_type='image',
                hash=img_hash,
                is_duplicate=False
            )
            
            images.append(extracted_img)
            logger.info(f"Successfully extracted image {img_index} from page {page_number} (size: {image.size})")
            
        except Exception as e:
            logger.warning(f"Failed to extract image {img_index} from page {page_number}: {e}")
    
    # Apply deduplication if enabled
    if processor.enable_image_dedup and images:
        images = processor._deduplicate_images(images)
        logger.info(f"After deduplication: {len(images)} unique images on page {page_number}")
    
    return images

def extract_drawings_from_page(page, page_number: int, processor) -> list:
    """Extract vector drawings from a PDF page using PyMuPDF"""
    from PIL import Image
    import io
    import hashlib
    import fitz
    from utils.pdf_processor import ExtractedImage
    
    drawings = []
    
    try:
        # Get drawings (vector graphics)
        drawings_list = page.get_drawings()
        
        if drawings_list:
            logger.info(f"Found {len(drawings_list)} raw vector elements on page {page_number}")
            
            # Filter out text and small decorative elements
            # Only keep actual vector graphics (lines, curves, shapes)
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height
            
            valid_drawings = []
            for i, drawing in enumerate(drawings_list):
                # Skip if it's just text (check for common text indicators)
                # Text in PDFs is often rendered as small line segments
                items = drawing.get('items', [])
                
                # Count actual vector paths vs text segments
                vector_paths = 0
                text_segments = 0
                total_length = 0
                
                for item in items:
                    if item[0] == 'l':  # line
                        # Check if it's a long line (likely a vector) vs short line (likely text)
                        p1, p2 = item[1], item[2]
                        length = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5
                        total_length += length
                        
                        # Lines longer than 20 points are likely vector graphics
                        if length > 20:
                            vector_paths += 1
                        else:
                            text_segments += 1
                    elif item[0] in ('c', 'q'):  # curves
                        vector_paths += 1
                    elif item[0] == 're':  # rectangles
                        vector_paths += 1
                
                # A drawing should have at least some substantial vector paths
                # and not be dominated by tiny text segments
                if vector_paths >= 3 and vector_paths > text_segments * 0.5:
                    # Get bounding box
                    if 'rect' in drawing:
                        rect = drawing['rect']
                        drawing_area = rect.width * rect.height
                        
                        # Skip if it's the entire page or nearly the entire page
                        # (likely a background or text block)
                        area_ratio = drawing_area / page_area
                        if 0.05 <= area_ratio <= 0.95:  # Between 5% and 95% of page
                            valid_drawings.append((i, drawing, rect))
                            logger.info(f"Drawing {i} on page {page_number}: {vector_paths} vectors, {text_segments} text segments, area={area_ratio*100:.1f}%")
                        else:
                            logger.debug(f"Skipping drawing {i} on page {page_number}: area ratio {area_ratio*100:.1f}% (too small or too large)")
                    elif total_length > 100:  # If no rect but substantial path length
                        # Use the drawing's natural bounds
                        try:
                            rect = drawing.get('rect', page_rect)
                            if rect and rect.width > 0 and rect.height > 0:
                                area_ratio = (rect.width * rect.height) / page_area
                                if 0.05 <= area_ratio <= 0.95:
                                    valid_drawings.append((i, drawing, rect))
                                    logger.info(f"Drawing {i} on page {page_number}: path-based, length={total_length:.0f}, area={area_ratio*100:.1f}%")
                        except:
                            pass
            
            logger.info(f"Filtered to {len(valid_drawings)} valid drawings on page {page_number}")
            
            # Extract each valid drawing individually
            for idx, drawing_info, rect in valid_drawings:
                try:
                    # Add some padding around the drawing
                    padding = 10
                    clip_rect = fitz.Rect(
                        max(0, rect.x0 - padding),
                        max(0, rect.y0 - padding),
                        min(page_rect.width, rect.x1 + padding),
                        min(page_rect.height, rect.y1 + padding)
                    )
                    
                    # Render only this region
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=clip_rect)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Calculate hash
                    img_hash = hashlib.md5(img.tobytes()).hexdigest()
                    
                    # Create drawing object
                    drawing_obj = ExtractedImage(
                        image=img,
                        page_number=page_number,
                        bbox=(clip_rect.x0, clip_rect.y0, clip_rect.x1, clip_rect.y1),
                        image_type='drawing',
                        hash=img_hash,
                        is_duplicate=False
                    )
                    
                    drawings.append(drawing_obj)
                    logger.info(f"Successfully extracted drawing {idx} from page {page_number} (size: {img.size})")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract drawing {idx} from page {page_number}: {e}")
    
    except Exception as e:
        logger.warning(f"Failed to extract drawings from page {page_number}: {e}")
    
    return drawings

async def process_pdf_task(
    pdf_id: int,
    options: dict,
    client_id: Optional[str] = None
):
    """Background task to process PDF"""
    from app.models import SessionLocal
    import time
    
    db = SessionLocal()
    start_time = time.time()
    
    try:
        # Get PDF record
        pdf_file = db.query(PDFFile).filter(PDFFile.id == pdf_id).first()
        if not pdf_file:
            logger.error(f"PDF {pdf_id} not found")
            return
        
        # Update status
        pdf_file.status = OCRStatus.PROCESSING
        pdf_file.updated_at = datetime.utcnow()
        db.commit()
        
        if client_id:
            await send_progress(client_id, {
                "type": "progress",
                "file_id": pdf_id,
                "filename": pdf_file.original_filename,
                "status": "processing",
                "progress": 0
            })
        
        # Initialize OCR engine if needed
        ocr_engine = None
        if options.get("use_ocr") and options.get("ocr_engine") != "none":
            ocr_config = {}
            if options.get("cloud_ocr_provider"):
                ocr_config["provider"] = options["cloud_ocr_provider"]
            
            ocr_engine = OCREngineFactory.get_engine(
                options["ocr_engine"],
                ocr_config
            )
            ocr_engine.initialize()
        
        # Initialize PDF processor
        processor = PDFProcessor(
            enable_image_dedup=options.get("deduplicate_images", False),
            dedup_threshold=settings.IMAGE_DEDUP_THRESHOLD,
            hash_size=settings.IMAGE_DEDUP_HASH_SIZE
        )
        
        # Get total pages first
        import fitz
        doc = fitz.open(pdf_file.file_path)
        total_pages = len(doc)
        doc.close()
        
        pdf_file.page_count = total_pages
        db.commit()
        
        # Process PDF with real-time progress tracking
        logger.info(f"Processing PDF: {pdf_file.original_filename} ({total_pages} pages)")
        
        pages = []
        doc = fitz.open(pdf_file.file_path)
        
        for page_num in range(total_pages):
            # Update current page
            pdf_file.current_page = page_num + 1
            db.commit()

            # Calculate progress (0-100%)
            progress = int(((page_num + 1) / total_pages) * 100)

            # Send progress update EVERY page for real-time sync
            if client_id:
                await send_progress(client_id, {
                    "type": "progress",
                    "file_id": pdf_id,
                    "filename": pdf_file.original_filename,
                    "status": "processing",
                    "progress": progress,
                    "current_page": page_num + 1,
                    "total_pages": total_pages
                })

            # Log to terminal for debugging
            logger.info(f"Processing page {page_num + 1}/{total_pages}")

            # Yield control to event loop to allow WebSocket messages to be sent
            await asyncio.sleep(0)

            # Actually process the page
            fitz_page = doc[page_num]
            # Convert page to image for OCR if needed
            pix = fitz_page.get_pixmap(matrix=fitz.Matrix(2, 2))
            from PIL import Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Process based on whether OCR is needed
            if options.get("use_ocr") and ocr_engine:
                page_result = ocr_engine.process_pdf_page(img, page_num + 1)
            else:
                # Direct text extraction
                text = fitz_page.get_text()
                page_result = type('obj', (object,), {
                    'page_number': page_num + 1,
                    'text': text,
                    'markdown': text,
                    'images': [],
                    'tables': [],
                    'has_images': False,
                    'has_tables': False,
                    'has_drawings': False
                })()
            
            # Extract images from PDF page if enabled
            if options.get("extract_images"):
                page_images = extract_images_from_page(fitz_page, page_num + 1, processor)
                page_result.images.extend(page_images)
                page_result.has_images = len(page_result.images) > 0
            
            # Extract drawings from PDF page if enabled
            if options.get("extract_drawings"):
                page_drawings = extract_drawings_from_page(fitz_page, page_num + 1, processor)
                if page_drawings:
                    page_result.images.extend(page_drawings)
                    page_result.has_drawings = True
                    page_result.has_images = True
                    logger.info(f"Extracted {len(page_drawings)} drawings from page {page_num + 1}")
            
            pages.append(page_result)

            # Yield control again after page processing
            await asyncio.sleep(0)
        
        doc.close()

        # Yield control after document processing
        await asyncio.sleep(0)

        # Save extracted content to database
        output_dir = os.path.join(settings.OUTPUT_DIR, str(pdf_id))
        os.makedirs(output_dir, exist_ok=True)

        images_dir = os.path.join(output_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        all_images = []
        all_tables = []

        for page in pages:
            # Save page
            db_page = PDFPage(
                pdf_file_id=pdf_id,
                page_number=page.page_number,
                text_content=page.text,
                ocr_text=page.text if options.get("use_ocr") else None,
                markdown_content=page.markdown,
                has_images=page.has_images,
                has_tables=page.has_tables,
                has_drawings=page.has_drawings
            )
            db.add(db_page)

            # Save images (without deduplication - will do globally later)
            for idx, img in enumerate(page.images):
                img_filename = f"page_{page.page_number}_img_{idx + 1}.png"
                img_path = os.path.join(images_dir, img_filename)
                img.image.save(img_path)

                db_image = ExtractedImage(
                    pdf_file_id=pdf_id,
                    page_number=page.page_number,
                    image_path=img_path,
                    image_hash=img.hash,
                    is_duplicate=False,  # Will mark later after global dedup
                    image_type=img.image_type,
                    width=img.image.width,
                    height=img.image.height
                )
                db.add(db_image)
                db.commit()

                all_images.append((db_image, img))

            # Save tables
            for table in page.tables:
                db_table = ExtractedTable(
                    pdf_file_id=pdf_id,
                    page_number=page.page_number,
                    table_data=table.data,
                    markdown_content=table.markdown
                )
                db.add(db_table)
                db.commit()

                if table.image:
                    all_tables.append((db_table, table.image))

            # Yield control periodically during database operations
            await asyncio.sleep(0)

        db.commit()
        
        # Apply global deduplication across all images (including drawings)
        if options.get("deduplicate_images") and all_images:
            logger.info(f"Applying global deduplication to {len(all_images)} images")
            seen_hashes = {}
            duplicates_found = 0
            
            for db_image, img in all_images:
                if img.hash in seen_hashes:
                    # Mark as duplicate
                    db_image.is_duplicate = True
                    db_image.original_image_id = seen_hashes[img.hash]
                    duplicates_found += 1
                    logger.info(f"Marked image on page {db_image.page_number} as duplicate of image on page {db_image.original_image_id}")
                else:
                    seen_hashes[img.hash] = db_image.id
                    db_image.is_duplicate = False
            
            db.commit()
            logger.info(f"Deduplication complete: {duplicates_found} duplicates found, {len(seen_hashes)} unique images")
        
        # Generate image descriptions if enabled
        logger.info(f"Image description check: describe_images={options.get('describe_images')}, describe_tables={options.get('describe_tables')}, all_images_count={len(all_images)}")
        
        if (options.get("describe_images") or options.get("describe_tables")) and all_images:
            logger.info(f"Starting image description for {len(all_images)} images")
            
            if client_id:
                await send_progress(client_id, {
                    "type": "progress",
                    "file_id": pdf_id,
                    "filename": pdf_file.original_filename,
                    "status": "describing_images",
                    "progress": 70
                })

            # Check if API key is provided
            api_key = options.get("openai_compatible_api_key")
            if not api_key:
                logger.warning("Image description enabled but no API key provided. Skipping description.")
            else:
                # Get concurrent request count (default to 2 for rate limit safety)
                max_concurrent = options.get("image_description_concurrent", 2)
                max_concurrent = max(1, min(5, max_concurrent))  # Clamp between 1 and 5 for safety
                
                # Calculate rate limit delay based on concurrent requests
                # If 1 concurrent, no delay needed. If more, add delay to avoid rate limits
                rate_limit_delay = 1.0 if max_concurrent > 1 else 0.0
                
                description_service = ImageDescriptionService(
                    provider=options.get("image_description_provider", "openai_compatible"),
                    api_key=api_key,
                    base_url=options.get("openai_compatible_base_url"),
                    model=options.get("openai_compatible_model", "llava"),
                    rate_limit_delay=rate_limit_delay
                )

                # Filter images that need description (exclude duplicates)
                images_to_describe = [(db_img, pil_img) for db_img, pil_img in all_images if not db_img.is_duplicate]
                
                if images_to_describe:
                    total_images = len(images_to_describe)
                    logger.info(f"Describing {total_images} images with model {options.get('openai_compatible_model', 'llava')}")
                    
                    # Process images in batches with progress updates
                    descriptions = []
                    batch_size = max_concurrent
                    
                    for batch_start in range(0, total_images, batch_size):
                        batch_end = min(batch_start + batch_size, total_images)
                        batch = images_to_describe[batch_start:batch_end]
                        
                        logger.info(f"Processing image batch {batch_start//batch_size + 1}/{(total_images-1)//batch_size + 1} ({batch_start+1}-{batch_end} of {total_images})")
                        
                        try:
                            # Extract PIL Images from ExtractedImage objects
                            batch_images = [img[1].image for img in batch]
                            batch_descriptions = await description_service.batch_describe(
                                batch_images, 
                                max_concurrent=len(batch_images)
                            )
                            descriptions.extend(batch_descriptions)
                            
                            # Send progress update
                            progress_pct = int(70 + (batch_end / total_images) * 15)  # Progress from 70% to 85%
                            if client_id:
                                await send_progress(client_id, {
                                    "type": "progress",
                                    "file_id": pdf_id,
                                    "filename": pdf_file.original_filename,
                                    "status": "describing_images",
                                    "progress": progress_pct,
                                    "current_image": batch_end,
                                    "total_images": total_images
                                })
                            
                            # Save descriptions for this batch
                            for (db_image, _), description in zip(batch, batch_descriptions):
                                db_image.description = description
                                logger.info(f"Saved description for {db_image.image_type} on page {db_image.page_number}: {description[:100]}...")
                            
                            db.commit()
                            
                        except Exception as e:
                            logger.error(f"Error describing image batch: {e}")
                            # Continue with empty descriptions for failed batch
                            for _ in batch:
                                descriptions.append(f"[Error: Failed to generate description - {str(e)}]")

                    logger.info(f"Received {len(descriptions)} descriptions total")

                await description_service.close()

            db.commit()

        # Yield control after image description
        await asyncio.sleep(0)
        
        # Generate markdown file
        if client_id:
            await send_progress(client_id, {
                "type": "progress",
                "file_id": pdf_id,
                "filename": pdf_file.original_filename,
                "status": "generating_markdown",
                "progress": 90
            })
        
        markdown_content = generate_markdown(pages, pdf_file, db, options)
        md_filename = f"{os.path.splitext(pdf_file.original_filename)[0]}.md"
        md_path = os.path.join(output_dir, md_filename)
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # Save output file record
        output_file = OutputFile(
            pdf_file_id=pdf_id,
            output_type="markdown",
            file_path=md_path
        )
        db.add(output_file)

        # Update status
        pdf_file.status = OCRStatus.COMPLETED
        pdf_file.updated_at = datetime.utcnow()
        pdf_file.completed_at = datetime.utcnow()
        pdf_file.processing_duration_seconds = time.time() - start_time
        db.commit()

        # Yield control before sending completion
        await asyncio.sleep(0)
        
        if client_id:
            await send_progress(client_id, {
                "type": "complete",
                "file_id": pdf_id,
                "filename": pdf_file.original_filename,
                "status": "completed",
                "progress": 100,
                "download_url": f"/api/download/{pdf_id}",
                "duration_seconds": pdf_file.processing_duration_seconds
            })
        
        logger.info(f"Completed processing PDF: {pdf_file.original_filename} in {pdf_file.processing_duration_seconds:.2f}s")
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_id}: {e}")
        pdf_file = db.query(PDFFile).filter(PDFFile.id == pdf_id).first()
        if pdf_file:
            pdf_file.status = OCRStatus.FAILED
            pdf_file.error_message = str(e)
            pdf_file.updated_at = datetime.utcnow()
            db.commit()
        
        if client_id:
            await send_progress(client_id, {
                "type": "error",
                "file_id": pdf_id,
                "filename": pdf_file.original_filename if pdf_file else "unknown",
                "status": "failed",
                "error": str(e)
            })
    
    finally:
        db.close()

def generate_markdown(pages, pdf_file, db, options=None):
    """Generate final markdown content"""
    md_parts = []
    options = options or {}
    replace_text_with_description = options.get("replace_text_with_description", False)
    describe_images = options.get("describe_images", False)
    describe_tables = options.get("describe_tables", False)
    
    # Content
    for page in pages:
        # Add page number header
        md_parts.append(f"\n## Page {page.page_number}\n")
        
        # Get images and tables with descriptions for this page
        page_images = []
        page_tables = []
        
        if replace_text_with_description and (describe_images or describe_tables):
            if describe_images:
                page_images = db.query(ExtractedImage).filter(
                    ExtractedImage.pdf_file_id == pdf_file.id,
                    ExtractedImage.page_number == page.page_number,
                    ExtractedImage.description.isnot(None)
                ).all()
            
            if describe_tables:
                page_tables = db.query(ExtractedTable).filter(
                    ExtractedTable.pdf_file_id == pdf_file.id,
                    ExtractedTable.page_number == page.page_number,
                    ExtractedTable.description.isnot(None)
                ).all()
        
        # Build page content
        if replace_text_with_description and (page_images or page_tables):
            # REPLACE text with image/table descriptions - don't show original text
            # Only show a brief note that text was replaced
            if page.text.strip():
                md_parts.append(f"*Original text extracted from this page has been replaced with image descriptions below.*\n")
            
            # Add image descriptions (these REPLACE the original text)
            for img in page_images:
                rel_path = os.path.relpath(img.image_path, os.path.dirname(pdf_file.file_path))
                md_parts.append(f"\n**Image Description:**")
                md_parts.append(f"![Image]({rel_path})")
                md_parts.append(f"{img.description}\n")
            
            # Add table descriptions
            for table in page_tables:
                md_parts.append(f"\n**Table Description:**")
                if table.markdown_content:
                    md_parts.append(table.markdown_content)
                md_parts.append(f"{table.description}\n")
        else:
            # Use original page markdown (normal behavior)
            # Remove existing page header if present to avoid duplication
            page_content = page.markdown
            if page_content.startswith(f"## Page {page.page_number}"):
                # Remove the page header line
                lines = page_content.split('\n')
                if len(lines) > 1:
                    page_content = '\n'.join(lines[1:]).strip()
            md_parts.append(page_content)
    
    # Image descriptions appendix (only if not replacing text)
    if not replace_text_with_description:
        images_with_desc = db.query(ExtractedImage).filter(
            ExtractedImage.pdf_file_id == pdf_file.id,
            ExtractedImage.description.isnot(None)
        ).order_by(ExtractedImage.page_number, ExtractedImage.id).all()
        
        if images_with_desc:
            md_parts.append("\n## Image Descriptions\n")
            
            # Group by image type
            regular_images = [img for img in images_with_desc if img.image_type == 'image']
            drawings = [img for img in images_with_desc if img.image_type == 'drawing']
            
            # Add regular images
            if regular_images:
                md_parts.append("### Images\n")
                for img in regular_images:
                    rel_path = os.path.relpath(img.image_path, os.path.dirname(pdf_file.file_path))
                    md_parts.append(f"#### Image on Page {img.page_number}")
                    md_parts.append(f"![Image]({rel_path})")
                    md_parts.append(f"**Description:** {img.description}\n")
            
            # Add drawings
            if drawings:
                md_parts.append("### Drawings\n")
                for img in drawings:
                    rel_path = os.path.relpath(img.image_path, os.path.dirname(pdf_file.file_path))
                    md_parts.append(f"#### Drawing on Page {img.page_number}")
                    md_parts.append(f"![Drawing]({rel_path})")
                    md_parts.append(f"**Description:** {img.description}\n")
    
    return "\n".join(md_parts)

@app.get("/api/files")
async def list_files(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all processed files"""
    query = db.query(PDFFile)
    
    if status:
        query = query.filter(PDFFile.status == status)
    
    files = query.order_by(PDFFile.created_at.desc()).all()
    
    return [
        {
            "id": f.id,
            "filename": f.original_filename,
            "status": f.status,
            "page_count": f.page_count,
            "created_at": f.created_at.isoformat() + 'Z' if f.created_at else None,
            "error_message": f.error_message
        }
        for f in files
    ]

@app.get("/api/files/{file_id}")
async def get_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Get file details"""
    pdf_file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    
    if not pdf_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    pages = db.query(PDFPage).filter(PDFPage.pdf_file_id == file_id).all()
    images = db.query(ExtractedImage).filter(ExtractedImage.pdf_file_id == file_id).all()
    tables = db.query(ExtractedTable).filter(ExtractedTable.pdf_file_id == file_id).all()
    outputs = db.query(OutputFile).filter(OutputFile.pdf_file_id == file_id).all()
    
    return {
        "id": pdf_file.id,
        "filename": pdf_file.original_filename,
        "status": pdf_file.status,
        "page_count": pdf_file.page_count,
        "current_page": pdf_file.current_page,
        "processing_duration_seconds": pdf_file.processing_duration_seconds,
        "file_size": pdf_file.file_size,
        "created_at": pdf_file.created_at.isoformat() + 'Z' if pdf_file.created_at else None,
        "updated_at": pdf_file.updated_at.isoformat() + 'Z' if pdf_file.updated_at else None,
        "completed_at": pdf_file.completed_at.isoformat() + 'Z' if pdf_file.completed_at else None,
        "error_message": pdf_file.error_message,
        "use_ocr": pdf_file.use_ocr,
        "ocr_engine": pdf_file.ocr_engine,
        "pages": [{"page_number": p.page_number, "has_images": p.has_images, "has_tables": p.has_tables} for p in pages],
        "image_count": len([i for i in images if not i.is_duplicate]),
        "duplicate_count": len([i for i in images if i.is_duplicate]),
        "table_count": len(tables),
        "outputs": [{"type": o.output_type, "path": o.file_path} for o in outputs]
    }

@app.delete("/api/files/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Delete a file and all associated data"""
    pdf_file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    
    if not pdf_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Delete physical files
        if os.path.exists(pdf_file.file_path):
            os.remove(pdf_file.file_path)
        
        # Delete output files
        output_files = db.query(OutputFile).filter(OutputFile.pdf_file_id == file_id).all()
        for output in output_files:
            if os.path.exists(output.file_path):
                os.remove(output.file_path)
        
        # Delete extracted images
        images = db.query(ExtractedImage).filter(ExtractedImage.pdf_file_id == file_id).all()
        for img in images:
            if img.image_path and os.path.exists(img.image_path):
                os.remove(img.image_path)
        
        # Delete from database (cascade will handle related records)
        db.delete(pdf_file)
        db.commit()
        
        return {"message": "File deleted successfully", "file_id": file_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

@app.post("/api/test-connection/image-description")
async def test_image_description_connection(
    provider: str = Form("openai_compatible"),
    api_key: Optional[str] = Form(None),
    base_url: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
):
    """Test connection to image description API"""
    try:
        from utils.image_description import ImageDescriptionService
        
        service = ImageDescriptionService(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model or "llava"
        )
        
        # Create a simple test image
        from PIL import Image
        import io
        test_img = Image.new('RGB', (100, 100), color='red')
        
        # Try to get a description
        description = await service.describe_image(
            test_img,
            prompt="What color is this image?",
            max_tokens=50
        )
        
        await service.close()
        
        return {
            "success": True,
            "message": "Connection successful",
            "test_response": description[:100] if description else "No response"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }

@app.post("/api/test-connection/cloud-ocr")
async def test_cloud_ocr_connection(
    provider: str = Form("aws"),
    aws_access_key_id: Optional[str] = Form(None),
    aws_secret_access_key: Optional[str] = Form(None),
    aws_region: Optional[str] = Form("us-east-1"),
):
    """Test connection to Cloud OCR service"""
    try:
        config = {
            "provider": provider,
        }
        
        if provider == "aws":
            config.update({
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
                "aws_region": aws_region,
            })
        
        from ocr_engines import OCREngineFactory
        engine = OCREngineFactory.create_engine("cloud", config)
        
        if engine.is_available():
            return {
                "success": True,
                "message": f"{provider.upper()} OCR connection successful"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to initialize {provider.upper()} OCR client"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }

@app.get("/api/download/{file_id}")
async def download_file(
    file_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Download processed markdown file with extracted assets as a zip archive"""
    import zipfile
    import tempfile
    from fastapi.responses import FileResponse
    
    # Get PDF file info
    pdf_file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not pdf_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get output markdown file
    output_file = db.query(OutputFile).filter(
        OutputFile.pdf_file_id == file_id,
        OutputFile.output_type == "markdown"
    ).first()
    
    if not output_file or not os.path.exists(output_file.file_path):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    # Create a temporary zip file on disk
    base_name = os.path.splitext(pdf_file.original_filename)[0]
    temp_zip_path = tempfile.mktemp(suffix='.zip')
    
    try:
        # Create zip file on disk (much faster than memory for large files)
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add markdown file
            md_filename = f"{base_name}.md"
            zip_file.write(output_file.file_path, md_filename)
            
            # Get extracted images
            images = db.query(ExtractedImage).filter(
                ExtractedImage.pdf_file_id == file_id,
                ExtractedImage.is_duplicate == False  # Only include non-duplicate images
            ).all()
            
            logger.info(f"Adding {len(images)} images to download for file {file_id}")
            
            for img in images:
                if img.image_path and os.path.exists(img.image_path):
                    # Determine subfolder based on image type
                    if img.image_type == 'drawing':
                        subfolder = 'drawings'
                    elif img.image_type == 'table_image':
                        subfolder = 'tables'
                    else:
                        subfolder = 'images'
                    
                    # Get filename from path
                    img_filename = os.path.basename(img.image_path)
                    # Add image to zip with organized folder structure
                    zip_file.write(
                        img.image_path, 
                        f"{subfolder}/page_{img.page_number}_{img_filename}"
                    )
            
            # Get extracted tables metadata
            tables = db.query(ExtractedTable).filter(
                ExtractedTable.pdf_file_id == file_id
            ).all()
            
            # Add table metadata as JSON
            if tables:
                import json
                table_data = []
                for table in tables:
                    table_info = {
                        "page_number": table.page_number,
                        "data": table.table_data,
                        "markdown": table.markdown_content,
                        "description": table.description
                    }
                    table_data.append(table_info)
                
                # Write table metadata to JSON file in zip
                tables_json = json.dumps(table_data, indent=2, default=str)
                zip_file.writestr(
                    "tables_metadata.json",
                    tables_json
                )
        
        # Schedule cleanup of temp file after response
        def cleanup_temp_file():
            try:
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
                    logger.info(f"Cleaned up temp file: {temp_zip_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup temp file: {e}")
        
        background_tasks.add_task(cleanup_temp_file)
        
        # Return file response (supports streaming and range requests)
        return FileResponse(
            temp_zip_path,
            media_type="application/zip",
            filename=f"{base_name}.zip"
        )
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        logger.error(f"Error creating download zip: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating download: {str(e)}")

@app.post("/api/download/batch")
async def download_batch_files(
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Download multiple markdown files with extracted assets as a zip archive"""
    import zipfile
    import tempfile
    from fastapi.responses import FileResponse
    
    file_ids = request.get("file_ids", [])
    
    if not file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    
    # Create a temporary zip file on disk
    temp_zip_path = tempfile.mktemp(suffix='.zip')
    
    try:
        # Create zip file on disk (much faster than memory for large files)
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_id in file_ids:
                # Get PDF file info
                pdf_file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
                if not pdf_file:
                    continue
                    
                # Create folder name based on original filename (without extension)
                base_name = os.path.splitext(pdf_file.original_filename)[0]
                folder_name = f"{base_name}_{file_id}"
                
                # Get output markdown file
                output_file = db.query(OutputFile).filter(
                    OutputFile.pdf_file_id == file_id,
                    OutputFile.output_type == "markdown"
                ).first()
                
                if output_file and os.path.exists(output_file.file_path):
                    # Add markdown file to zip with folder prefix
                    md_filename = f"{base_name}.md"
                    zip_file.write(output_file.file_path, f"{folder_name}/{md_filename}")
                
                # Get extracted images
                images = db.query(ExtractedImage).filter(
                    ExtractedImage.pdf_file_id == file_id,
                    ExtractedImage.is_duplicate == False  # Only include non-duplicate images
                ).all()
                
                logger.info(f"Adding {len(images)} images to batch download for file {file_id}")
                
                for img in images:
                    if img.image_path and os.path.exists(img.image_path):
                        # Determine subfolder based on image type
                        if img.image_type == 'drawing':
                            subfolder = 'drawings'
                        elif img.image_type == 'table_image':
                            subfolder = 'tables'
                        else:
                            subfolder = 'images'
                        
                        # Get filename from path
                        img_filename = os.path.basename(img.image_path)
                        # Add image to zip with organized folder structure
                        zip_file.write(
                            img.image_path, 
                            f"{folder_name}/{subfolder}/page_{img.page_number}_{img_filename}"
                        )
                
                # Get extracted tables (if they have associated images)
                tables = db.query(ExtractedTable).filter(
                    ExtractedTable.pdf_file_id == file_id
                ).all()
                
                # Add table metadata as JSON
                if tables:
                    import json
                    table_data = []
                    for table in tables:
                        table_info = {
                            "page_number": table.page_number,
                            "data": table.table_data,
                            "markdown": table.markdown_content,
                            "description": table.description
                        }
                        table_data.append(table_info)
                    
                    # Write table metadata to JSON file in zip
                    tables_json = json.dumps(table_data, indent=2, default=str)
                    zip_file.writestr(
                        f"{folder_name}/tables_metadata.json",
                        tables_json
                    )
        
        # Schedule cleanup of temp file after response
        def cleanup_temp_file():
            try:
                if os.path.exists(temp_zip_path):
                    os.remove(temp_zip_path)
                    logger.info(f"Cleaned up batch temp file: {temp_zip_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup batch temp file: {e}")
        
        background_tasks.add_task(cleanup_temp_file)
        
        # Return file response (supports streaming and range requests)
        return FileResponse(
            temp_zip_path,
            media_type="application/zip",
            filename=f"pdf2md_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
        )
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        logger.error(f"Error creating batch download zip: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating download: {str(e)}")

@app.get("/api/ocr-engines")
async def list_ocr_engines():
    """List available OCR engines"""
    return OCREngineFactory.list_available_engines()

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)