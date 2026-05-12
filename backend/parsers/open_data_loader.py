"""
Open Data Loader integration for batch document processing.
Open Data Loader provides efficient data loading and preprocessing pipelines.

This module will work in fallback mode if open_data_loader is not installed.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from queue import Queue

logger = logging.getLogger(__name__)

# Try to import open_data_loader, set flag if not available
try:
    from open_data_loader import DataLoader, Dataset
    from open_data_loader.transforms import Compose, Transform
    ODL_AVAILABLE = True
except ImportError:
    ODL_AVAILABLE = False
    logger.warning("open_data_loader not installed. Using fallback batch processing.")


@dataclass
class ProcessingJob:
    """Represents a document processing job"""
    file_path: str
    file_id: Optional[str] = None
    options: Dict[str, Any] = None
    priority: int = 0
    callback: Optional[Callable] = None


@dataclass
class ProcessingResult:
    """Result of document processing"""
    file_path: str
    file_id: Optional[str]
    success: bool
    elements: List[Any]
    markdown: str
    processing_time: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class BatchDocumentProcessor:
    """
    Batch document processor using Open Data Loader for efficient processing.
    Supports parallel processing, caching, and progress tracking.
    
    Falls back to standard ThreadPoolExecutor if open_data_loader is not installed.
    """
    
    def __init__(
        self,
        batch_size: int = 4,
        num_workers: int = 2,
        use_docling: bool = False,
        extract_images: bool = True,
        extract_tables: bool = True,
        use_ocr: bool = False,
        ocr_engine = None,
        enable_cache: bool = False,
        cache_dir: Optional[str] = None
    ):
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.use_docling = use_docling
        self.extract_images = extract_images
        self.extract_tables = extract_tables
        self.use_ocr = use_ocr
        self.ocr_engine = ocr_engine
        self.enable_cache = enable_cache
        self.cache_dir = cache_dir
        
        self._progress_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        if not ODL_AVAILABLE:
            logger.info("BatchDocumentProcessor using fallback mode (ThreadPoolExecutor)")
        
    def register_progress_callback(self, callback: Callable):
        """Register a callback for progress updates"""
        self._progress_callbacks.append(callback)
        
    def _notify_progress(self, current: int, total: int, file_path: str, status: str):
        """Notify all registered progress callbacks"""
        for callback in self._progress_callbacks:
            try:
                callback(current, total, file_path, status)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    def process_files(
        self,
        file_paths: List[str],
        progress_callback: Optional[Callable] = None
    ) -> Iterator[ProcessingResult]:
        """
        Process multiple files
        
        Args:
            file_paths: List of file paths to process
            progress_callback: Optional callback for progress updates
            
        Yields:
            ProcessingResult objects
        """
        if progress_callback:
            self.register_progress_callback(progress_callback)
        
        if ODL_AVAILABLE:
            # Use Open Data Loader
            yield from self._process_with_odl(file_paths)
        else:
            # Use fallback ThreadPoolExecutor
            yield from self._process_with_fallback(file_paths)
    
    def _process_with_fallback(
        self,
        file_paths: List[str]
    ) -> Iterator[ProcessingResult]:
        """Fallback processing using ThreadPoolExecutor"""
        total_files = len(file_paths)
        processed_count = 0
        
        logger.info(f"Processing {total_files} files with {self.num_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(self._process_single_fallback, path, str(i)): path 
                for i, path in enumerate(file_paths)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    processed_count += 1
                    
                    self._notify_progress(
                        processed_count,
                        total_files,
                        path,
                        'completed' if result['success'] else 'failed'
                    )
                    
                    yield ProcessingResult(
                        file_path=result['file_path'],
                        file_id=result['file_id'],
                        success=result['success'],
                        elements=result['elements'],
                        markdown=result['markdown'],
                        processing_time=result['processing_time'],
                        error=result['error'],
                        metadata=result['metadata']
                    )
                    
                except Exception as e:
                    processed_count += 1
                    logger.error(f"Error processing {path}: {e}")
                    
                    self._notify_progress(
                        processed_count,
                        total_files,
                        path,
                        'failed'
                    )
                    
                    yield ProcessingResult(
                        file_path=path,
                        file_id=None,
                        success=False,
                        elements=[],
                        markdown='',
                        processing_time=0,
                        error=str(e),
                        metadata={}
                    )
    
    def _process_single_fallback(self, file_path: str, file_id: str) -> Dict[str, Any]:
        """Process a single file using fallback method"""
        start_time = time.time()
        
        try:
            if self.use_docling:
                # Use Docling parser
                from parsers.docling_parser import DoclingParser
                parser = DoclingParser(
                    enable_ocr=self.use_ocr,
                    enable_table_detection=self.extract_tables,
                    enable_figure_detection=self.extract_images
                )
                elements = parser.parse_document(
                    file_path,
                    extract_images=self.extract_images,
                    extract_tables=self.extract_tables
                )
                markdown = parser.convert_to_markdown(elements)
            else:
                # Use standard PDF processor
                from utils.pdf_processor import PDFProcessor
                
                processor = PDFProcessor()
                pages = processor.process_pdf(
                    file_path,
                    extract_images=self.extract_images,
                    extract_tables=self.extract_tables,
                    use_ocr=self.use_ocr,
                    ocr_engine=self.ocr_engine
                )
                
                # Combine pages into elements
                elements = []
                markdown_parts = []
                
                for page in pages:
                    elements.append({
                        'page_number': page.page_number,
                        'text': page.text,
                        'images': page.images,
                        'tables': page.tables
                    })
                    markdown_parts.append(page.markdown)
                
                markdown = "\n\n".join(markdown_parts)
            
            processing_time = time.time() - start_time
            
            return {
                'file_path': file_path,
                'file_id': file_id,
                'success': True,
                'elements': elements,
                'markdown': markdown,
                'processing_time': processing_time,
                'error': None,
                'metadata': {
                    'element_count': len(elements),
                    'char_count': len(markdown)
                }
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error processing {file_path}: {e}")
            
            return {
                'file_path': file_path,
                'file_id': file_id,
                'success': False,
                'elements': [],
                'markdown': '',
                'processing_time': processing_time,
                'error': str(e),
                'metadata': {}
            }
    
    def _process_with_odl(
        self,
        file_paths: List[str]
    ) -> Iterator[ProcessingResult]:
        """Process files using Open Data Loader (when available)"""
        if not ODL_AVAILABLE:
            return
        
        # This would contain the actual ODL implementation
        # For now, fall back to standard processing
        logger.info("Open Data Loader not fully implemented, using fallback")
        yield from self._process_with_fallback(file_paths)
    
    def process_single(
        self,
        file_path: str,
        file_id: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process a single file
        
        Args:
            file_path: Path to the file
            file_id: Optional file identifier
            
        Returns:
            ProcessingResult
        """
        result = self._process_single_fallback(file_path, file_id or "0")
        
        return ProcessingResult(
            file_path=result['file_path'],
            file_id=result['file_id'],
            success=result['success'],
            elements=result['elements'],
            markdown=result['markdown'],
            processing_time=result['processing_time'],
            error=result['error'],
            metadata=result['metadata']
        )


