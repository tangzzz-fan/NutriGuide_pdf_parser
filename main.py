from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from contextlib import asynccontextmanager
from typing import List
import uuid
from datetime import datetime

from config.settings import get_settings
from services.pdf_parser import PDFParserService
from services.database import DatabaseService
from services.task_manager import init_task_manager, get_task_manager
from models.response_models import (
    HealthResponse,
    ParseResponse,
    ProcessingStatus,
    ErrorResponse
)
from celery_app import parse_pdf_task, celery_app
from utils.logger import get_logger
from utils.validators import validate_upload_file, sanitize_filename
from utils.middleware import (
    RateLimitMiddleware, 
    MetricsMiddleware, 
    SecurityMiddleware, 
    RequestLoggingMiddleware,
    set_metrics_collector
)
from api.admin import admin_router
from api.tasks import router as tasks_router

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
        
        # Initialize task manager
        init_task_manager(celery_app)
        logger.info("Task manager initialized successfully")
        
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

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Add middleware in order (last added = first executed)
# 1. Request logging (outermost)
if settings.is_development:
    app.add_middleware(RequestLoggingMiddleware)

# 2. Security middleware
app.add_middleware(SecurityMiddleware)

# 3. Metrics collection
metrics_middleware = MetricsMiddleware(app)
app.add_middleware(MetricsMiddleware)
set_metrics_collector(metrics_middleware)

# 4. Rate limiting
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)

