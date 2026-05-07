from .base import BaseOCREngine, OCRResult, PageResult
from typing import List, Dict, Any, Optional
from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TesseractEngine(BaseOCREngine):
    """Tesseract OCR implementation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.tesseract_cmd = config.get('tesseract_cmd', None)
        self.lang = config.get('lang', 'eng')
        self.psm = config.get('psm', 6)  # Page segmentation mode
        self.oem = config.get('oem', 3)  # OCR Engine mode
        
    def initialize(self) -> bool:
        """Initialize Tesseract"""
        if self._initialized:
            return True
            
        try:
            import pytesseract
            
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            
            # Test if tesseract is available
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract version: {version}")
            
            self._initialized = True
            return True
            
        except ImportError as e:
            logger.error(f"pytesseract not installed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Tesseract: {e}")
            return False
    
    def process_image(self, image: Image.Image) -> List[OCRResult]:
        """Process image with Tesseract"""
        if not self._initialized:
            self.initialize()
        
        import pytesseract
        
        # Preprocess
        image = self.preprocess_image(image)
        
        # Get detailed data
        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            config=f'--psm {self.psm} --oem {self.oem}',
            output_type=pytesseract.Output.DICT
        )
        
        ocr_results = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 0:  # Valid confidence
                text = data['text'][i].strip()
                if text:
                    bbox = (
                        data['left'][i],
                        data['top'][i],
                        data['left'][i] + data['width'][i],
                        data['top'][i] + data['height'][i]
                    )
                    
                    ocr_results.append(OCRResult(
                        text=text,
                        confidence=float(data['conf'][i]) / 100.0,
                        bbox=bbox
                    ))
        
        return ocr_results
    
    def process_pdf_page(self, image: Image.Image, page_number: int) -> PageResult:
        """Process a PDF page"""
        import pytesseract
        
        # Preprocess
        image = self.preprocess_image(image)
        
        # Get text
        text = pytesseract.image_to_string(
            image,
            lang=self.lang,
            config=f'--psm {self.psm} --oem {self.oem}'
        )
        
        # Get detailed blocks
        blocks = self.process_image(image)
        
        # Tesseract doesn't extract images/tables natively
        images = []
        tables = []
        
        return PageResult(
            page_number=page_number,
            text=text,
            markdown=text,  # Set markdown to same as text for now
            blocks=blocks,
            images=images,
            tables=tables,
            has_images=len(images) > 0,
            has_tables=len(tables) > 0,
            has_drawings=False
        )
    
    def cleanup(self):
        """Cleanup Tesseract resources"""
        self._initialized = False