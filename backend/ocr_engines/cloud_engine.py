from .base import BaseOCREngine, OCRResult, PageResult
from typing import List, Dict, Any, Optional
from PIL import Image
import io
import base64
import logging

logger = logging.getLogger(__name__)

class CloudOCREngine(BaseOCREngine):
    """Cloud OCR implementation supporting AWS Textract, Azure Form Recognizer, and Google Vision"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.provider = config.get('provider', 'aws')
        self.client = None
        
        # AWS credentials
        self.aws_access_key = config.get('aws_access_key_id')
        self.aws_secret_key = config.get('aws_secret_access_key')
        self.aws_region = config.get('aws_region', 'us-east-1')
        
        # Azure credentials
        self.azure_endpoint = config.get('azure_endpoint')
        self.azure_key = config.get('azure_key')
        
        # Google credentials
        self.google_credentials_path = config.get('google_credentials_path')
        
    def initialize(self) -> bool:
        """Initialize Cloud OCR client"""
        if self._initialized:
            return True
        
        try:
            if self.provider == 'aws':
                import boto3
                self.client = boto3.client(
                    'textract',
                    aws_access_key_id=self.aws_access_key,
                    aws_secret_access_key=self.aws_secret_key,
                    region_name=self.aws_region
                )
                
            elif self.provider == 'azure':
                from azure.ai.formrecognizer import DocumentAnalysisClient
                from azure.core.credentials import AzureKeyCredential
                
                self.client = DocumentAnalysisClient(
                    endpoint=self.azure_endpoint,
                    credential=AzureKeyCredential(self.azure_key)
                )
                
            elif self.provider == 'google':
                from google.cloud import vision
                self.client = vision.ImageAnnotatorClient()
                
            else:
                logger.error(f"Unknown cloud provider: {self.provider}")
                return False
            
            self._initialized = True
            logger.info(f"Cloud OCR ({self.provider}) initialized successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Cloud SDK not installed for {self.provider}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Cloud OCR: {e}")
            return False
    
    def _image_to_bytes(self, image: Image.Image) -> bytes:
        """Convert PIL image to bytes"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def process_image(self, image: Image.Image) -> List[OCRResult]:
        """Process image with Cloud OCR"""
        if not self._initialized:
            self.initialize()
        
        image_bytes = self._image_to_bytes(image)
        
        if self.provider == 'aws':
            return self._process_aws(image_bytes)
        elif self.provider == 'azure':
            return self._process_azure(image_bytes)
        elif self.provider == 'google':
            return self._process_google(image_bytes)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def _process_aws(self, image_bytes: bytes) -> List[OCRResult]:
        """Process with AWS Textract"""
        import boto3
        
        response = self.client.detect_document_text(
            Document={'Bytes': image_bytes}
        )
        
        ocr_results = []
        blocks = response.get('Blocks', [])
        
        for block in blocks:
            if block['BlockType'] == 'LINE':
                bbox = block.get('Geometry', {}).get('BoundingBox', {})
                if bbox:
                    # Convert relative coordinates to absolute
                    width, height = 1000, 1000  # Placeholder
                    bbox_tuple = (
                        int(bbox['Left'] * width),
                        int(bbox['Top'] * height),
                        int((bbox['Left'] + bbox['Width']) * width),
                        int((bbox['Top'] + bbox['Height']) * height)
                    )
                else:
                    bbox_tuple = None
                
                ocr_results.append(OCRResult(
                    text=block.get('Text', ''),
                    confidence=block.get('Confidence', 0) / 100.0,
                    bbox=bbox_tuple
                ))
        
        return ocr_results
    
    def _process_azure(self, image_bytes: bytes) -> List[OCRResult]:
        """Process with Azure Form Recognizer"""
        from azure.ai.formrecognizer import DocumentAnalysisClient
        
        poller = self.client.begin_analyze_document(
            "prebuilt-read",
            document=image_bytes
        )
        result = poller.result()
        
        ocr_results = []
        for page in result.pages:
            for line in page.lines:
                # Get bounding box
                bbox_points = line.bounding_box
                if bbox_points:
                    x_coords = [p.x for p in bbox_points]
                    y_coords = [p.y for p in bbox_points]
                    bbox_tuple = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                else:
                    bbox_tuple = None
                
                ocr_results.append(OCRResult(
                    text=line.content,
                    confidence=getattr(line, 'confidence', 0.9),
                    bbox=bbox_tuple
                ))
        
        return ocr_results
    
    def _process_google(self, image_bytes: bytes) -> List[OCRResult]:
        """Process with Google Vision"""
        from google.cloud import vision
        
        image = vision.Image(content=image_bytes)
        response = self.client.document_text_detection(image=image)
        
        ocr_results = []
        document = response.full_text_annotation
        
        for page in document.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    para_text = ""
                    for word in paragraph.words:
                        word_text = "".join([symbol.text for symbol in word.symbols])
                        para_text += word_text + " "
                    
                    # Get bounding box
                    vertices = paragraph.bounding_box.vertices
                    bbox_tuple = (
                        vertices[0].x, vertices[0].y,
                        vertices[2].x, vertices[2].y
                    )
                    
                    ocr_results.append(OCRResult(
                        text=para_text.strip(),
                        confidence=block.confidence,
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
        
        # Cloud OCR may provide table detection
        tables = []
        images = []
        
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
        """Cleanup Cloud OCR resources"""
        self.client = None
        self._initialized = False