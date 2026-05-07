import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import io
import os
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from imagehash import phash
import cv2

logger = logging.getLogger(__name__)

@dataclass
class ExtractedImage:
    """Represents an extracted image from PDF"""
    image: Image.Image
    page_number: int
    bbox: Tuple[float, float, float, float]
    image_type: str  # 'image', 'drawing', 'table'
    hash: Optional[str] = None
    is_duplicate: bool = False
    original_image_id: Optional[int] = None

@dataclass
class ExtractedTable:
    """Represents an extracted table from PDF"""
    page_number: int
    bbox: Tuple[float, float, float, float]
    data: List[List[str]]
    markdown: str
    image: Optional[Image.Image] = None

@dataclass
class ProcessedPage:
    """Represents a processed PDF page"""
    page_number: int
    text: str
    markdown: str
    images: List[ExtractedImage]
    tables: List[ExtractedTable]
    has_images: bool
    has_tables: bool
    has_drawings: bool

class PDFProcessor:
    """Process PDF files to extract text, images, tables, and drawings"""
    
    def __init__(
        self,
        enable_image_dedup: bool = False,
        dedup_threshold: float = 0.9,
        hash_size: int = 16
    ):
        self.enable_image_dedup = enable_image_dedup
        self.dedup_threshold = dedup_threshold
        self.hash_size = hash_size
        self.image_hashes: Dict[str, int] = {}  # hash -> image_id mapping
        
    def process_pdf(
        self,
        pdf_path: str,
        extract_images: bool = True,
        extract_tables: bool = True,
        extract_drawings: bool = True,
        use_ocr: bool = False,
        ocr_engine = None
    ) -> List[ProcessedPage]:
        """
        Process a PDF file and extract all content
        
        Args:
            pdf_path: Path to the PDF file
            extract_images: Whether to extract images
            extract_tables: Whether to extract tables
            extract_drawings: Whether to extract vector drawings
            use_ocr: Whether to use OCR for text extraction
            ocr_engine: OCR engine instance (required if use_ocr=True)
            
        Returns:
            List of ProcessedPage objects
        """
        pages = []
        
        try:
            # Open with PyMuPDF for images and drawings
            doc = fitz.open(pdf_path)
            
            # Open with pdfplumber for tables and text
            with pdfplumber.open(pdf_path) as pdf:
                for page_num in range(len(doc)):
                    page_number = page_num + 1
                    logger.info(f"Processing page {page_number}")
                    
                    # Get PyMuPDF page
                    fitz_page = doc[page_num]
                    # Get pdfplumber page
                    plumber_page = pdf.pages[page_num] if page_num < len(pdf.pages) else None
                    
                    # Process the page
                    processed_page = self._process_page(
                        fitz_page,
                        plumber_page,
                        page_number,
                        extract_images,
                        extract_tables,
                        extract_drawings,
                        use_ocr,
                        ocr_engine
                    )
                    pages.append(processed_page)
                    
            doc.close()
            
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise
            
        return pages
    
    def _process_page(
        self,
        fitz_page,
        plumber_page,
        page_number: int,
        extract_images: bool,
        extract_tables: bool,
        extract_drawings: bool,
        use_ocr: bool,
        ocr_engine
    ) -> ProcessedPage:
        """Process a single page"""
        
        images = []
        tables = []
        has_drawings = False
        
        # Extract text
        if use_ocr and ocr_engine:
            # Convert page to image for OCR
            pix = fitz_page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            page_result = ocr_engine.process_pdf_page(img, page_number)
            text = page_result.text
        else:
            # Direct text extraction
            text = fitz_page.get_text()
        
        # Extract images
        if extract_images:
            images.extend(self._extract_images(fitz_page, page_number))
        
        # Extract tables
        if extract_tables and plumber_page:
            tables.extend(self._extract_tables(plumber_page, page_number))
        
        # Extract drawings (vector graphics)
        if extract_drawings:
            drawings = self._extract_drawings(fitz_page, page_number)
            if drawings:
                images.extend(drawings)
                has_drawings = True
        
        # Deduplicate images if enabled
        if self.enable_image_dedup and images:
            images = self._deduplicate_images(images)
        
        # Convert to markdown
        markdown = self._convert_to_markdown(
            text, images, tables, page_number
        )
        
        return ProcessedPage(
            page_number=page_number,
            text=text,
            markdown=markdown,
            images=images,
            tables=tables,
            has_images=len(images) > 0,
            has_tables=len(tables) > 0,
            has_drawings=has_drawings
        )
    
    def _extract_images(
        self,
        fitz_page,
        page_number: int
    ) -> List[ExtractedImage]:
        """Extract images from a page"""
        images = []
        
        try:
            # Get image list
            image_list = fitz_page.get_images(full=True)
            
            for img_index, img in enumerate(image_list, start=1):
                xref = img[0]
                base_image = fitz_page.parent.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Convert to PIL Image
                try:
                    pil_image = Image.open(io.BytesIO(image_bytes))
                    if pil_image.mode in ('RGBA', 'LA', 'P'):
                        pil_image = pil_image.convert('RGB')
                    
                    # Calculate hash for deduplication
                    img_hash = self._compute_image_hash(pil_image)
                    
                    extracted = ExtractedImage(
                        image=pil_image,
                        page_number=page_number,
                        bbox=(0, 0, pil_image.width, pil_image.height),
                        image_type='image',
                        hash=img_hash
                    )
                    images.append(extracted)
                    
                except Exception as e:
                    logger.warning(f"Failed to process image {img_index} on page {page_number}: {e}")
                    
        except Exception as e:
            logger.error(f"Error extracting images from page {page_number}: {e}")
        
        return images
    
    def _extract_tables(
        self,
        plumber_page,
        page_number: int
    ) -> List[ExtractedTable]:
        """Extract tables from a page using pdfplumber"""
        tables = []
        
        try:
            # Find tables
            detected_tables = plumber_page.find_tables()
            
            for table_idx, table in enumerate(detected_tables):
                try:
                    # Extract table data
                    table_data = table.extract()
                    
                    if table_data and len(table_data) > 0:
                        # Convert to markdown
                        markdown = self._table_to_markdown(table_data)
                        
                        # Create table image if needed
                        im = plumber_page.to_image()
                        im.draw_rect(table.bbox, stroke="red", stroke_width=2)
                        table_img = im.original
                        
                        extracted_table = ExtractedTable(
                            page_number=page_number,
                            bbox=table.bbox,
                            data=table_data,
                            markdown=markdown,
                            image=table_img
                        )
                        tables.append(extracted_table)
                        
                except Exception as e:
                    logger.warning(f"Failed to extract table {table_idx} on page {page_number}: {e}")
                    
        except Exception as e:
            logger.error(f"Error extracting tables from page {page_number}: {e}")
        
        return tables
    
    def _extract_drawings(
        self,
        fitz_page,
        page_number: int
    ) -> List[ExtractedImage]:
        """Extract vector drawings from a page"""
        drawings = []
        
        try:
            # Get drawings (vector graphics)
            drawings_list = fitz_page.get_drawings()
            
            if drawings_list:
                # Render page to image to capture drawings
                pix = fitz_page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # For now, we capture the whole page as a drawing image
                # In a more sophisticated implementation, we could crop to drawing bounds
                img_hash = self._compute_image_hash(img)
                
                drawing = ExtractedImage(
                    image=img,
                    page_number=page_number,
                    bbox=(0, 0, img.width, img.height),
                    image_type='drawing',
                    hash=img_hash
                )
                drawings.append(drawing)
                
        except Exception as e:
            logger.error(f"Error extracting drawings from page {page_number}: {e}")
        
        return drawings
    
    def _compute_image_hash(self, image: Image.Image) -> str:
        """Compute perceptual hash of an image"""
        try:
            # Use perceptual hash
            hash_value = str(phash(image, hash_size=self.hash_size))
            return hash_value
        except Exception as e:
            logger.warning(f"Failed to compute image hash: {e}")
            # Fallback to simple hash
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            return hashlib.md5(img_bytes.getvalue()).hexdigest()
    
    def _deduplicate_images(
        self,
        images: List[ExtractedImage]
    ) -> List[ExtractedImage]:
        """Remove duplicate images based on perceptual hashing"""
        unique_images = []
        
        for img in images:
            if not img.hash:
                unique_images.append(img)
                continue
            
            # Check if this hash already exists
            is_duplicate = False
            for existing_hash, existing_id in self.image_hashes.items():
                # Compute hash similarity (hamming distance)
                similarity = self._hash_similarity(img.hash, existing_hash)
                
                if similarity >= self.dedup_threshold:
                    img.is_duplicate = True
                    img.original_image_id = existing_id
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                self.image_hashes[img.hash] = id(img)
                unique_images.append(img)
        
        return unique_images
    
    def _hash_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two perceptual hashes"""
        try:
            # Convert hex strings to integers
            h1 = int(hash1, 16)
            h2 = int(hash2, 16)
            
            # Calculate Hamming distance
            xor = h1 ^ h2
            distance = bin(xor).count('1')
            max_distance = len(hash1) * 4  # hex to bits
            
            # Convert to similarity (1.0 = identical, 0.0 = completely different)
            similarity = 1.0 - (distance / max_distance)
            return similarity
        except Exception:
            return 0.0
    
    def _table_to_markdown(self, table_data: List[List[str]]) -> str:
        """Convert table data to markdown format"""
        if not table_data or len(table_data) == 0:
            return ""
        
        md_lines = []
        
        # Header row
        header = table_data[0]
        md_lines.append("| " + " | ".join(str(cell or "") for cell in header) + " |")
        
        # Separator
        md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        # Data rows
        for row in table_data[1:]:
            md_lines.append("| " + " | ".join(str(cell or "") for cell in row) + " |")
        
        return "\n".join(md_lines)
    
    def _convert_to_markdown(
        self,
        text: str,
        images: List[ExtractedImage],
        tables: List[ExtractedTable],
        page_number: int
    ) -> str:
        """Convert page content to markdown"""
        md_parts = []
        
        # Add page header
        md_parts.append(f"## Page {page_number}\n")
        
        # Add text content
        if text.strip():
            md_parts.append(text.strip())
            md_parts.append("")
        
        # Add tables
        for table in tables:
            md_parts.append(table.markdown)
            md_parts.append("")
        
        # Add image placeholders
        for idx, img in enumerate(images):
            if not img.is_duplicate:
                md_parts.append(f"![Image {idx + 1} - Page {page_number}](./images/page_{page_number}_img_{idx + 1}.png)")
                md_parts.append("")
        
        return "\n".join(md_parts)
    
    def reset_deduplication_cache(self):
        """Reset the image deduplication cache"""
        self.image_hashes.clear()