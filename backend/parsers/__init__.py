"""
Integration module for Docling and Open Data Loader with existing PDF2MD system.
Provides unified interface for document parsing.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from app.config import settings

logger = logging.getLogger(__name__)


class ParserType(str, Enum):
    """Available parser types"""
    STANDARD = "standard"  # Current PyMuPDF + pdfplumber
    DOCLING = "docling"    # Docling with layout analysis
    ODL_BATCH = "odl_batch"  # Open Data Loader batch processing


class DocumentParser:
    """
    Unified document parser that can switch between different parsing engines.
    """
    
    def __init__(
        self,
        parser_type: Optional[ParserType] = None,
        extract_images: bool = True,
        extract_tables: bool = True,
        use_ocr: bool = False,
        ocr_engine = None,
        progress_callback: Optional[Callable] = None
    ):
        self.parser_type = parser_type or self._get_default_parser_type()
        self.extract_images = extract_images
        self.extract_tables = extract_tables
        self.use_ocr = use_ocr
        self.ocr_engine = ocr_engine
        self.progress_callback = progress_callback
        
        self._parser = None
        self._batch_processor = None
        
    def _get_default_parser_type(self) -> ParserType:
        """Get default parser type from settings"""
        if settings.USE_DOCLING:
            return ParserType.DOCLING
        elif settings.USE_OPEN_DATA_LOADER:
            return ParserType.ODL_BATCH
        return ParserType.STANDARD
    
    def _get_parser(self):
        """Lazy load the appropriate parser"""
        if self._parser is None:
            if self.parser_type == ParserType.DOCLING:
                from parsers.docling_parser import DoclingParser
                self._parser = DoclingParser(
                    enable_ocr=self.use_ocr,
                    ocr_engine=settings.DOCLING_OCR_ENGINE,
                    enable_table_detection=self.extract_tables and settings.DOCLING_ENABLE_TABLE_DETECTION,
                    enable_figure_detection=self.extract_images and settings.DOCLING_ENABLE_FIGURE_DETECTION,
                    enable_layout_analysis=settings.DOCLING_ENABLE_LAYOUT_ANALYSIS
                )
                logger.info("Initialized Docling parser")
                
            elif self.parser_type == ParserType.STANDARD:
                from utils.pdf_processor import PDFProcessor
                self._parser = PDFProcessor(
                    enable_image_dedup=settings.ENABLE_IMAGE_DEDUPLICATION,
                    dedup_threshold=settings.IMAGE_DEDUP_THRESHOLD,
                    hash_size=settings.IMAGE_DEDUP_HASH_SIZE
                )
                logger.info("Initialized standard PDF parser")
                
        return self._parser
    
    def _get_batch_processor(self):
        """Lazy load batch processor for Open Data Loader"""
        if self._batch_processor is None and self.parser_type == ParserType.ODL_BATCH:
            from parsers.open_data_loader import BatchDocumentProcessor
            self._batch_processor = BatchDocumentProcessor(
                batch_size=settings.ODL_BATCH_SIZE,
                num_workers=settings.ODL_NUM_WORKERS,
                use_docling=settings.USE_DOCLING,
                extract_images=self.extract_images,
                extract_tables=self.extract_tables,
                use_ocr=self.use_ocr,
                ocr_engine=self.ocr_engine
            )
            if self.progress_callback:
                self._batch_processor.register_progress_callback(self.progress_callback)
            logger.info("Initialized Open Data Loader batch processor")
            
        return self._batch_processor
    
    def parse_single(
        self,
        file_path: str,
        file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse a single document
        
        Args:
            file_path: Path to the document
            file_id: Optional file identifier
            
        Returns:
            Dictionary with parsed content
        """
        if self.parser_type == ParserType.ODL_BATCH:
            # Use Open Data Loader for single file processing
            processor = self._get_batch_processor()
            result = processor.process_single(file_path, file_id)
            
            return {
                'success': result.success,
                'file_id': result.file_id,
                'file_path': result.file_path,
                'markdown': result.markdown,
                'elements': result.elements,
                'processing_time': result.processing_time,
                'error': result.error,
                'metadata': result.metadata
            }
        
        elif self.parser_type == ParserType.DOCLING:
            # Use Docling parser
            parser = self._get_parser()
            elements = parser.parse_document(
                file_path,
                extract_images=self.extract_images,
                extract_tables=self.extract_tables
            )
            markdown = parser.convert_to_markdown(elements)
            
            return {
                'success': True,
                'file_id': file_id,
                'file_path': file_path,
                'markdown': markdown,
                'elements': elements,
                'processing_time': 0,  # Not tracked in this mode
                'error': None,
                'metadata': {'element_count': len(elements)}
            }
        
        else:
            # Use standard parser
            parser = self._get_parser()
            pages = parser.process_pdf(
                file_path,
                extract_images=self.extract_images,
                extract_tables=self.extract_tables,
                extract_drawings=self.extract_images,
                use_ocr=self.use_ocr,
                ocr_engine=self.ocr_engine
            )
            
            # Convert to unified format
            markdown_parts = []
            elements = []
            
            for page in pages:
                markdown_parts.append(page.markdown)
                elements.append({
                    'page_number': page.page_number,
                    'text': page.text,
                    'images': page.images,
                    'tables': page.tables,
                    'has_images': page.has_images,
                    'has_tables': page.has_tables
                })
            
            return {
                'success': True,
                'file_id': file_id,
                'file_path': file_path,
                'markdown': '\n\n'.join(markdown_parts),
                'elements': elements,
                'processing_time': 0,
                'error': None,
                'metadata': {
                    'page_count': len(pages),
                    'element_count': len(elements)
                }
            }
    
    def parse_batch(
        self,
        file_paths: List[str],
        file_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse multiple documents
        
        Args:
            file_paths: List of file paths
            file_ids: Optional list of file identifiers
            
        Returns:
            List of result dictionaries
        """
        if file_ids is None:
            file_ids = [None] * len(file_paths)
        
        results = []
        
        if self.parser_type == ParserType.ODL_BATCH:
            # Use Open Data Loader for efficient batch processing
            processor = self._get_batch_processor()
            
            for result in processor.process_files(file_paths):
                results.append({
                    'success': result.success,
                    'file_id': result.file_id,
                    'file_path': result.file_path,
                    'markdown': result.markdown,
                    'elements': result.elements,
                    'processing_time': result.processing_time,
                    'error': result.error,
                    'metadata': result.metadata
                })
        else:
            # Process sequentially for other parsers
            for file_path, file_id in zip(file_paths, file_ids):
                try:
                    result = self.parse_single(file_path, file_id)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
                    results.append({
                        'success': False,
                        'file_id': file_id,
                        'file_path': file_path,
                        'markdown': '',
                        'elements': [],
                        'processing_time': 0,
                        'error': str(e),
                        'metadata': {}
                    })
        
        return results


def create_parser(
    parser_type: Optional[str] = None,
    **kwargs
) -> DocumentParser:
    """
    Factory function to create a document parser
    
    Args:
        parser_type: Type of parser ('standard', 'docling', 'odl_batch')
        **kwargs: Additional parser options
        
    Returns:
        DocumentParser instance
    """
    if parser_type:
        parser_type = ParserType(parser_type)
    
    return DocumentParser(parser_type=parser_type, **kwargs)


def get_available_parsers() -> Dict[str, Dict[str, Any]]:
    """
    Get information about available parsers
    
    Returns:
        Dictionary with parser information
    """
    parsers = {
        'standard': {
            'name': 'Standard',
            'description': 'PyMuPDF + pdfplumber with OCR support',
            'available': True,
            'features': ['text_extraction', 'table_extraction', 'image_extraction', 'ocr']
        },
        'docling': {
            'name': 'Docling',
            'description': 'Advanced document understanding with layout analysis',
            'available': False,
            'features': ['layout_analysis', 'table_structure', 'figure_extraction', 'ocr']
        },
        'odl_batch': {
            'name': 'Open Data Loader',
            'description': 'Batch processing with parallel execution',
            'available': False,
            'features': ['batch_processing', 'parallel_execution', 'streaming']
        }
    }
    
    # Check availability
    try:
        import docling
        parsers['docling']['available'] = True
    except ImportError:
        pass
    
    try:
        import open_data_loader
        parsers['odl_batch']['available'] = True
    except ImportError:
        pass
    
    return parsers


# Backwards compatibility functions

def parse_pdf(
    file_path: str,
    extract_images: bool = True,
    extract_tables: bool = True,
    use_ocr: bool = False,
    ocr_engine = None
) -> Dict[str, Any]:
    """
    Backwards compatible PDF parsing function
    
    Args:
        file_path: Path to PDF file
        extract_images: Whether to extract images
        extract_tables: Whether to extract tables
        use_ocr: Whether to use OCR
        ocr_engine: OCR engine instance
        
    Returns:
        Dictionary with parsed content
    """
    parser = create_parser(
        extract_images=extract_images,
        extract_tables=extract_tables,
        use_ocr=use_ocr,
        ocr_engine=ocr_engine
    )
    return parser.parse_single(file_path)
