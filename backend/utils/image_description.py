import base64
import io
import logging
import random
from typing import Optional, Dict, Any
from PIL import Image
import httpx
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

logger = logging.getLogger(__name__)

class ImageDescriptionService:
    """Service for generating image descriptions using OpenAI-compatible APIs"""
    
    def __init__(
        self,
        provider: str = "openai_compatible",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 120,
        rate_limit_delay: float = 0.0  # Delay between requests in seconds (0 = no delay)
    ):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model or "gpt-4-vision-preview"
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(timeout=timeout)
        
        # Rate limiting tracking
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_lock = asyncio.Lock()
        
    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL image to base64 string"""
        buffer = io.BytesIO()
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        image.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return img_str
    
    async def _rate_limit_wait(self):
        """Wait if needed to respect rate limits"""
        async with self._rate_limit_lock:
            import time
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self.rate_limit_delay:
                wait_time = self.rate_limit_delay - time_since_last
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s before next request")
                await asyncio.sleep(wait_time)
            
            self._last_request_time = time.time()
            self._request_count += 1
    
    async def describe_image(
        self,
        image: Image.Image,
        prompt: Optional[str] = None,
        max_tokens: int = 500
    ) -> str:
        """
        Generate a description for an image
        
        Args:
            image: PIL Image to describe
            prompt: Custom prompt for description
            max_tokens: Maximum tokens in response
            
        Returns:
            Description text
        """
        if not self.api_key:
            raise ValueError("API key is required for image description")
        
        # Default prompt
        if not prompt:
            prompt = "Describe this image in detail. Include what you see, any text, and the context."
        
        try:
            # Encode image
            base64_image = self._encode_image(image)
            
            logger.debug(f"Sending request to {self.provider} API with model {self.model}")
            
            # Apply rate limiting
            await self._rate_limit_wait()
            
            if self.provider == "openai":
                return await self._describe_with_openai(
                    base64_image, prompt, max_tokens
                )
            else:
                return await self._describe_with_openai_compatible(
                    base64_image, prompt, max_tokens
                )
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout error describing image: {e}")
            return f"[Image description unavailable: Request timed out after {self.timeout}s]"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error(f"Rate limit exceeded (429): {e}")
                return "[Image description unavailable: Rate limit exceeded. Please reduce concurrent requests or wait before retrying.]"
            else:
                logger.error(f"HTTP error describing image: {e}")
                return f"[Image description unavailable: HTTP {e.response.status_code} error]"
        except Exception as e:
            logger.error(f"Error describing image: {e}")
            logger.exception("Full traceback:")
            return f"[Image description unavailable: {str(e)}]"
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=60, jitter=2),
        retry=retry_if_exception_type((
            httpx.TimeoutException, 
            httpx.ReadTimeout, 
            httpx.ConnectTimeout,
            httpx.HTTPStatusError
        )),
        reraise=True
    )
    async def _describe_with_openai(
        self,
        base64_image: str,
        prompt: str,
        max_tokens: int
    ) -> str:
        """Describe image using OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            # Check for rate limit before raising
            if response.status_code == 429:
                retry_after = response.headers.get('retry-after', 'unknown')
                logger.warning(f"Rate limit hit (429). Retry-After: {retry_after}s")
                response.raise_for_status()
            
            response.raise_for_status()
            
            result = response.json()
            description = result["choices"][0]["message"]["content"]
            
            return description
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.error(f"Rate limit (429) encountered. Will retry with exponential backoff.")
            raise
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=60, jitter=2),
        retry=retry_if_exception_type((
            httpx.TimeoutException, 
            httpx.ReadTimeout, 
            httpx.ConnectTimeout,
            httpx.HTTPStatusError
        )),
        reraise=True
    )
    async def _describe_with_openai_compatible(
        self,
        base64_image: str,
        prompt: str,
        max_tokens: int
    ) -> str:
        """Describe image using OpenAI-compatible API (e.g., llava, local models)"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Different providers may have slightly different formats
        # This is a standard OpenAI-compatible format
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": max_tokens
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            # Check for rate limit before raising
            if response.status_code == 429:
                retry_after = response.headers.get('retry-after', 'unknown')
                logger.warning(f"Rate limit hit (429). Retry-After: {retry_after}s")
                # Re-raise to trigger retry
                response.raise_for_status()
            
            response.raise_for_status()
            
            result = response.json()
            
            # Debug logging to see actual response structure
            logger.debug(f"API Response structure: {list(result.keys()) if isinstance(result, dict) else type(result)}")
            
            # Safely extract description
            try:
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]
                    if "message" in choice and "content" in choice["message"]:
                        description = choice["message"]["content"]
                    elif "text" in choice:
                        description = choice["text"]
                    else:
                        logger.warning(f"Unexpected response structure: {choice}")
                        description = str(choice)
                else:
                    logger.warning(f"No choices in response: {result}")
                    description = str(result)
            except Exception as e:
                logger.error(f"Error parsing response: {e}. Response: {result}")
                description = f"[Error parsing response: {str(e)}]"
            
            return description
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Add extra logging for rate limit errors
                logger.error(f"Rate limit (429) encountered. Will retry with exponential backoff.")
            raise  # Re-raise to trigger tenacity retry
    
    async def describe_table(
        self,
        image: Image.Image,
        table_data: Optional[list] = None,
        max_tokens: int = 500
    ) -> str:
        """
        Generate a description for a table image
        
        Args:
            image: PIL Image of the table
            table_data: Optional structured table data
            max_tokens: Maximum tokens in response
            
        Returns:
            Description text
        """
        if table_data:
            prompt = f"""This is a table from a document. The table contains the following data:

