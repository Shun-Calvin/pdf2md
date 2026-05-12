"""
API endpoints for Docling and Open Data Loader integration.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging

from app.config import settings
from app.models import get_db, PDFFile, OCRStatus
from parsers import create_parser, ParserType, get_available_parsers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/parsers", tags=["parsers"])


@router.get("/available")
async def list_available_parsers():
    """List all available parsers and their capabilities"""
    return get_available_parsers()


@router.post("/parse/{file_id}")
async def parse_with_parser(
    file_id: int,
    parser_type: str = Query(..., description="Parser type: standard, docling, or odl_batch"),
    extract_images: bool = Query(True),
    extract_tables: bool = Query(True),
    use_ocr: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Parse a document using the specified parser.
    
    Args:
        file_id: Database ID of the file to parse
        parser_type: Type of parser to use (standard, docling, odl_batch)
        extract_images: Whether to extract images
        extract_tables: Whether to extract tables
        use_ocr: Whether to use OCR
    """
    # Get file from database
    pdf_file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not pdf_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Create parser
        parser = create_parser(
            parser_type=parser_type,
            extract_images=extract_images,
            extract_tables=extract_tables,
            use_ocr=use_ocr
        )
        
        # Parse the document
        result = parser.parse_single(
            pdf_file.file_path,
            file_id=str(file_id)
        )
        
        return {
            "success": result['success'],
            "file_id": file_id,
            "parser_type": parser_type,
            "elements_count": len(result['elements']),
            "markdown_length": len(result['markdown']),
            "processing_time": result['processing_time'],
            "error": result['error'],
            "metadata": result['metadata']
        }
        
    except Exception as e:
        logger.error(f"Error parsing file {file_id} with {parser_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.post("/parse-batch")
async def parse_batch(
    file_ids: List[int],
    parser_type: str = Query(..., description="Parser type: standard, docling, or odl_batch"),
    extract_images: bool = Query(True),
    extract_tables: bool = Query(True),
    use_ocr: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Parse multiple documents in batch using the specified parser.
    
    Args:
        file_ids: List of database IDs of files to parse
        parser_type: Type of parser to use (standard, docling, odl_batch)
        extract_images: Whether to extract images
        extract_tables: Whether to extract tables
        use_ocr: Whether to use OCR
    """
    # Get files from database
    pdf_files = db.query(PDFFile).filter(PDFFile.id.in_(file_ids)).all()
    if not pdf_files:
        raise HTTPException(status_code=404, detail="No files found")
    
    file_paths = [f.file_path for f in pdf_files]
    file_id_map = {f.file_path: str(f.id) for f in pdf_files}
    
    try:
        # Create parser
        parser = create_parser(
            parser_type=parser_type,
            extract_images=extract_images,
            extract_tables=extract_tables,
            use_ocr=use_ocr
        )
        
        # Track progress
        results = []
        
        def progress_callback(current, total, file_path, status):
            logger.info(f"Batch progress: {current}/{total} - {file_path} - {status}")
        
        # Parse batch
        if parser_type == "odl_batch":
            # Use batch processing
            batch_results = parser.parse_batch(
                file_paths,
                file_ids=[file_id_map[fp] for fp in file_paths]
            )
        else:
            # Process sequentially
            batch_results = []
            for fp in file_paths:
                result = parser.parse_single(fp, file_id_map[fp])
                batch_results.append(result)
        
        # Format results
        for result in batch_results:
            results.append({
                "file_id": result['file_id'],
                "success": result['success'],
                "elements_count": len(result['elements']),
                "markdown_length": len(result['markdown']),
                "processing_time": result['processing_time'],
                "error": result['error']
            })
        
        return {
            "success": True,
            "parser_type": parser_type,
            "total_files": len(file_ids),
            "processed_files": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch parsing with {parser_type}: {e}")
        raise HTTPException(status_code=500, detail=f"Batch parsing failed: {str(e)}")


@router.get("/settings")
async def get_parser_settings():
    """Get current parser configuration settings"""
    return {
        "docling": {
            "enabled": settings.USE_DOCLING,
            "ocr_engine": settings.DOCLING_OCR_ENGINE,
            "enable_table_detection": settings.DOCLING_ENABLE_TABLE_DETECTION,
            "enable_figure_detection": settings.DOCLING_ENABLE_FIGURE_DETECTION,
            "enable_layout_analysis": settings.DOCLING_ENABLE_LAYOUT_ANALYSIS
        },
        "open_data_loader": {
            "enabled": settings.USE_OPEN_DATA_LOADER,
            "batch_size": settings.ODL_BATCH_SIZE,
            "num_workers": settings.ODL_NUM_WORKERS,
            "enable_streaming": settings.ODL_ENABLE_STREAMING
        }
    }


@router.post("/reprocess/{file_id}")
async def reprocess_file(
    file_id: int,
    parser_type: Optional[str] = Query(None, description="Parser type (optional, uses default if not specified)"),
    extract_images: bool = Query(True),
    extract_tables: bool = Query(True),
    use_ocr: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Reprocess a file with different parser options.
    
    Args:
        file_id: Database ID of the file to reprocess
        parser_type: Optional parser type override
        extract_images: Whether to extract images
        extract_tables: Whether to extract tables
        use_ocr: Whether to use OCR
    """
    # Get file from database
    pdf_file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not pdf_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Update status to processing
    pdf_file.status = OCRStatus.PROCESSING
    db.commit()
    
    try:
        # Create parser
        parser = create_parser(
            parser_type=parser_type,
            extract_images=extract_images,
            extract_tables=extract_tables,
            use_ocr=use_ocr
        )
        
        # Parse the document
        result = parser.parse_single(
            pdf_file.file_path,
            file_id=str(file_id)
        )
        
        # Update status based on result
        if result['success']:
            pdf_file.status = OCRStatus.COMPLETED
        else:
            pdf_file.status = OCRStatus.FAILED
            pdf_file.error_message = result['error']
        
        db.commit()
        
        return {
            "success": result['success'],
            "file_id": file_id,
            "parser_type": parser.parser_type.value,
            "elements_count": len(result['elements']),
            "markdown_preview": result['markdown'][:500] if result['markdown'] else "",
            "error": result['error']
        }
        
    except Exception as e:
        pdf_file.status = OCRStatus.FAILED
        pdf_file.error_message = str(e)
        db.commit()
        
        logger.error(f"Error reprocessing file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Reprocessing failed: {str(e)}")


@router.get("/compare/{file_id}")
async def compare_parsers(
    file_id: int,
    parsers: List[str] = Query(..., description="List of parser types to compare"),
    db: Session = Depends(get_db)
):
    """
    Compare different parsers on the same document.
    
    Args:
        file_id: Database ID of the file to compare
        parsers: List of parser types to compare (e.g., ["standard", "docling"])
    """
    # Get file from database
    pdf_file = db.query(PDFFile).filter(PDFFile.id == file_id).first()
    if not pdf_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    comparison_results = []
    
    for parser_type in parsers:
        try:
            # Create parser
            parser = create_parser(parser_type=parser_type)
            
            # Parse the document
            start_time = __import__('time').time()
            result = parser.parse_single(pdf_file.file_path, file_id=str(file_id))
            end_time = __import__('time').time()
            
            comparison_results.append({
                "parser_type": parser_type,
                "success": result['success'],
                "elements_count": len(result['elements']),
                "markdown_length": len(result['markdown']),
                "processing_time": end_time - start_time,
                "error": result['error']
            })
            
        except Exception as e:
            comparison_results.append({
                "parser_type": parser_type,
                "success": False,
                "error": str(e)
            })
    
    return {
        "file_id": file_id,
        "filename": pdf_file.original_filename,
        "comparisons": comparison_results
    }


@router.post("/install-docling")
async def install_docling():
    """
    Install Docling package using pip.
    Returns installation progress and status.
    """
    import subprocess
    import sys
    import asyncio
    
    try:
        # Check if docling is already installed
        try:
            import docling
            return {
                "success": True,
                "message": "Docling is already installed",
                "version": getattr(docling, '__version__', 'unknown'),
                "already_installed": True
            }
        except ImportError:
            pass
        
        # Install docling using pip
        logger.info("Starting Docling installation...")
        
        # Run pip install in a subprocess
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "docling>=2.0.0",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.info("Docling installed successfully")
            
            # Try to import and get version
            try:
                # Force reload of modules
                import importlib
                import sys
                if 'docling' in sys.modules:
                    importlib.reload(sys.modules['docling'])
                else:
                    import docling
                
                version = getattr(docling, '__version__', 'unknown')
            except:
                version = 'unknown'
            
            return {
                "success": True,
                "message": "Docling installed successfully",
                "version": version,
                "already_installed": False,
                "output": stdout.decode() if stdout else None
            }
        else:
            error_msg = stderr.decode() if stderr else "Installation failed"
            logger.error(f"Docling installation failed: {error_msg}")
            return {
                "success": False,
                "message": f"Installation failed: {error_msg}",
                "error": error_msg
            }
            
    except Exception as e:
        logger.error(f"Error during Docling installation: {e}")
        return {
            "success": False,
            "message": f"Installation error: {str(e)}",
            "error": str(e)
        }


@router.get("/check-dependencies")
async def check_dependencies():
    """
    Check which optional dependencies are installed.
    """
    dependencies = {
        "docling": {
            "installed": False,
            "version": None,
            "install_command": "pip install docling>=2.0.0"
        },
        "open_data_loader": {
            "installed": False,
            "version": None,
            "install_command": "pip install open-dataset-loader>=0.1.0"
        }
    }
    
    # Check docling
    try:
        import docling
        dependencies["docling"]["installed"] = True
        dependencies["docling"]["version"] = getattr(docling, '__version__', 'unknown')
    except ImportError:
        pass
    
    # Check open_data_loader
    try:
        import open_data_loader
        dependencies["open_data_loader"]["installed"] = True
        dependencies["open_data_loader"]["version"] = getattr(open_data_loader, '__version__', 'unknown')
    except ImportError:
        pass
    
    return dependencies
