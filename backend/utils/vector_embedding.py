import logging
from typing import List, Optional
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

class VectorEmbeddingService:
    """Service for generating vector embeddings from images using CLIP or similar models"""
    
    def __init__(self, model_name: str = "clip"):
        self.model_name = model_name
        self.model = None
        self.processor = None
        
    def initialize(self) -> bool:
        """Initialize the embedding model"""
        try:
            if self.model_name == "clip":
                try:
                    from transformers import CLIPProcessor, CLIPModel
                    self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                    self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
                    logger.info("CLIP model initialized successfully")
                    return True
                except ImportError:
                    logger.warning("transformers not installed, trying sentence-transformers")
                    try:
                        from sentence_transformers import SentenceTransformer
                        self.model = SentenceTransformer('clip-ViT-B-32')
                        logger.info("Sentence Transformer CLIP model initialized")
                        return True
                    except ImportError:
                        logger.error("No CLIP implementation available")
                        return False
            elif self.model_name == "openai":
                # OpenAI embeddings would require API key
                logger.info("OpenAI embeddings selected - will use API")
                return True
            else:
                logger.error(f"Unknown embedding model: {self.model_name}")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            return False
    
    def generate_image_embedding(self, image: Image.Image) -> Optional[List[float]]:
        """Generate embedding vector for an image"""
        if not self.model:
            if not self.initialize():
                return None
        
        try:
            if self.model_name == "clip":
                if hasattr(self.model, 'get_image_features'):
                    # transformers CLIP
                    inputs = self.processor(images=image, return_tensors="pt")
                    image_features = self.model.get_image_features(**inputs)
                    embedding = image_features.detach().numpy()[0].tolist()
                else:
                    # sentence-transformers
                    embedding = self.model.encode(image).tolist()
                
                return embedding
            else:
                logger.warning(f"Embedding generation not implemented for {self.model_name}")
                return None
        except Exception as e:
            logger.error(f"Error generating image embedding: {e}")
            return None
    
    def generate_text_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding vector for text"""
        if not self.model:
            if not self.initialize():
                return None
        
        try:
            if self.model_name == "clip":
                if hasattr(self.model, 'get_text_features'):
                    # transformers CLIP
                    inputs = self.processor(text=[text], return_tensors="pt")
                    text_features = self.model.get_text_features(**inputs)
                    embedding = text_features.detach().numpy()[0].tolist()
                else:
                    # sentence-transformers
                    embedding = self.model.encode(text).tolist()
                
                return embedding
            else:
                logger.warning(f"Embedding generation not implemented for {self.model_name}")
                return None
        except Exception as e:
            logger.error(f"Error generating text embedding: {e}")
            return None