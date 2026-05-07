from .base import BaseOCREngine, OCRResult, PageResult
from typing import List, Dict, Any, Optional
from PIL import Image
import numpy as np
import logging

logger = logging.getLogger(__name__)

class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR implementation supporting both mobile and server models"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.ocr = None
        self.model_type = config.get('model_type', 'mobile')  # 'mobile' or 'server'
        self.use_gpu = config.get('use_gpu', False)
        self.lang = config.get('lang', 'en')
        
    def initialize(self) -> bool:
        """Initialize PaddleOCR"""
        if self._initialized:
            return True
            
        try:
            from paddleocr import PaddleOCR
            
            # Configure based on model type
            # PaddleOCR 3.x uses text_detection_model_name and text_recognition_model_name
            if self.model_type == 'mobile':
                # Mobile models - faster, lighter
                self.ocr = PaddleOCR(
                    lang=self.lang,
                    text_detection_model_name='PP-OCRv5_mobile_det',
                    text_recognition_model_name='PP-OCRv5_mobile_rec',
                )
            else:
                # Server models - more accurate, slower
                self.ocr = PaddleOCR(
                    lang=self.lang,
                    text_detection_model_name='PP-OCRv5_server_det',
                    text_recognition_model_name='PP-OCRv5_server_rec',
                )
            
            self._initialized = True
            logger.info(f"PaddleOCR {self.model_type} initialized successfully")
            return True
            
        except ImportError as e:
            logger.error(f"PaddleOCR not installed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            return False
    
    def process_image(self, image: Image.Image) -> List[OCRResult]:
        """Process image with PaddleOCR"""
        if not self._initialized:
            self.initialize()
        
        if not self.ocr:
            raise RuntimeError("PaddleOCR not initialized")
        
        # Convert PIL to numpy array
        image_array = np.array(image)
        
        # Run OCR - PaddleOCR 3.x uses predict() instead of ocr()
        try:
            # Try the new API first
            result = self.ocr.predict(image_array)
            result_list = list(result) if result else []
        except Exception as e:
            # Fallback to ocr() method
            try:
                result = self.ocr.ocr(image_array)
                result_list = [result] if result else []
            except:
                result_list = []
        
        ocr_results = []
        if result_list:
            # Parse results - format varies by PaddleOCR version
            for item in result_list:
                if isinstance(item, list):
                    for line in item:
                        if line and len(line) >= 2:
                            bbox = line[0] if len(line) > 0 else None
                            text_info = line[1] if len(line) > 1 else None
                            
                            if text_info:
                                if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                                    text = str(text_info[0])
                                    confidence = float(text_info[1]) if isinstance(text_info[1], (int, float)) else 0.9
                                else:
                                    text = str(text_info)
                                    confidence = 0.9
                                
                                # Convert bbox
                                if bbox and len(bbox) >= 4:
                                    x_coords = [float(p[0]) if isinstance(p, (list, tuple)) else float(p) for p in bbox]
                                    y_coords = [float(p[1]) if isinstance(p, (list, tuple)) else float(p) for p in bbox]
                                    bbox_tuple = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                                else:
                                    bbox_tuple = None
                                
                                ocr_results.append(OCRResult(
                                    text=text,
                                    confidence=confidence,
                                    bbox=bbox_tuple
                                ))
        
        return ocr_results
    
    def process_pdf_page(self, image: Image.Image, page_number: int) -> PageResult:
        """Process a PDF page"""
        # Preprocess
        image = self.preprocess_image(image)
        
        # Extract text
        ocr_results = self.process_image(image)
        
        # Combine text
        full_text = "\n".join([r.text for r in ocr_results])
        
        # Extract images and tables (PaddleOCR doesn't do this natively)
        images = []
        tables = []
        
        return PageResult(
            page_number=page_number,
            text=full_text,
            markdown=full_text,  # Set markdown to same as text for now
            blocks=ocr_results,
            images=images,
            tables=tables,
            has_images=len(images) > 0,
            has_tables=len(tables) > 0,
            has_drawings=False
        )
    
    def cleanup(self):
        """Cleanup PaddleOCR resources"""
        if self.ocr:
            # PaddleOCR doesn't have explicit cleanup, but we can delete the object
            del self.ocr
            self.ocr = None
        self._initialized = False