# 5. CORS (innermost, closest to app)
cors_config = settings.get_cors_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin_router)
app.include_router(tasks_router)

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
    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Check file size for sync processing
    if file.size and file.size > settings.max_file_size_sync:
        max_mb = settings.max_file_size_sync / (1024 * 1024)
        raise HTTPException(
            status_code=413, 
            detail=f"File too large for synchronous parsing ({max_mb}MB limit). Use async endpoint."
        )
    
    try:
        # Save uploaded file with validation
        file_id = str(uuid.uuid4())
        file_path = await _save_uploaded_file(file, file_id, validate=True)
        
        logger.info(f"Starting sync parsing for {file.filename}")
        
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
        if os.path.exists(file_path):
            os.remove(file_path)
        
        logger.info(f"Sync parsing completed for {file.filename}")
        
        return ParseResponse(
            document_id=document_id,
            status="completed",
            message="PDF parsed successfully",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Sync parsing failed for {file.filename}: {e}")
        # Clean up on error
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

@app.post("/parse/async")
async def parse_pdf_async(
    file: UploadFile = File(...),
    parsing_type: str = "auto",
    callback_url: str = None
):
    """
    Asynchronous PDF parsing - for large files using enhanced task management
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Check overall file size limit
    if file.size and file.size > settings.max_file_size:
        max_mb = settings.max_file_size / (1024 * 1024)
        raise HTTPException(
            status_code=413, 
            detail=f"File too large ({max_mb}MB limit)"
        )
    
    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        
        # Save uploaded file with validation
        file_path = await _save_uploaded_file(file, file_id, validate=True)
        
        # Save initial record to database and get the actual document_id
        document_id = await db_service.save_parsing_result(
            file_id=file_id,
            filename=file.filename,
            parsing_type=parsing_type,
            status="pending"
        )
        
        # Submit task through task manager
        task_manager = get_task_manager()
        task_id = await task_manager.submit_parsing_task(
            file_path=file_path,
            file_id=file_id,
            document_id=document_id,
            parsing_type=parsing_type,
            callback_url=callback_url
        )
        
        logger.info(f"Async parsing task submitted: {task_id} for {file.filename}")
        
        return {
            "task_id": task_id,
            "document_id": document_id,
            "file_id": file_id,
            "status": "pending",
            "message": "PDF parsing task submitted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit async parsing task for {file.filename}: {e}")
        # Clean up on error
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to submit parsing task: {str(e)}")

@app.post("/parse/batch")
async def parse_pdf_batch(
    files: List[UploadFile] = File(...),
    parsing_type: str = "auto"
):
    """
    Batch PDF parsing using enhanced task management
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > settings.max_batch_size:
        raise HTTPException(
            status_code=400, 
            detail=f"Too many files ({settings.max_batch_size} limit)"
        )
    
    try:
        batch_id = str(uuid.uuid4())
        files_info = []
        
        # Process and save all files
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                continue  # Skip non-PDF files
                
            file_id = str(uuid.uuid4())
            
            # Save file
            file_path = await _save_uploaded_file(file, file_id, validate=True)
            
            # Save to database and get actual document_id
            document_id = await db_service.save_parsing_result(
                file_id=file_id,
                filename=file.filename,
                parsing_type=parsing_type,
                status="pending"
            )
            
            files_info.append({
                "file_id": file_id,
                "document_id": document_id,
                "file_path": file_path,
                "filename": file.filename
            })
        
        if not files_info:
            raise HTTPException(status_code=400, detail="No valid PDF files found")
        
        # Submit batch task
        task_manager = get_task_manager()
        task_id = await task_manager.submit_batch_parsing_task(
            batch_id=batch_id,
            files_info=files_info,
            parsing_type=parsing_type
        )
        
        logger.info(f"Batch parsing task submitted: {task_id}, files: {len(files_info)}")
        
        return {
            "task_id": task_id,
            "batch_id": batch_id,
            "status": "pending",
            "file_count": len(files_info),
            "message": f"Batch parsing task submitted for {len(files_info)} files"
        }
        
    except Exception as e:
        logger.error(f"Failed to submit batch parsing task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit batch task: {str(e)}")

@app.get("/parse/status/{document_id}", response_model=ProcessingStatus)
async def get_parsing_status(document_id: str):
    """Get parsing status and results"""
    try:
        result = await db_service.get_parsing_result(document_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 确定状态和进度
        doc_status = result.get("status", "unknown")
        progress = 100 if doc_status == "completed" else (50 if doc_status == "processing" else 0)
        
        # 准备消息
        if result.get("error_message"):
            message = result.get("error_message")
        elif doc_status == "completed":
            message = "Processing completed"
        elif doc_status == "processing":
            message = "Processing in progress"
        else:
            message = "Processing pending"
        
        return ProcessingStatus(
            status=doc_status,  # 返回实际的文档状态
            message=message,
            document_id=document_id,
            progress=progress,
            data=result.get("result"),
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get status failed for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")

@app.get("/parse/result/{document_id}")
async def get_parsing_result(document_id: str):
    """Get detailed parsing result"""
    try:
        result = await db_service.get_parsing_result(document_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get result failed for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get result")

@app.get("/parse/result/{document_id}/download")
async def download_parsing_result(document_id: str):
    """Download parsing result as JSON file"""
    try:
        result = await db_service.get_parsing_result(document_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # 准备下载内容
        download_content = {
            "document_id": document_id,
            "filename": result.get("filename", "unknown"),
            "parsing_type": result.get("parsing_type", "unknown"),
            "status": result.get("status", "unknown"),
            "created_at": result.get("created_at").isoformat() if result.get("created_at") else None,
            "updated_at": result.get("updated_at").isoformat() if result.get("updated_at") else None,
            "quality_score": result.get("quality_score"),
            "processing_time": result.get("processing_time"),
            "result": result.get("result", {})
        }
        
        # 生成文件名
        safe_filename = sanitize_filename(result.get("filename", "result"))
        if safe_filename.endswith('.pdf'):
            safe_filename = safe_filename[:-4]  # 移除.pdf后缀
        json_filename = f"{safe_filename}_parsed.json"
        
        # 创建JSON响应
        import json
        json_content = json.dumps(download_content, indent=2, ensure_ascii=False, default=str)
        
        # 对文件名进行 URL 编码以支持中文
        import urllib.parse
        encoded_filename = urllib.parse.quote(json_filename.encode('utf-8'))

        return Response(
            content=json_content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download result")

@app.get("/parse/history")
async def get_parsing_history(
    limit: int = 10,
    offset: int = 0,
    status: str = None,
    parsing_type: str = None
):
    """Get parsing history"""
    try:
        history = await db_service.get_parsing_history(
            limit=limit,
            offset=offset,
            status=status,
            parsing_type=parsing_type
        )
        return history
        
    except Exception as e:
        logger.error(f"Get history failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get history")

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
        logger.error(f"Delete failed for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")

async def _save_uploaded_file(file: UploadFile, file_id: str, validate: bool = True) -> str:
    """Save uploaded file with optional validation"""
    try:
        # Sanitize filename
        safe_filename = sanitize_filename(file.filename)
        file_path = os.path.join(settings.upload_dir, f"{file_id}_{safe_filename}")
        
        # Read file content
        content = await file.read()
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Validate if requested
        if validate:
            is_valid, error, file_info = validate_upload_file(file_path, file.filename)
            if not is_valid:
                # Clean up invalid file
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise ValueError(f"File validation failed: {error}")
            
            logger.info(f"File validated successfully: {file_info}")
        
        return file_path
        
    except Exception as e:
        # Clean up on any error
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Web interface route
@app.get("/dashboard")
async def dashboard(request: Request):
    """Web dashboard interface"""
    return templates.TemplateResponse("index.html", {"request": request})

# Root endpoint - redirect to dashboard for web interface
@app.get("/")
async def root(request: Request):
    """Root endpoint - serve web dashboard or API info based on Accept header"""
    # Check if request is from a browser (HTML accepted)
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header:
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        # Return API information for API clients
        return {
            "service": "NutriGuide PDF Parser",
            "version": "1.0.0",
            "status": "running",
            "environment": settings.environment,
            "docs": "/docs",
            "admin": "/admin",
            "dashboard": "/dashboard",
            "timestamp": datetime.utcnow().isoformat()
        }

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    try:
        from utils.middleware import get_metrics_collector
        collector = get_metrics_collector()
        
        if collector:
            return collector.get_metrics()
        else:
            return {"error": "Metrics collection disabled"}
            
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    ) 