class StreamingDocumentProcessor:
    """
    Streaming document processor for real-time processing of large document sets.
    Uses Open Data Loader with streaming capabilities.
    """
    
    def __init__(
        self,
        processor: BatchDocumentProcessor,
        max_queue_size: int = 100
    ):
        self.processor = processor
        self.max_queue_size = max_queue_size
        self._job_queue: Queue = Queue(maxsize=max_queue_size)
        self._result_queue: Queue = Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def start(self):
        """Start the streaming processor"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._worker_loop)
            self._worker_thread.start()
            logger.info("Streaming document processor started")
    
    def stop(self):
        """Stop the streaming processor"""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        logger.info("Streaming document processor stopped")
    
    def submit(self, job: ProcessingJob) -> bool:
        """
        Submit a job for processing
        
        Args:
            job: ProcessingJob to process
            
        Returns:
            True if job was queued, False if queue is full
        """
        try:
            self._job_queue.put(job, block=False)
            return True
        except:
            return False
    
    def get_result(self, timeout: Optional[float] = None) -> Optional[ProcessingResult]:
        """
        Get a processed result
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            ProcessingResult or None if timeout
        """
        try:
            return self._result_queue.get(timeout=timeout)
        except:
            return None
    
    def _worker_loop(self):
        """Worker thread loop"""
        while not self._stop_event.is_set():
            try:
                # Get job from queue
                job = self._job_queue.get(timeout=1.0)
                
                # Process the job
                result = self.processor.process_single(
                    job.file_path,
                    job.file_id
                )
                
                # Call callback if provided
                if job.callback:
                    try:
                        job.callback(result)
                    except Exception as e:
                        logger.warning(f"Job callback error: {e}")
                
                # Put result in result queue
                self._result_queue.put(result)
                
            except Exception as e:
                if not isinstance(e, Exception):  # Not timeout
                    logger.error(f"Worker loop error: {e}")


# Convenience functions

def create_batch_processor(
    use_docling: bool = False,
    batch_size: int = 4,
    num_workers: int = 2,
    **kwargs
) -> BatchDocumentProcessor:
    """
    Create a batch document processor
    
    Args:
        use_docling: Whether to use Docling parser
        batch_size: Number of files per batch
        num_workers: Number of parallel workers
        **kwargs: Additional processor options
        
    Returns:
        BatchDocumentProcessor instance
    """
    return BatchDocumentProcessor(
        batch_size=batch_size,
        num_workers=num_workers,
        use_docling=use_docling,
        **kwargs
    )


def process_documents_parallel(
    file_paths: List[str],
    use_docling: bool = False,
    max_workers: int = 4,
    progress_callback: Optional[Callable] = None
) -> List[ProcessingResult]:
    """
    Process multiple documents in parallel
    
    Args:
        file_paths: List of file paths
        use_docling: Whether to use Docling parser
        max_workers: Maximum number of parallel workers
        progress_callback: Optional progress callback
        
    Returns:
        List of ProcessingResult
    """
    processor = create_batch_processor(
        use_docling=use_docling,
        num_workers=max_workers
    )
    
    results = []
    for result in processor.process_files(file_paths, progress_callback):
        results.append(result)
    
    return results
