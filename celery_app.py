"""
Celery Application - 异步任务处理
配置Celery worker处理PDF解析任务
"""

import os
import asyncio
import time
import traceback
from celery import Celery
from celery.signals import worker_ready, worker_shutting_down
from celery.exceptions import Ignore
from typing import Optional, Dict, Any
import json

from config.settings import get_settings
from utils.logger import get_logger, log_parsing_start, log_parsing_complete, log_parsing_error
from services.pdf_parser import PDFParserService
from services.database import DatabaseService

# 确保 Celery worker 有正确的环境变量
if not os.getenv('MONGODB_URL'):
    os.environ['MONGODB_URL'] = "mongodb://admin:admin123@localhost:27017/nutriguide_dev?authSource=admin"
if not os.getenv('MONGODB_DATABASE'):
    os.environ['MONGODB_DATABASE'] = "nutriguide_dev"

settings = get_settings()
logger = get_logger(__name__)

# 创建Celery应用
celery_app = Celery(
    "pdf_parser",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["celery_app"]
)

# Celery配置
celery_app.conf.update(
    # 序列化配置 - 关键修复点
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区配置
    timezone="UTC",
    enable_utc=True,
    
    # 任务跟踪和结果配置 - 关键修复点
    task_track_started=True,
    task_ignore_result=False,  # 重新启用结果存储
    task_store_eager_result=True,  # 启用即时结果存储
    result_expires=3600,  # 结果保存1小时
    
    # 超时配置
    task_time_limit=30 * 60,  # 30分钟超时
    task_soft_time_limit=25 * 60,  # 25分钟软超时
    
    # Worker配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    
    # 结果后端配置 - 关键修复点
    result_backend_transport_options={
        'retry_policy': {
            'timeout': 5.0
        }
    },
    
    # 添加队列和路由配置
    task_default_queue="pdf_parsing",
    task_routes={
        "parse_pdf_task_v2": {"queue": "pdf_parsing"},
        "batch_parse_task_v2": {"queue": "batch_processing"},
        "cleanup_old_files": {"queue": "maintenance"}
    },
    
    # 错误处理配置 - 关键修复点
    task_annotations={
        '*': {
            'rate_limit': '10/s',
            'time_limit': 1800,
            'soft_time_limit': 1500,
        }
    },
    
    # 避免复杂对象序列化问题
    task_always_eager=False,
    result_accept_content=['json'],
    result_compression='gzip',
)

# 全局服务实例
pdf_service: Optional[PDFParserService] = None
db_service: Optional[DatabaseService] = None


