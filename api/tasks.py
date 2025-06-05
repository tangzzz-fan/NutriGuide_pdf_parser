"""
Tasks API - 任务管理和监控API
提供任务状态查询、队列监控、任务控制等功能
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime

from services.task_manager import get_task_manager, TaskManager, TaskStatus, QueueStats
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
):
    """获取任务状态"""
    try:
        task_status = await task_manager.get_task_status(task_id)
        
        if not task_status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 转换为字典格式
        return {
            "task_id": task_status.task_id,
            "task_type": task_status.task_type,
            "status": task_status.status,
            "progress": task_status.progress,
            "message": task_status.message,
            "created_at": task_status.created_at.isoformat(),
            "updated_at": task_status.updated_at.isoformat(),
            "file_id": task_status.file_id,
            "filename": task_status.filename,
            "document_id": task_status.document_id,
            "parsing_type": task_status.parsing_type,
            "error": task_status.error,
            "result": task_status.result,
            "duration": task_status.duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务状态失败")


@router.post("/cancel/{task_id}")
async def cancel_task(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager)
):
    """取消任务"""
    try:
        success = await task_manager.cancel_task(task_id)
        
        if success:
            return {"message": "任务已取消", "task_id": task_id}
        else:
            raise HTTPException(status_code=400, detail="取消任务失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(status_code=500, detail="取消任务失败")


@router.get("/queue/stats", response_model=Dict[str, Any])
async def get_queue_stats(
    task_manager: TaskManager = Depends(get_task_manager)
):
    """获取队列统计信息"""
    try:
        stats = await task_manager.get_queue_stats()
        
        return {
            "pending_tasks": stats.pending_tasks,
            "processing_tasks": stats.processing_tasks,
            "completed_tasks": stats.completed_tasks,
            "failed_tasks": stats.failed_tasks,
            "total_tasks": stats.total_tasks,
            "average_processing_time": stats.average_processing_time,
            "queue_length": stats.queue_length,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取队列统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取队列统计失败")


@router.get("/recent", response_model=List[Dict[str, Any]])
async def get_recent_tasks(
    limit: int = Query(10, ge=1, le=100),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """获取最近的任务"""
    try:
        tasks = await task_manager.get_recent_tasks(limit)
        
        result = []
        for task in tasks:
            result.append({
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "file_id": task.file_id,
                "filename": task.filename,
                "document_id": task.document_id,
                "parsing_type": task.parsing_type,
                "error": task.error,
                "duration": task.duration
            })
        
        return result
        
    except Exception as e:
        logger.error(f"获取最近任务失败: {e}")
        raise HTTPException(status_code=500, detail="获取最近任务失败")


@router.get("/workers/status", response_model=Dict[str, Any])
async def get_worker_status(
    task_manager: TaskManager = Depends(get_task_manager)
):
    """获取Worker状态"""
    try:
        status = await task_manager.get_worker_status()
        return status
        
    except Exception as e:
        logger.error(f"获取Worker状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取Worker状态失败")


@router.post("/cleanup")
async def cleanup_old_tasks(
    days: int = Query(7, ge=1, le=365),
    task_manager: TaskManager = Depends(get_task_manager)
):
    """清理旧任务记录"""
    try:
        cleaned_count = await task_manager.cleanup_old_tasks(days)
        
        return {
            "message": f"已清理 {cleaned_count} 个旧任务记录",
            "cleaned_count": cleaned_count,
            "cutoff_days": days
        }
        
    except Exception as e:
        logger.error(f"清理旧任务失败: {e}")
        raise HTTPException(status_code=500, detail="清理旧任务失败")


@router.get("/monitor/realtime", response_model=Dict[str, Any])
async def get_realtime_monitor(
    task_manager: TaskManager = Depends(get_task_manager)
):
    """获取实时监控数据"""
    try:
        # 获取队列统计
        queue_stats = await task_manager.get_queue_stats()
        
        # 获取Worker状态
        worker_status = await task_manager.get_worker_status()
        
        # 获取最近任务
        recent_tasks = await task_manager.get_recent_tasks(5)
        
        # 计算成功率
        total_completed = queue_stats.completed_tasks + queue_stats.failed_tasks
        success_rate = (queue_stats.completed_tasks / total_completed * 100) if total_completed > 0 else 0
        
        return {
            "queue_stats": {
                "pending": queue_stats.pending_tasks,
                "processing": queue_stats.processing_tasks,
                "completed": queue_stats.completed_tasks,
                "failed": queue_stats.failed_tasks,
                "total": queue_stats.total_tasks,
                "queue_length": queue_stats.queue_length,
                "average_time": queue_stats.average_processing_time
            },
            "worker_status": {
                "total_workers": worker_status.get("total_workers", 0),
                "active_tasks": worker_status.get("total_active_tasks", 0),
                "workers": worker_status.get("workers", {})
            },
            "performance": {
                "success_rate": round(success_rate, 2),
                "average_processing_time": queue_stats.average_processing_time
            },
            "recent_tasks": [
                {
                    "task_id": task.task_id,
                    "status": task.status,
                    "filename": task.filename,
                    "created_at": task.created_at.isoformat(),
                    "duration": task.duration
                }
                for task in recent_tasks
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取实时监控数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取实时监控数据失败") 