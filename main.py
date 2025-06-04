from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from contextlib import asynccontextmanager
from typing import List
import uuid
from datetime import datetime

from config.settings import get_settings
from services.pdf_parser import PDFParserService
from services.database import DatabaseService
from models.response_models import (
    HealthResponse,
    ParseResponse,
    ProcessingStatus,
    ErrorResponse
)
from celery_app import parse_pdf_task
from utils.logger import get_logger

# Initialize settings and logger
settings = get_settings()
logger = get_logger(__name__)

# Initialize services
pdf_service = PDFParserService()
db_service = DatabaseService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting PDF Parser Service...")
    try:
        await db_service.connect()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down PDF Parser Service...")
    try:
        await db_service.disconnect()
        logger.info("Database disconnected successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="NutriGuide PDF Parser Service",
    description="Microservice for parsing PDF documents to extract nutrition and recipe data",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [settings.backend_api_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = await db_service.check_connection()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            services={
                "database": "connected" if db_status else "disconnected",
                "redis": "connected",  # TODO: Implement Redis health check
                "pdf_parser": "ready"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/parse/sync", response_model=ParseResponse)
async def parse_pdf_sync(
    file: UploadFile = File(...),
    parsing_type: str = "auto"  # auto, food, recipe
):
    """
    Synchronous PDF parsing - for small files only
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    if file.size > 5 * 1024 * 1024:  # 5MB limit for sync parsing
        raise HTTPException(
            status_code=413, 
            detail="File too large for synchronous parsing. Use async endpoint."
        )
    
    try:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = await _save_uploaded_file(file, file_id)
        
        # Parse PDF synchronously
        result = await pdf_service.parse_pdf(file_path, parsing_type)
        
        # Save results to database
        document_id = await db_service.save_parsing_result(
            file_id=file_id,
            filename=file.filename,
            parsing_type=parsing_type,
            result=result,
            status="completed"
        )
        
        # Clean up temporary file
        os.remove(file_path)
        
        return ParseResponse(
            document_id=document_id,
            status="completed",
            message="PDF parsed successfully",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Sync parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

@app.post("/parse/async")
async def parse_pdf_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    parsing_type: str = "auto",
    callback_url: str = None
):
    """
    Asynchronous PDF parsing - for large files
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = await _save_uploaded_file(file, file_id)
        
        # Create database record with pending status
        document_id = await db_service.save_parsing_result(
            file_id=file_id,
            filename=file.filename,
            parsing_type=parsing_type,
            result=None,
            status="pending"
        )
        
        # Queue parsing task
        task = parse_pdf_task.delay(
            file_path=file_path,
            file_id=file_id,
            document_id=document_id,
            parsing_type=parsing_type,
            callback_url=callback_url
        )
        
        return JSONResponse(
            status_code=202,
            content={
                "document_id": document_id,
                "task_id": task.id,
                "status": "queued",
                "message": "PDF parsing queued for processing"
            }
        )
        
    except Exception as e:
        logger.error(f"Async parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue parsing: {str(e)}")

@app.get("/parse/status/{document_id}", response_model=ProcessingStatus)
async def get_parsing_status(document_id: str):
    """Get parsing status and results"""
    try:
        result = await db_service.get_parsing_result(document_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return ProcessingStatus(
            document_id=document_id,
            status=result.get("status", "unknown"),
            progress=result.get("progress", 0),
            message=result.get("message", ""),
            data=result.get("result"),
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get parsing status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve status")

@app.get("/parse/history")
async def get_parsing_history(
    limit: int = 10,
    offset: int = 0,
    status: str = None
):
    """Get parsing history"""
    try:
        history = await db_service.get_parsing_history(
            limit=limit,
            offset=offset,
            status_filter=status
        )
        
        return {
            "total": len(history),
            "items": history,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get parsing history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")

@app.delete("/parse/{document_id}")
async def delete_parsing_result(document_id: str):
    """Delete parsing result"""
    try:
        success = await db_service.delete_parsing_result(document_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")

# Helper functions
async def _save_uploaded_file(file: UploadFile, file_id: str) -> str:
    """Save uploaded file to disk"""
    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{file_id}_{file.filename}")
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    return file_path

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code,
            timestamp=datetime.utcnow()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            status_code=500,
            timestamp=datetime.utcnow()
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    ) 