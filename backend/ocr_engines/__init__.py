from typing import Dict, Any, Optional
from .base import BaseOCREngine
from .paddleocr_engine import PaddleOCREngine
from .tesseract_engine import TesseractEngine
from .cloud_engine import CloudOCREngine
import logging

logger = logging.getLogger(__name__)

class OCREngineFactory:
    """Factory for creating OCR engine instances"""
    
    _engines: Dict[str, BaseOCREngine] = {}
    
    @classmethod
    def get_engine(
        cls,
        engine_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseOCREngine:
        """
        Get or create an OCR engine instance
        
        Args:
            engine_type: Type of OCR engine
                        ('paddleocr_mobile', 'paddleocr_server', 'tesseract', 'cloud')
            config: Configuration dictionary for the engine
            
        Returns:
            BaseOCREngine instance
        """
        cache_key = f"{engine_type}_{hash(str(config))}"
        
        if cache_key not in cls._engines:
            engine = cls.create_engine(engine_type, config)
            cls._engines[cache_key] = engine
            
        return cls._engines[cache_key]
    
    @classmethod
    def create_engine(
        cls,
        engine_type: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseOCREngine:
        """Create a new OCR engine instance"""
        config = config or {}
        
        if engine_type == 'paddleocr_mobile':
            config['model_type'] = 'mobile'
            return PaddleOCREngine(config)
            
        elif engine_type == 'paddleocr_server':
            config['model_type'] = 'server'
            return PaddleOCREngine(config)
            
        elif engine_type == 'tesseract':
            return TesseractEngine(config)
            
        elif engine_type == 'cloud':
            return CloudOCREngine(config)
            
        elif engine_type == 'docling':
            # Docling OCR adapter
            from parsers.docling_parser import DoclingOCRAdapter
            return DoclingOCRAdapter(**config)
            
        else:
            raise ValueError(f"Unknown OCR engine type: {engine_type}")
    
    @classmethod
    def list_available_engines(cls) -> Dict[str, bool]:
        """List all available OCR engines and their availability"""
        engines = {
            'paddleocr_mobile': False,
            'paddleocr_server': False,
            'tesseract': False,
            'cloud': False,
            'docling': False,
        }
        
        # Test PaddleOCR
        try:
            import paddleocr
            engines['paddleocr_mobile'] = True
            engines['paddleocr_server'] = True
        except ImportError:
            pass
        
        # Test Tesseract
        try:
            import pytesseract
            engines['tesseract'] = True
        except ImportError:
            pass
        
        # Test Cloud OCRs
        try:
            import boto3
            engines['cloud'] = True
        except ImportError:
            pass
        
        # Test Docling
        try:
            import docling
            engines['docling'] = True
        except ImportError:
            pass
        
        return engines
    
    @classmethod
    def cleanup_all(cls):
        """Cleanup all cached engines"""
        for engine in cls._engines.values():
            try:
                engine.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up engine: {e}")
        cls._engines.clear()

__all__ = [
    'BaseOCREngine',
    'PaddleOCREngine',
    'TesseractEngine',
    'CloudOCREngine',
    'OCREngineFactory'
]