def ensure_services_initialized():
    """确保服务已初始化"""
    global pdf_service, db_service

    if pdf_service is None:
        try:
            pdf_service = PDFParserService()
            logger.info("PDF解析服务初始化完成")
        except Exception as e:
            logger.error(f"PDF解析服务初始化失败: {e}")
            raise

    if db_service is None:
        try:
            db_service = DatabaseService()
            logger.info("数据库服务初始化完成")
        except Exception as e:
            logger.error(f"数据库服务初始化失败: {e}")
            raise


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Worker启动时初始化服务"""
    logger.info("Celery worker正在启动...")

    try:
        ensure_services_initialized()
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


@celery_app.task(bind=True, name="parse_pdf_task_v2")
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

    # 确保服务已初始化
    try:
        ensure_services_initialized()
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        return {
            "status": "failed",
            "document_id": document_id,
            "file_id": file_id,
            "filename": filename,
            "error": {
                "type": "ServiceInitializationError",
                "message": f"服务初始化失败: {str(e)}"
            },
            "duration": time.time() - start_time
        }

    # 记录任务开始
    log_parsing_start(file_id, filename, parsing_type)

    # 创建异步事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 记录任务开始（不更新状态以避免序列化问题）
        logger.info(f"开始解析PDF文件: {filename}")
        
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
        error_type = type(e).__name__
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
        
        # 记录错误信息（不更新状态以避免序列化问题）
        logger.error(f"任务执行失败: {error_type}: {error_msg}")
        
        # 直接返回错误结果而不是抛出异常
        return {
            "status": "failed",
            "document_id": document_id,
            "file_id": file_id,
            "filename": filename,
            "error": {
                "type": error_type,
                "message": error_msg
            },
            "duration": duration
        }
        
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

    # 确保服务实例存在并已连接
    if pdf_service is None:
        logger.warning("PDF解析服务未初始化，正在重新创建...")
        pdf_service = PDFParserService()

    if db_service is None:
        logger.warning("数据库服务未初始化，正在重新创建...")
        db_service = DatabaseService()

    if not hasattr(db_service, 'client') or db_service.client is None:
        logger.info("数据库连接不存在，正在建立连接...")
        await db_service.connect()

    # 验证数据库连接
    if not await db_service.check_connection():
        logger.warning("数据库连接失效，正在重新连接...")
        await db_service.connect()

    try:
        # 记录进度（不更新状态）
        logger.info("正在提取PDF内容...")
        
        await db_service.update_parsing_status(
            document_id=document_id,
            status="processing",
            progress=20,
            message="正在提取PDF内容..."
        )
        
        # 执行PDF解析
        parse_result = await pdf_service.parse_pdf(file_path, parsing_type)
        
        # 记录进度（不更新状态）
        logger.info("正在保存解析结果...")
        
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
        
        # 记录任务完成（不更新状态）
        logger.info(f"解析完成，耗时: {duration:.2f}秒")
        
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
        error_msg = str(e)
        error_type = type(e).__name__
        
        await db_service.update_parsing_status(
            document_id=document_id,
            status="failed",
            progress=100,
            message=f"解析失败: {error_msg}"
        )
        
        # 记录详细错误信息
        logger.error(f"解析任务失败: {error_type}: {error_msg}")
        
        # 重新抛出异常，让上层处理
        raise


async def _update_database_error(document_id: str, error_msg: str):
    """更新数据库错误状态"""
    global db_service

    if db_service is None:
        logger.warning("数据库服务未初始化，无法更新错误状态")
        return

    try:
        if not hasattr(db_service, 'client') or db_service.client is None:
            logger.info("数据库连接不存在，正在建立连接...")
            await db_service.connect()

        # 验证数据库连接
        if not await db_service.check_connection():
            logger.warning("数据库连接失效，正在重新连接...")
            await db_service.connect()
    except Exception as e:
        logger.error(f"建立数据库连接失败: {e}")
        return
    
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


@celery_app.task(name="batch_parse_task_v2")
def batch_parse_task(batch_id: str, files_info: list, parsing_type: str = "auto"):
    """
    批量解析任务

    Args:
        batch_id: 批次ID
        files_info: 文件信息列表
        parsing_type: 解析类型
    """
    logger.info(f"开始批量解析任务: {batch_id}, 文件数量: {len(files_info)}")

    # 确保服务已初始化
    try:
        ensure_services_initialized()
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        return {
            "status": "failed",
            "batch_id": batch_id,
            "error": {
                "type": "ServiceInitializationError",
                "message": f"服务初始化失败: {str(e)}"
            }
        }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            _async_batch_parse(batch_id, files_info, parsing_type)
        )
        return result
        
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        logger.error(f"批量解析任务失败: {error_type}: {error_msg}")
        
        # 返回错误结果而不是抛出异常
        return {
            "status": "failed",
            "batch_id": batch_id,
            "error": {
                "type": error_type,
                "message": error_msg
            }
        }
        
    finally:
        loop.close()


async def _async_batch_parse(batch_id: str, files_info: list, parsing_type: str):
    """异步批量解析逻辑"""
    global db_service, pdf_service

    # 确保服务实例存在并已连接
    if db_service is None:
        logger.warning("数据库服务未初始化，正在重新创建...")
        db_service = DatabaseService()

    if pdf_service is None:
        logger.warning("PDF解析服务未初始化，正在重新创建...")
        pdf_service = PDFParserService()

    if not hasattr(db_service, 'client') or db_service.client is None:
        logger.info("数据库连接不存在，正在建立连接...")
        await db_service.connect()

    # 验证数据库连接
    if not await db_service.check_connection():
        logger.warning("数据库连接失效，正在重新连接...")
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


def safe_serialize_exception(exc: Exception) -> Dict[str, Any]:
    """安全地序列化异常信息"""
    try:
        return {
            "type": type(exc).__name__,
            "message": str(exc),
            "module": type(exc).__module__,
            "args": list(exc.args) if exc.args else [],
        }
    except Exception:
        return {
            "type": "UnknownError",
            "message": "无法序列化异常信息",
            "module": "builtins",
            "args": [],
        }


def create_serializable_error(error_msg: str, error_type: str = "RuntimeError") -> Dict[str, Any]:
    """创建可序列化的错误信息"""
    return {
        "type": error_type,
        "message": error_msg,
        "module": "builtins",
        "args": [error_msg],
    }


# 导出Celery应用
__all__ = ["celery_app", "parse_pdf_task", "batch_parse_task", "cleanup_old_files"] 