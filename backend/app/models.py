from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

Base = declarative_base()

class OCRStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class OCREngine(str, Enum):
    PADDLEOCR_MOBILE = "paddleocr_mobile"
    PADDLEOCR_SERVER = "paddleocr_server"
    TESSERACT = "tesseract"
    CLOUD = "cloud"
    NONE = "none"  # For searchable PDFs

class CloudOCRProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GOOGLE = "google"

class ProcessingOptions(BaseModel):
    use_ocr: bool = Field(default=True, description="Whether to use OCR")
    ocr_engine: OCREngine = Field(default=OCREngine.PADDLEOCR_MOBILE)
    cloud_ocr_provider: Optional[CloudOCRProvider] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = Field(default="us-east-1")
    extract_images: bool = Field(default=True)
    extract_tables: bool = Field(default=True)
    extract_drawings: bool = Field(default=True)
    deduplicate_images: bool = Field(default=False)
    describe_images: bool = Field(default=False)
    describe_tables: bool = Field(default=False)
    replace_text_with_description: bool = Field(default=False, description="Replace searchable text with image description to avoid duplication")
    image_description_provider: str = Field(default="openai_compatible")
    image_description_concurrent: int = Field(default=5, description="Number of concurrent requests for image description (1-20)")
    openai_compatible_api_key: Optional[str] = None
    openai_compatible_base_url: Optional[str] = None
    openai_compatible_model: Optional[str] = None
    enable_vector_embedding: bool = Field(default=False)
    vector_embedding_model: Optional[str] = Field(default="clip")
    image_description_prompt: Optional[str] = Field(default=None, description="Custom prompt for image description")
    
class PDFFile(Base):
    __tablename__ = "pdf_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    page_count = Column(Integer)
    status = Column(String(50), default=OCRStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)  # Track completion time
    processing_duration_seconds = Column(Float, nullable=True)  # Track processing duration
    current_page = Column(Integer, default=0)  # Track current processing page
    error_message = Column(Text)
    
    # Processing options
    use_ocr = Column(Boolean, default=True)
    ocr_engine = Column(String(50), default=OCREngine.PADDLEOCR_MOBILE)
    
    # Relationships
    pages = relationship("PDFPage", back_populates="pdf_file", cascade="all, delete-orphan")
    images = relationship("ExtractedImage", back_populates="pdf_file", cascade="all, delete-orphan")
    tables = relationship("ExtractedTable", back_populates="pdf_file", cascade="all, delete-orphan")
    output_files = relationship("OutputFile", back_populates="pdf_file", cascade="all, delete-orphan")

class PDFPage(Base):
    __tablename__ = "pdf_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_file_id = Column(Integer, ForeignKey("pdf_files.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    text_content = Column(Text)
    ocr_text = Column(Text)
    markdown_content = Column(Text)
    has_images = Column(Boolean, default=False)
    has_tables = Column(Boolean, default=False)
    has_drawings = Column(Boolean, default=False)
    
    pdf_file = relationship("PDFFile", back_populates="pages")

class ExtractedImage(Base):
    __tablename__ = "extracted_images"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_file_id = Column(Integer, ForeignKey("pdf_files.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String(500))
    image_hash = Column(String(64))
    is_duplicate = Column(Boolean, default=False)
    original_image_id = Column(Integer, ForeignKey("extracted_images.id"), nullable=True)
    description = Column(Text)
    width = Column(Integer)
    height = Column(Integer)
    image_type = Column(String(50))  # 'image', 'drawing', 'table_image'
    
    pdf_file = relationship("PDFFile", back_populates="images")
    original_image = relationship("ExtractedImage", remote_side=[id])

class ExtractedTable(Base):
    __tablename__ = "extracted_tables"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_file_id = Column(Integer, ForeignKey("pdf_files.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    table_data = Column(JSON)  # Structured table data
    markdown_content = Column(Text)
    description = Column(Text)
    
    pdf_file = relationship("PDFFile", back_populates="tables")

class OutputFile(Base):
    __tablename__ = "output_files"
    
    id = Column(Integer, primary_key=True, index=True)
    pdf_file_id = Column(Integer, ForeignKey("pdf_files.id"), nullable=False)
    output_type = Column(String(50))  # 'markdown', 'images_zip', 'json'
    file_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    pdf_file = relationship("PDFFile", back_populates="output_files")

# Database setup
from app.config import settings
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)