"""
Example usage of Docling and Open Data Loader integration.
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_docling():
    """Example: Basic document parsing with Docling"""
    print("\n=== Example 1: Basic Docling Parsing ===\n")
    
    from parsers.docling_parser import DoclingParser
    
    # Create parser
    parser = DoclingParser(
        enable_ocr=True,
        enable_table_detection=True,
        enable_figure_detection=True
    )
    
    # Parse a document
    pdf_path = "path/to/your/document.pdf"
    
    try:
        elements = parser.parse_document(
            pdf_path,
            extract_images=True,
            extract_tables=True
        )
        
        print(f"Extracted {len(elements)} elements:")
        for elem in elements[:5]:  # Show first 5
            print(f"  - {elem.element_type}: {elem.content[:100]}...")
        
        # Convert to markdown
        markdown = parser.convert_to_markdown(elements)
        print(f"\nMarkdown preview:\n{markdown[:500]}...")
        
    except Exception as e:
        print(f"Error: {e}")


def example_batch_processing():
    """Example: Batch processing with Open Data Loader"""
    print("\n=== Example 2: Batch Processing with ODL ===\n")
    
    from parsers.open_data_loader import BatchDocumentProcessor
    
    # Create batch processor
    processor = BatchDocumentProcessor(
        batch_size=4,
        num_workers=2,
        use_docling=True,  # Use Docling for parsing
        extract_images=True,
        extract_tables=True
    )
    
    # List of files to process
    file_paths = [
        "path/to/doc1.pdf",
        "path/to/doc2.pdf",
        "path/to/doc3.pdf",
    ]
    
    # Progress callback
    def on_progress(current, total, file_path, status):
        print(f"Progress: {current}/{total} - {Path(file_path).name} - {status}")
    
    # Process files
    try:
        results = []
        for result in processor.process_files(file_paths, on_progress):
            results.append(result)
            print(f"  ✓ {result.file_path}: {'Success' if result.success else 'Failed'}")
            
        print(f"\nProcessed {len(results)} files")
        
    except Exception as e:
        print(f"Error: {e}")


def example_unified_parser():
    """Example: Using the unified parser interface"""
    print("\n=== Example 3: Unified Parser Interface ===\n")
    
    from parsers import create_parser, ParserType
    
    # Create parser with different engines
    
    # Option 1: Standard parser (default)
    standard_parser = create_parser(parser_type=ParserType.STANDARD)
    
    # Option 2: Docling parser
    docling_parser = create_parser(
        parser_type=ParserType.DOCLING,
        extract_images=True,
        extract_tables=True
    )
    
    # Option 3: Open Data Loader with batch processing
    odl_parser = create_parser(
        parser_type=ParserType.ODL_BATCH,
        use_docling=True,
        extract_images=True,
        extract_tables=True
    )
    
    # Parse a single document
    pdf_path = "path/to/your/document.pdf"
    
    for name, parser in [
        ("Standard", standard_parser),
        ("Docling", docling_parser),
        ("ODL", odl_parser)
    ]:
        try:
            result = parser.parse_single(pdf_path)
            print(f"{name} Parser:")
            print(f"  Success: {result['success']}")
            print(f"  Elements: {len(result['elements'])}")
            print(f"  Markdown length: {len(result['markdown'])} chars")
            print(f"  Processing time: {result['processing_time']:.2f}s")
            print()
        except Exception as e:
            print(f"{name} Parser Error: {e}\n")


def example_streaming_processing():
    """Example: Streaming document processing"""
    print("\n=== Example 4: Streaming Processing ===\n")
    
    from parsers.open_data_loader import BatchDocumentProcessor, StreamingDocumentProcessor, ProcessingJob
    
    # Create processor
    processor = BatchDocumentProcessor(
        batch_size=1,
        num_workers=2,
        use_docling=True
    )
    
    # Create streaming processor
    streaming = StreamingDocumentProcessor(processor, max_queue_size=10)
    
    # Start the processor
    streaming.start()
    
    # Submit jobs
    files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    for i, file_path in enumerate(files):
        job = ProcessingJob(
            file_path=file_path,
            file_id=f"file_{i}",
            callback=lambda result: print(f"Completed: {result.file_path}")
        )
        if streaming.submit(job):
            print(f"Submitted: {file_path}")
        else:
            print(f"Queue full, skipping: {file_path}")
    
    # Collect results
    print("\nCollecting results...")
    for _ in range(len(files)):
        result = streaming.get_result(timeout=10.0)
        if result:
            print(f"  Result: {result.file_path} - {'Success' if result.success else 'Failed'}")
    
    # Stop the processor
    streaming.stop()


def example_available_parsers():
    """Example: Check available parsers"""
    print("\n=== Example 5: Available Parsers ===\n")
    
    from parsers import get_available_parsers
    
    parsers = get_available_parsers()
    
    for parser_type, info in parsers.items():
        status = "✓ Available" if info['available'] else "✗ Not installed"
        print(f"{info['name']} ({parser_type}): {status}")
        print(f"  Description: {info['description']}")
        print(f"  Features: {', '.join(info['features'])}")
        print()


def example_configuration():
    """Example: Configuration options"""
    print("\n=== Example 6: Configuration ===\n")
    
    # Environment variables to set in .env file:
    config_example = """
# Docling Configuration
USE_DOCLING=true
DOCLING_OCR_ENGINE=tesseract
DOCLING_ENABLE_TABLE_DETECTION=true
DOCLING_ENABLE_FIGURE_DETECTION=true
DOCLING_ENABLE_LAYOUT_ANALYSIS=true

# Open Data Loader Configuration
USE_OPEN_DATA_LOADER=true
ODL_BATCH_SIZE=4
ODL_NUM_WORKERS=2
ODL_ENABLE_STREAMING=false

# OCR Engine Selection (now includes 'docling')
DEFAULT_OCR_ENGINE=docling  # paddleocr_mobile, paddleocr_server, tesseract, cloud, docling
"""
    
    print("Configuration example (.env file):")
    print(config_example)
    
    # Programmatic configuration
    print("\nProgrammatic configuration:")
    
    from app.config import settings
    
    print(f"USE_DOCLING: {settings.USE_DOCLING}")
    print(f"DOCLING_OCR_ENGINE: {settings.DOCLING_OCR_ENGINE}")
    print(f"USE_OPEN_DATA_LOADER: {settings.USE_OPEN_DATA_LOADER}")
    print(f"ODL_BATCH_SIZE: {settings.ODL_BATCH_SIZE}")
    print(f"DEFAULT_OCR_ENGINE: {settings.DEFAULT_OCR_ENGINE}")


if __name__ == "__main__":
    print("=" * 60)
    print("Docling & Open Data Loader Integration Examples")
    print("=" * 60)
    
    # Run examples
    example_available_parsers()
    example_configuration()
    
    # Uncomment to run actual parsing examples (requires document files)
    # example_basic_docling()
    # example_batch_processing()
    # example_unified_parser()
    # example_streaming_processing()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
