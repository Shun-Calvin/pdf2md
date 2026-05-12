"""
Docling parser integration for advanced document understanding.
Docling provides state-of-the-art document parsing with layout analysis.

This module will work in fallback mode if docling is not installed.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from PIL import Image
import io

logger = logging.getLogger(__name__)

# Try to import docling, set flag if not available
try:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import ConversionResult
    from docling.document_converter import DocumentConverter
    from docling.datamodel.settings import settings as docling_settings
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False
    logger.warning("Docling not installed. DoclingParser will use fallback mode.")


@dataclass
class DoclingElement:
    """Represents a parsed document element"""
    element_type: str  # 'text', 'table', 'image', 'heading', 'list', etc.
    content: str
    bbox: Optional[tuple] = None
    page_number: int = 0
    metadata: Dict[str, Any] = None
    image: Optional[Image.Image] = None


class DoclingParser:
    """
    Parser using Docling for advanced document understanding.
    Supports layout analysis, table detection, and structured output.
    
    Falls back to standard parsing if docling is not installed.
    """
    
    def __init__(
        self,
        enable_ocr: bool = True,
        ocr_engine: str = "tesseract",
        enable_table_detection: bool = True,
        enable_figure_detection: bool = True,
        enable_layout_analysis: bool = True
    ):
        self.enable_ocr = enable_ocr
        self.ocr_engine = ocr_engine
        self.enable_table_detection = enable_table_detection
        self.enable_figure_detection = enable_figure_detection
        self.enable_layout_analysis = enable_layout_analysis
        
        self._converter = None
        
        if not DOCLING_AVAILABLE:
            logger.warning("DoclingParser initialized in fallback mode. Install docling for full functionality.")
        
    def _get_converter(self):
        """Lazy load the Docling converter"""
        if self._converter is None and DOCLING_AVAILABLE:
            # Configure OCR settings
            if self.enable_ocr:
                docling_settings.ocr.enabled = True
                docling_settings.ocr.engine = self.ocr_engine
            else:
                docling_settings.ocr.enabled = False
                
            # Configure pipeline features
            docling_settings.pipeline.features.table_structure = self.enable_table_detection
            docling_settings.pipeline.features.figure_extraction = self.enable_figure_detection
            docling_settings.pipeline.features.layout_analysis = self.enable_layout_analysis
            
            self._converter = DocumentConverter()
            
        return self._converter
    
    def parse_document(
        self,
        file_path: str,
        extract_images: bool = True,
        extract_tables: bool = True
    ) -> List[DoclingElement]:
        """
        Parse a document using Docling
        
        Args:
            file_path: Path to the document file
            extract_images: Whether to extract images
            extract_tables: Whether to extract tables
            
        Returns:
            List of document elements
        """
        elements = []
        
        if not DOCLING_AVAILABLE:
            # Fallback: use standard PDF processor
            logger.info("Using fallback parsing (docling not installed)")
            return self._fallback_parse(file_path, extract_images, extract_tables)
        
        try:
            converter = self._get_converter()
            if converter is None:
                return self._fallback_parse(file_path, extract_images, extract_tables)
            
            # Convert the document
            result = converter.convert(Path(file_path))
            
            if not result or not result.document:
                logger.error(f"Failed to convert document: {file_path}")
                return elements
            
            # Extract elements from each page
            for page_num, page in enumerate(result.document.pages, start=1):
                page_elements = self._extract_page_elements(
                    page, page_num, extract_images, extract_tables
                )
                elements.extend(page_elements)
            
            logger.info(f"Successfully parsed {file_path} with {len(elements)} elements")
            
        except Exception as e:
            logger.error(f"Error parsing document with Docling: {e}")
            logger.info("Falling back to standard parser")
            return self._fallback_parse(file_path, extract_images, extract_tables)
            
        return elements
    
    def _fallback_parse(
        self,
        file_path: str,
        extract_images: bool,
        extract_tables: bool
    ) -> List[DoclingElement]:
        """Fallback parsing using standard PDF processor"""
        from utils.pdf_processor import PDFProcessor
        
        processor = PDFProcessor()
        pages = processor.process_pdf(
            file_path,
            extract_images=extract_images,
            extract_tables=extract_tables
        )
        
        elements = []
        for page in pages:
            # Add text element
            elements.append(DoclingElement(
                element_type='text',
                content=page.text,
                page_number=page.page_number
            ))
            
            # Add table elements
            for table in page.tables:
                elements.append(DoclingElement(
                    element_type='table',
                    content=table.markdown,
                    page_number=page.page_number
                ))
            
            # Add image elements
            for img in page.images:
                if not img.is_duplicate:
                    elements.append(DoclingElement(
                        element_type='image',
                        content=f'Image on page {page.page_number}',
                        page_number=page.page_number,
                        image=img.image
                    ))
        
        return elements
    
    def _extract_page_elements(
        self,
        page,
        page_number: int,
        extract_images: bool,
        extract_tables: bool
    ) -> List[DoclingElement]:
        """Extract elements from a single page"""
        elements = []
        
        if not DOCLING_AVAILABLE:
            return elements
        
        try:
            # Extract text with layout information
            if hasattr(page, 'text'):
                text_element = DoclingElement(
                    element_type='text',
                    content=page.text,
                    page_number=page_number,
                    metadata={'layout_type': 'body'}
                )
                elements.append(text_element)
            
            # Extract headings
            if hasattr(page, 'headings'):
                for heading in page.headings:
                    element = DoclingElement(
                        element_type='heading',
                        content=heading.text,
                        bbox=getattr(heading, 'bbox', None),
                        page_number=page_number,
                        metadata={'level': getattr(heading, 'level', 1)}
                    )
                    elements.append(element)
            
            # Extract lists
            if hasattr(page, 'lists'):
                for list_item in page.lists:
                    element = DoclingElement(
                        element_type='list',
                        content=list_item.text,
                        bbox=getattr(list_item, 'bbox', None),
                        page_number=page_number
                    )
                    elements.append(element)
            
            # Extract tables
            if extract_tables and hasattr(page, 'tables'):
                for table in page.tables:
                    table_data = self._convert_table_to_markdown(table)
                    element = DoclingElement(
                        element_type='table',
                        content=table_data['markdown'],
                        bbox=getattr(table, 'bbox', None),
                        page_number=page_number,
                        metadata={
                            'rows': table_data.get('rows', 0),
                            'cols': table_data.get('cols', 0),
                            'data': table_data.get('data', [])
                        }
                    )
                    elements.append(element)
            
            # Extract figures/images
            if extract_images and hasattr(page, 'figures'):
                for figure in page.figures:
                    img = self._extract_figure_image(figure)
                    element = DoclingElement(
                        element_type='image',
                        content=getattr(figure, 'caption', ''),
                        bbox=getattr(figure, 'bbox', None),
                        page_number=page_number,
                        image=img,
                        metadata={'caption': getattr(figure, 'caption', '')}
                    )
                    elements.append(element)
            
        except Exception as e:
            logger.warning(f"Error extracting elements from page {page_number}: {e}")
        
        return elements
    
    def _convert_table_to_markdown(self, table) -> Dict[str, Any]:
        """Convert Docling table to markdown format"""
        result = {
            'markdown': '',
            'data': [],
            'rows': 0,
            'cols': 0
        }
        
        if not DOCLING_AVAILABLE:
            return result
        
        try:
            if hasattr(table, 'data') and table.data:
                table_data = table.data
                result['data'] = table_data
                result['rows'] = len(table_data)
                result['cols'] = len(table_data[0]) if table_data else 0
                
                # Convert to markdown
                md_lines = []
                
                # Header
                if table_data:
                    header = table_data[0]
                    md_lines.append("| " + " | ".join(str(cell or "") for cell in header) + " |")
                    md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
                    
                    # Data rows
                    for row in table_data[1:]:
                        md_lines.append("| " + " | ".join(str(cell or "") for cell in row) + " |")
                
                result['markdown'] = "\n".join(md_lines)
                
        except Exception as e:
            logger.warning(f"Error converting table to markdown: {e}")
        
        return result
    
    def _extract_figure_image(self, figure) -> Optional[Image.Image]:
        """Extract image from a figure element"""
        if not DOCLING_AVAILABLE:
            return None
        
        try:
            if hasattr(figure, 'image') and figure.image:
                # Convert to PIL Image
                if isinstance(figure.image, bytes):
                    return Image.open(io.BytesIO(figure.image))
                elif hasattr(figure.image, 'tobytes'):
                    return Image.fromarray(figure.image)
        except Exception as e:
            logger.warning(f"Error extracting figure image: {e}")
        
        return None
    
    def convert_to_markdown(self, elements: List[DoclingElement]) -> str:
        """Convert extracted elements to markdown format"""
        md_parts = []
        current_page = 0
        
        for element in elements:
            # Add page header when page changes
            if element.page_number != current_page:
                current_page = element.page_number
                md_parts.append(f"\n## Page {current_page}\n")
            
            # Format based on element type
            if element.element_type == 'heading':
                level = element.metadata.get('level', 1) if element.metadata else 1
                md_parts.append(f"{'#' * level} {element.content}\n")
                
            elif element.element_type == 'text':
                md_parts.append(f"{element.content}\n")
                
            elif element.element_type == 'list':
                md_parts.append(f"- {element.content}\n")
                
            elif element.element_type == 'table':
                md_parts.append(f"\n{element.content}\n")
                
            elif element.element_type == 'image':
                caption = element.metadata.get('caption', '') if element.metadata else ''
                if caption:
                    md_parts.append(f"\n![{caption}](image_placeholder)\n")
                else:
                    md_parts.append(f"\n![Image](image_placeholder)\n")
        
        return "\n".join(md_parts)


class DoclingOCRAdapter:
    """
    Adapter to use Docling as an OCR engine compatible with existing OCR interface.
    Falls back to standard OCR if docling is not available.
    """
    
    def __init__(self, **kwargs):
        if DOCLING_AVAILABLE:
            self.parser = DoclingParser(enable_ocr=True, **kwargs)
        else:
            self.parser = None
            logger.warning("DoclingOCRAdapter: docling not available, using fallback")
        
    def process_pdf_page(self, image, page_number: int) -> Any:
        """
        Process a PDF page image using Docling OCR.
        Compatible with existing OCR engine interface.
        """
        from ocr_engines.base import OCRResult
        
        if not DOCLING_AVAILABLE or self.parser is None:
            # Fallback: return empty result
            return OCRResult(
                text="",
                confidence=0.0,
                page_number=page_number,
                blocks=[]
            )
        
        # Save image temporarily for Docling processing
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            image.save(tmp.name)
            tmp_path = tmp.name
        
        try:
            # Parse the image
            elements = self.parser.parse_document(tmp_path, extract_images=False, extract_tables=False)
            
            # Combine text from all elements
            text_parts = []
            for elem in elements:
                if elem.element_type in ['text', 'heading']:
                    text_parts.append(elem.content)
            
            full_text = "\n".join(text_parts)
            
            # Create OCR result
            return OCRResult(
                text=full_text,
                confidence=0.9,  # Docling doesn't provide confidence scores directly
                page_number=page_number,
                blocks=[]
            )
            
        finally:
            # Cleanup temporary file
            Path(tmp_path).unlink(missing_ok=True)
