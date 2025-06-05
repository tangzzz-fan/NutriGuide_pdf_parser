"""
管理员 API 端点
提供系统监控、批量操作、数据导出等功能
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import io
import csv
import json
import zipfile
import uuid

from services.database import DatabaseService
from services.pdf_parser import PDFParserService
from utils.middleware import get_metrics_collector
from utils.logger import get_logger
from config.settings import get_settings
from celery_app import batch_parse_task, cleanup_old_files

logger = get_logger(__name__)
settings = get_settings()

# 创建路由器
admin_router = APIRouter(prefix="/admin", tags=["admin"])

# 依赖注入
db_service = DatabaseService()
pdf_service = PDFParserService()


@admin_router.get("/metrics")
async def get_system_metrics():
    """获取系统性能指标"""
    try:
        # 获取中间件指标
        metrics_collector = get_metrics_collector()
        api_metrics = metrics_collector.get_metrics() if metrics_collector else {}
        
        # 获取数据库统计
        db_stats = await db_service.get_parsing_stats(days=7)
        
        # 系统指标
        system_metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "api_metrics": api_metrics,
            "database_stats": db_stats,
            "service_status": {
                "database": await db_service.check_connection(),
                "pdf_parser": True,  # 简单检查
                "redis": True  # TODO: 实现Redis健康检查
            }
        }
        
        return system_metrics
        
    except Exception as e:
        logger.error(f"获取系统指标失败: {e}")
        raise HTTPException(status_code=500, detail="获取系统指标失败")


@admin_router.get("/stats")
async def get_parsing_statistics(
    days: int = Query(default=7, ge=1, le=365, description="统计天数")
):
    """获取解析统计信息"""
    try:
        stats = await db_service.get_parsing_stats(days=days)
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@admin_router.post("/batch/parse")
async def batch_parse_pdfs(
    files: List[UploadFile] = File(...),
    parsing_type: str = Query(default="auto", description="解析类型"),
    user_id: Optional[str] = Query(default=None, description="用户ID")
):
    """批量解析PDF文件"""
    if len(files) > 20:  # 限制批量大小
        raise HTTPException(status_code=400, detail="批量文件数量不能超过20个")
    
    try:
        batch_id = str(uuid.uuid4())
        files_info = []
        
        # 保存上传的文件
        for file in files:
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"文件 {file.filename} 不是PDF格式"
                )
            
            # 保存文件
            file_id = str(uuid.uuid4())
            file_path = f"temp/batch_{batch_id}_{file_id}.pdf"
            
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            files_info.append({
                "file_id": file_id,
                "filename": file.filename,
                "file_path": file_path,
                "size": len(content)
            })
        
        # 保存批量操作记录
        operation_id = await db_service.save_batch_operation(
            batch_id=batch_id,
            files_info=files_info,
            parsing_type=parsing_type,
            user_id=user_id
        )
        
        # 启动批量解析任务
        task = batch_parse_task.delay(batch_id, files_info, parsing_type)
        
        return {
            "batch_id": batch_id,
            "operation_id": operation_id,
            "task_id": task.id,
            "files_count": len(files),
            "status": "queued",
            "message": "批量解析任务已提交"
        }
        
    except Exception as e:
        logger.error(f"批量解析失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量解析失败: {str(e)}")


@admin_router.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """获取批量操作状态"""
    try:
        batch_info = await db_service.get_batch_operation(batch_id)
        
        if not batch_info:
            raise HTTPException(status_code=404, detail="批量操作不存在")
        
        return batch_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取批量状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取批量状态失败")


@admin_router.get("/export/results")
async def export_parsing_results(
    format: str = Query(default="json", regex="^(json|csv|xlsx)$"),
    days: int = Query(default=30, ge=1, le=365),
    status: Optional[str] = Query(default=None),
    parsing_type: Optional[str] = Query(default=None)
):
    """导出解析结果"""
    try:
        # 获取数据
        history = await db_service.get_parsing_history(
            limit=10000,  # 最大导出数量
            offset=0,
            status=status,
            parsing_type=parsing_type
        )
        
        results = history["results"]
        
        if format == "json":
            return export_as_json(results)
        elif format == "csv":
            return export_as_csv(results)
        elif format == "xlsx":
            return export_as_xlsx(results)
            
    except Exception as e:
        logger.error(f"导出结果失败: {e}")
        raise HTTPException(status_code=500, detail="导出结果失败")


def export_as_json(results: List[Dict[str, Any]]) -> StreamingResponse:
    """导出为JSON格式"""
    json_str = json.dumps(results, indent=2, ensure_ascii=False, default=str)
    
    return StreamingResponse(
        io.BytesIO(json_str.encode('utf-8')),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=parsing_results.json"}
    )


def export_as_csv(results: List[Dict[str, Any]]) -> StreamingResponse:
    """导出为CSV格式"""
    output = io.StringIO()
    
    if results:
        fieldnames = results[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in results:
            # 处理日期字段
            processed_row = {}
            for key, value in row.items():
                if isinstance(value, datetime):
                    processed_row[key] = value.isoformat()
                else:
                    processed_row[key] = str(value) if value is not None else ""
            writer.writerow(processed_row)
    
    content = output.getvalue().encode('utf-8')
    
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=parsing_results.csv"}
    )


def export_as_xlsx(results: List[Dict[str, Any]]) -> StreamingResponse:
    """导出为Excel格式"""
    try:
        import pandas as pd
        
        # 转换为DataFrame
        df = pd.DataFrame(results)
        
        # 处理日期列
        for col in df.columns:
            if df[col].dtype == 'object':
                # 尝试转换日期
                try:
                    df[col] = pd.to_datetime(df[col])
                except:
                    pass
        
        # 保存为Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='解析结果', index=False)
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=parsing_results.xlsx"}
        )
        
    except ImportError:
        raise HTTPException(status_code=500, detail="Excel导出功能不可用，请安装pandas和openpyxl")
    except Exception as e:
        logger.error(f"Excel导出失败: {e}")
        raise HTTPException(status_code=500, detail="Excel导出失败")


@admin_router.post("/cleanup")
async def trigger_cleanup(
    days: int = Query(default=30, ge=1, le=365, description="清理多少天前的记录")
):
    """触发数据清理"""
    try:
        # 启动清理任务
        task = cleanup_old_files.delay(days)
        
        return {
            "task_id": task.id,
            "message": f"数据清理任务已启动，将清理{days}天前的记录",
            "status": "queued"
        }
        
    except Exception as e:
        logger.error(f"启动清理任务失败: {e}")
        raise HTTPException(status_code=500, detail="启动清理任务失败")


@admin_router.get("/logs")
async def get_system_logs(
    level: str = Query(default="INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    lines: int = Query(default=100, ge=1, le=1000),
    search: Optional[str] = Query(default=None, description="搜索关键词")
):
    """获取系统日志"""
    try:
        # TODO: 实现日志读取逻辑
        # 这里应该从日志文件中读取最近的日志
        logs = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "这是一个示例日志条目",
                "module": "admin"
            }
        ]
        
        return {
            "logs": logs,
            "total": len(logs),
            "level": level,
            "lines": lines
        }
        
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        raise HTTPException(status_code=500, detail="获取日志失败")


@admin_router.get("/health/detailed")
async def detailed_health_check():
    """详细的健康检查"""
    try:
        health_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "services": {},
            "metrics": {},
            "version": "1.0.0"
        }
        
        # 检查数据库
        try:
            db_connected = await db_service.check_connection()
            health_info["services"]["database"] = {
                "status": "connected" if db_connected else "disconnected",
                "type": "MongoDB"
            }
        except Exception as e:
            health_info["services"]["database"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 检查PDF解析服务
        try:
            # 简单检查 - 可以尝试创建解析器实例
            pdf_service = PDFParserService()
            health_info["services"]["pdf_parser"] = {
                "status": "ready",
                "extractors": len(pdf_service.extractors)
            }
        except Exception as e:
            health_info["services"]["pdf_parser"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 检查文件系统
        import shutil
        disk_usage = shutil.disk_usage(".")
        health_info["metrics"]["disk"] = {
            "total": disk_usage.total,
            "used": disk_usage.used,
            "free": disk_usage.free,
            "usage_percent": (disk_usage.used / disk_usage.total) * 100
        }
        
        # 检查内存
        import psutil
        memory = psutil.virtual_memory()
        health_info["metrics"]["memory"] = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "usage_percent": memory.percent
        }
        
        # 根据各项检查结果确定总体状态
        services_status = [service.get("status") for service in health_info["services"].values()]
        if "error" in services_status:
            health_info["status"] = "unhealthy"
        elif "disconnected" in services_status:
            health_info["status"] = "degraded"
        
        return health_info
        
    except Exception as e:
        logger.error(f"详细健康检查失败: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e)
        }


@admin_router.get("/config")
async def get_system_config():
    """获取系统配置（脱敏）"""
    try:
        config = {
            "environment": settings.environment,
            "debug": settings.debug,
            "max_file_size": settings.max_file_size,
            "max_file_size_sync": settings.max_file_size_sync,
            "allowed_extensions": settings.allowed_extensions,
            "default_parsing_type": settings.default_parsing_type,
            "ocr_enabled": settings.ocr_enabled,
            "rate_limit_enabled": settings.rate_limit_enabled,
            "rate_limit_per_minute": settings.rate_limit_per_minute,
            "cache_enabled": settings.cache_enabled,
            "metrics_enabled": settings.metrics_enabled,
            "cleanup_enabled": settings.cleanup_enabled
        }
        
        return config
        
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取配置失败") 