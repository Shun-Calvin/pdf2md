from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np
from PIL import Image

@dataclass
class OCRResult:
    text: str
    confidence: float
    bbox: Optional[tuple] = None  # (x1, y1, x2, y2)
    
@dataclass
class PageResult:
    page_number: int
    text: str
    blocks: List[OCRResult]
    images: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    markdown: str = ""  # Added markdown field with default empty string
    has_images: bool = False
    has_tables: bool = False
    has_drawings: bool = False

class BaseOCREngine(ABC):
    """Base class for all OCR engines"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the OCR engine. Returns True if successful."""
        pass
    
    @abstractmethod
    def process_image(self, image: Image.Image) -> List[OCRResult]:
        """Process a single image and return OCR results."""
        pass
    
    @abstractmethod
    def process_pdf_page(self, image: Image.Image, page_number: int) -> PageResult:
        """Process a PDF page and return structured results."""
        pass
    
    def is_available(self) -> bool:
        """Check if the engine is available/installed."""
        try:
            return self.initialize()
        except Exception:
            return False
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return image
    
    def cleanup(self):
        """Cleanup resources."""
        self._initialized = False