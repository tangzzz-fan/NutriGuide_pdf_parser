"""
Celery Application - 异步任务处理
配置Celery worker处理PDF解析任务
"""

import os
import asyncio
import time
from celery import Celery
from celery.signals import worker_ready, worker_shutting_down
from typing import Optional

from config.settings import get_settings
from utils.logger import get_logger, log_parsing_start, log_parsing_complete, log_parsing_error
from services.pdf_parser import PDFParserService
from services.database import DatabaseService

settings = get_settings()
logger = get_logger(__name__)

# 创建Celery应用
celery_app = Celery(
    "pdf_parser",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["celery_app"]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟超时
    task_soft_time_limit=25 * 60,  # 25分钟软超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    result_expires=3600,  # 结果保存1小时
)

# 全局服务实例
pdf_service: Optional[PDFParserService] = None
db_service: Optional[DatabaseService] = None


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Worker启动时初始化服务"""
    global pdf_service, db_service
    
    logger.info("Celery worker正在启动...")
    
    try:
        # 初始化PDF解析服务
        pdf_service = PDFParserService()
        logger.info("PDF解析服务初始化完成")
        
        # 初始化数据库服务
        db_service = DatabaseService()
        # 注意：在同步环境中不能直接调用异步方法
        # 数据库连接将在任务中建立
        logger.info("数据库服务初始化完成")
        
        logger.info("Celery worker启动成功")
        
    except Exception as e:
        logger.error(f"Celery worker启动失败: {e}")
        raise


@worker_shutting_down.connect
def worker_shutting_down_handler(sender=None, **kwargs):
    """Worker关闭时清理资源"""
    global db_service
    
    logger.info("Celery worker正在关闭...")
    
    try:
        if db_service:
            # 在异步环境中断开数据库连接
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(db_service.disconnect())
            loop.close()
            
        logger.info("Celery worker关闭完成")
        
    except Exception as e:
        logger.error(f"Celery worker关闭时出错: {e}")


@celery_app.task(bind=True, name="parse_pdf_task")
def parse_pdf_task(
    self,
    file_path: str,
    file_id: str,
    document_id: str,
    parsing_type: str = "auto",
    callback_url: Optional[str] = None
):
    """
    PDF解析异步任务
    
    Args:
        file_path: PDF文件路径
        file_id: 文件ID
        document_id: 文档ID
        parsing_type: 解析类型
        callback_url: 回调URL（可选）
    """
    global pdf_service, db_service
    
    start_time = time.time()
    filename = os.path.basename(file_path)
    
    # 记录任务开始
    log_parsing_start(file_id, filename, parsing_type)
    
    # 创建异步事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 更新任务状态为处理中
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 10,
                "total": 100,
                "status": "开始解析PDF文件..."
            }
        )
        
        # 异步执行解析和数据库操作
        result = loop.run_until_complete(
            _async_parse_and_save(
                self, file_path, file_id, document_id, 
                parsing_type, callback_url, start_time
            )
        )
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        duration = time.time() - start_time
        
        # 记录错误
        log_parsing_error(file_id, error_msg, duration)
        
        # 更新数据库状态
        try:
            loop.run_until_complete(
                _update_database_error(document_id, error_msg)
            )
        except Exception as db_error:
            logger.error(f"更新数据库错误状态失败: {db_error}")
        
        # 更新任务状态
        self.update_state(
            state="FAILURE",
            meta={
                "current": 100,
                "total": 100,
                "status": f"解析失败: {error_msg}",
                "error": error_msg
            }
        )
        
        raise
        
    finally:
        # 清理临时文件
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"临时文件已删除: {file_path}")
        except Exception as e:
            logger.warning(f"删除临时文件失败: {e}")
        
        # 关闭事件循环
        loop.close()


async def _async_parse_and_save(
    task,
    file_path: str,
    file_id: str,
    document_id: str,
    parsing_type: str,
    callback_url: Optional[str],
    start_time: float
) -> dict:
    """异步解析和保存逻辑"""
    global pdf_service, db_service
    
    filename = os.path.basename(file_path)
    
    # 确保数据库连接
    if not db_service.client:
        await db_service.connect()
    
    try:
        # 更新进度：开始解析
        task.update_state(
            state="PROGRESS",
            meta={
                "current": 20,
                "total": 100,
                "status": "正在提取PDF内容..."
            }
        )
        
        await db_service.update_parsing_status(
            document_id=document_id,
            status="processing",
            progress=20,
            message="正在提取PDF内容..."
        )
        
        # 执行PDF解析
        parse_result = await pdf_service.parse_pdf(file_path, parsing_type)
        
        # 更新进度：解析完成
        task.update_state(
            state="PROGRESS",
            meta={
                "current": 80,
                "total": 100,
                "status": "正在保存解析结果..."
            }
        )
        
        # 保存解析结果到数据库
        await db_service.update_parsing_status(
            document_id=document_id,
            status="completed",
            progress=100,
            result=parse_result,
            message="解析完成"
        )
        
        # 计算执行时间
        duration = time.time() - start_time
        quality_score = parse_result.get("quality_score", 0)
        
        # 记录解析完成
        log_parsing_complete(file_id, quality_score, duration)
        
        # 发送回调（如果有）
        if callback_url:
            await _send_callback(callback_url, document_id, parse_result)
        
        # 更新最终任务状态
        task.update_state(
            state="SUCCESS",
            meta={
                "current": 100,
                "total": 100,
                "status": "解析完成",
                "result": parse_result,
                "duration": duration
            }
        )
        
        return {
            "status": "completed",
            "document_id": document_id,
            "file_id": file_id,
            "filename": filename,
            "parsing_type": parsing_type,
            "quality_score": quality_score,
            "duration": duration,
            "result": parse_result
        }
        
    except Exception as e:
        # 确保错误也被正确处理
        duration = time.time() - start_time
        await db_service.update_parsing_status(
            document_id=document_id,
            status="failed",
            progress=100,
            message=f"解析失败: {str(e)}"
        )
        raise


async def _update_database_error(document_id: str, error_msg: str):
    """更新数据库错误状态"""
    global db_service
    
    if not db_service:
        return
    
    if not db_service.client:
        await db_service.connect()
    
    await db_service.update_parsing_status(
        document_id=document_id,
        status="failed",
        progress=100,
        message=f"解析失败: {error_msg}"
    )


async def _send_callback(callback_url: str, document_id: str, result: dict):
    """发送回调通知"""
    try:
        import httpx
        
        callback_data = {
            "document_id": document_id,
            "status": "completed",
            "result": result
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=callback_data,
                timeout=10.0
            )
            
            if response.status_code == 200:
                logger.info(f"回调发送成功: {callback_url}")
            else:
                logger.warning(f"回调发送失败: {callback_url}, 状态码: {response.status_code}")
                
    except Exception as e:
        logger.error(f"发送回调失败: {e}")


@celery_app.task(name="batch_parse_task")
def batch_parse_task(batch_id: str, files_info: list, parsing_type: str = "auto"):
    """
    批量解析任务
    
    Args:
        batch_id: 批次ID
        files_info: 文件信息列表
        parsing_type: 解析类型
    """
    logger.info(f"开始批量解析任务: {batch_id}, 文件数量: {len(files_info)}")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            _async_batch_parse(batch_id, files_info, parsing_type)
        )
        return result
        
    except Exception as e:
        logger.error(f"批量解析任务失败: {e}")
        raise
        
    finally:
        loop.close()


async def _async_batch_parse(batch_id: str, files_info: list, parsing_type: str):
    """异步批量解析逻辑"""
    global db_service
    
    # 确保数据库连接
    if not db_service.client:
        await db_service.connect()
    
    # 更新批次状态为处理中
    await db_service.update_batch_status(batch_id, "processing")
    
    completed_count = 0
    failed_count = 0
    
    # 逐个处理文件
    for file_info in files_info:
        try:
            file_id = file_info["file_id"]
            file_path = file_info["file_path"]
            
            # 创建解析记录
            document_id = await db_service.save_parsing_result(
                file_id=file_id,
                filename=file_info["filename"],
                parsing_type=parsing_type,
                status="processing"
            )
            
            # 解析文件
            result = await pdf_service.parse_pdf(file_path, parsing_type)
            
            # 保存结果
            await db_service.update_parsing_status(
                document_id=document_id,
                status="completed",
                result=result
            )
            
            completed_count += 1
            
        except Exception as e:
            logger.error(f"批量解析中单个文件失败: {file_info.get('filename', 'unknown')}, 错误: {e}")
            failed_count += 1
    
    # 更新批次最终状态
    total_files = len(files_info)
    success_rate = (completed_count / total_files) * 100 if total_files > 0 else 0
    
    final_status = "completed" if failed_count == 0 else "partial_failed" if completed_count > 0 else "failed"
    
    await db_service.update_batch_status(
        batch_id,
        final_status,
        completed_count=completed_count,
        failed_count=failed_count,
        success_rate=success_rate
    )
    
    logger.info(f"批量解析完成: {batch_id}, 成功: {completed_count}, 失败: {failed_count}")
    
    return {
        "batch_id": batch_id,
        "status": final_status,
        "total_files": total_files,
        "completed_count": completed_count,
        "failed_count": failed_count,
        "success_rate": success_rate
    }


@celery_app.task(name="cleanup_old_files")
def cleanup_old_files():
    """清理旧文件任务"""
    logger.info("开始清理旧文件...")
    
    try:
        import shutil
        from datetime import datetime, timedelta
        
        # 清理超过7天的上传文件
        uploads_dir = "uploads"
        if os.path.exists(uploads_dir):
            cutoff_time = datetime.now() - timedelta(days=7)
            
            for root, dirs, files in os.walk(uploads_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff_time:
                        try:
                            os.remove(file_path)
                            logger.info(f"已删除旧文件: {file_path}")
                        except Exception as e:
                            logger.warning(f"删除文件失败: {file_path}, 错误: {e}")
        
        # 清理旧日志文件（超过30天）
        logs_dir = "logs"
        if os.path.exists(logs_dir):
            cutoff_time = datetime.now() - timedelta(days=30)
            
            for file in os.listdir(logs_dir):
                if file.endswith('.log') or file.endswith('.log.gz'):
                    file_path = os.path.join(logs_dir, file)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < cutoff_time:
                        try:
                            os.remove(file_path)
                            logger.info(f"已删除旧日志: {file_path}")
                        except Exception as e:
                            logger.warning(f"删除日志失败: {file_path}, 错误: {e}")
        
        logger.info("旧文件清理完成")
        return {"status": "completed", "message": "旧文件清理完成"}
        
    except Exception as e:
        logger.error(f"清理旧文件失败: {e}")
        raise


# 导出Celery应用
__all__ = ["celery_app", "parse_pdf_task", "batch_parse_task", "cleanup_old_files"] 