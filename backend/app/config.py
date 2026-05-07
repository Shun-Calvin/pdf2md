from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "PDF2MD Converter"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Storage settings
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    TEMP_DIR: str = "temp"
    
    # Database
    DATABASE_URL: str = "sqlite:///./pdf2md.db"
    
    # Redis (for task queue)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # OCR Settings
    DEFAULT_OCR_ENGINE: str = "paddleocr_mobile"  # paddleocr_mobile, paddleocr_server, tesseract, cloud
    TESSERACT_CMD: Optional[str] = None
    PADDLEOCR_USE_GPU: bool = False
    
    # Cloud OCR Settings
    CLOUD_OCR_PROVIDER: Optional[str] = None  # aws, azure, google
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # Image Description Settings
    ENABLE_IMAGE_DESCRIPTION: bool = False
    IMAGE_DESCRIPTION_PROVIDER: str = "openai"  # openai, openai_compatible
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4-vision-preview"
    
    # OpenAI Compatible Settings
    OPENAI_COMPATIBLE_API_KEY: Optional[str] = None
    OPENAI_COMPATIBLE_BASE_URL: Optional[str] = None
    OPENAI_COMPATIBLE_MODEL: str = "llava"
    
    # Image Processing
    ENABLE_IMAGE_DEDUPLICATION: bool = False
    IMAGE_DEDUP_THRESHOLD: float = 0.9
    IMAGE_DEDUP_HASH_SIZE: int = 16
    
    # Processing
    MAX_WORKERS: int = 4
    BATCH_SIZE: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# Ensure directories exist
for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
    os.makedirs(directory, exist_ok=True)