{self._format_table_data(table_data)}

Please provide a brief description of what this table represents and any key insights."""
        else:
            prompt = "This is a table from a document. Please describe what this table shows, its structure, and any key information it contains."
        
        return await self.describe_image(image, prompt, max_tokens)
    
    def _format_table_data(self, table_data: list) -> str:
        """Format table data for prompt"""
        if not table_data:
            return "No structured data available"
        
        lines = []
        for row in table_data[:10]:  # Limit to first 10 rows
            lines.append(" | ".join(str(cell or "") for cell in row))
        
        if len(table_data) > 10:
            lines.append(f"... ({len(table_data) - 10} more rows)")
        
        return "\n".join(lines)
    
    async def batch_describe(
        self,
        images: list,
        prompts: Optional[list] = None,
        max_concurrent: int = 5
    ) -> list:
        """
        Describe multiple images in batch
        
        Args:
            images: List of PIL Images
            prompts: Optional list of prompts (one per image)
            max_concurrent: Maximum concurrent requests (default: 5 for good performance)
            
        Returns:
            List of descriptions
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        total = len(images)
        completed = 0
        failed = 0
        
        async def describe_with_limit(image, prompt, index):
            nonlocal completed, failed
            async with semaphore:
                logger.debug(f"Describing image {index + 1}/{total}")
                try:
                    result = await self.describe_image(image, prompt)
                    completed += 1
                    if completed % 10 == 0 or completed == total:
                        logger.info(f"Completed {completed}/{total} image descriptions ({failed} failed)")
                    return result
                except Exception as e:
                    logger.error(f"Error describing image {index + 1}/{total}: {e}")
                    completed += 1
                    failed += 1
                    return f"[Error: {str(e)}]"
        
        if prompts is None:
            prompts = [None] * len(images)
        
        logger.info(f"Starting batch description of {total} images with max {max_concurrent} concurrent")
        
        # Process all images concurrently with semaphore limit
        tasks = [
            describe_with_limit(img, prompt, i)
            for i, (img, prompt) in enumerate(zip(images, prompts))
        ]
        
        descriptions = await asyncio.gather(*tasks)
        
        logger.info(f"Completed batch description: {len(descriptions)} results ({failed} failed)")
        
        return descriptions
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()