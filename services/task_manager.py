"""
Task Manager Service - 任务管理和状态追踪
负责Redis队列管理、任务状态追踪、任务监控等功能
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from celery import Celery
from celery.result import AsyncResult
import redis
from dataclasses import dataclass, asdict

from config.settings import get_settings
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class TaskStatus:
    """任务状态数据结构"""
    task_id: str
    task_type: str
    status: str  # pending, processing, completed, failed
    progress: int  # 0-100
    created_at: datetime
    updated_at: datetime
    file_id: Optional[str] = None
    filename: Optional[str] = None
    document_id: Optional[str] = None
    parsing_type: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None


@dataclass
class QueueStats:
    """队列统计信息"""
    pending_tasks: int
    processing_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_tasks: int
    average_processing_time: float
    queue_length: int


class TaskManager:
    """任务管理器"""
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
        self.redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        
        # Redis键前缀
        self.task_status_prefix = "task_status:"
        self.queue_stats_prefix = "queue_stats:"
        self.task_history_prefix = "task_history:"
        
        logger.info("Task Manager initialized")
    
    async def submit_parsing_task(
        self,
        file_path: str,
        file_id: str,
        document_id: str,
        parsing_type: str = "auto",
        callback_url: Optional[str] = None,
        priority: int = 5
    ) -> str:
        """提交PDF解析任务"""
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 创建任务状态
            task_status = TaskStatus(
                task_id=task_id,
                task_type="pdf_parsing",
                status="pending",
                progress=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                file_id=file_id,
                filename=file_path.split('/')[-1],
                document_id=document_id,
                parsing_type=parsing_type,
                message="任务已提交，等待处理..."
            )
            
            # 保存任务状态到Redis
            await self._save_task_status(task_status)
            
            # 提交到Celery
            celery_result = self.celery_app.send_task(
                'parse_pdf_task_v2',
                args=[file_path, file_id, document_id, parsing_type, callback_url],
                task_id=task_id,
                priority=priority
            )
            
            # 更新队列统计
            await self._update_queue_stats("pending", 1)
            
            logger.info(f"PDF解析任务已提交: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"提交PDF解析任务失败: {e}")
            raise
    
    async def submit_batch_parsing_task(
        self,
        batch_id: str,
        files_info: List[Dict[str, Any]],
        parsing_type: str = "auto",
        priority: int = 3
    ) -> str:
        """提交批量解析任务"""
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 创建任务状态
            task_status = TaskStatus(
                task_id=task_id,
                task_type="batch_parsing",
                status="pending",
                progress=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                message=f"批量任务已提交，共{len(files_info)}个文件..."
            )
            
            # 保存任务状态
            await self._save_task_status(task_status)
            
            # 提交到Celery
            celery_result = self.celery_app.send_task(
                'batch_parse_task_v2',
                args=[batch_id, files_info, parsing_type],
                task_id=task_id,
                priority=priority
            )
            
            # 更新队列统计
            await self._update_queue_stats("pending", 1)
            
            logger.info(f"批量解析任务已提交: {task_id}, 文件数量: {len(files_info)}")
            return task_id
            
        except Exception as e:
            logger.error(f"提交批量解析任务失败: {e}")
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        try:
            # 从Redis获取状态
            status_data = self.redis_client.get(f"{self.task_status_prefix}{task_id}")
            
            if status_data:
                data = json.loads(status_data)
                # 转换日期字符串回datetime对象
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                return TaskStatus(**data)
            
            # 如果Redis中没有，尝试从Celery获取
            celery_result = AsyncResult(task_id, app=self.celery_app)
            if celery_result.state:
                return self._convert_celery_result_to_status(celery_result)
            
            return None
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None
    
    async def update_task_status(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None
    ) -> bool:
        """更新任务状态"""
        try:
            # 获取当前状态
            current_status = await self.get_task_status(task_id)
            if not current_status:
                logger.warning(f"任务不存在: {task_id}")
                return False
            
            # 更新字段
            if status is not None:
                current_status.status = status
            if progress is not None:
                current_status.progress = progress
            if message is not None:
                current_status.message = message
            if error is not None:
                current_status.error = error
            if result is not None:
                current_status.result = result
            if duration is not None:
                current_status.duration = duration
            
            current_status.updated_at = datetime.utcnow()
            
            # 保存更新后的状态
            await self._save_task_status(current_status)
            
            # 如果任务完成或失败，更新统计信息
            if status in ['completed', 'failed']:
                await self._update_queue_stats("pending", -1)
                await self._update_queue_stats(status, 1)
                
                # 保存到历史记录
                await self._save_task_history(current_status)
            
            return True
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False
    
    async def get_queue_stats(self) -> QueueStats:
        """获取队列统计信息"""
        try:
            # 从Redis获取统计数据
            stats_data = self.redis_client.hgetall(f"{self.queue_stats_prefix}current")
            
            if not stats_data:
                # 初始化统计数据
                stats_data = {
                    'pending_tasks': '0',
                    'processing_tasks': '0', 
                    'completed_tasks': '0',
                    'failed_tasks': '0',
                    'total_tasks': '0',
                    'average_processing_time': '0.0',
                    'queue_length': '0'
                }
            
            # 获取实时队列长度
            queue_length = len(self.celery_app.control.inspect().active() or {})
            
            return QueueStats(
                pending_tasks=int(stats_data.get('pending_tasks', 0)),
                processing_tasks=int(stats_data.get('processing_tasks', 0)),
                completed_tasks=int(stats_data.get('completed_tasks', 0)),
                failed_tasks=int(stats_data.get('failed_tasks', 0)),
                total_tasks=int(stats_data.get('total_tasks', 0)),
                average_processing_time=float(stats_data.get('average_processing_time', 0.0)),
                queue_length=queue_length
            )
            
        except Exception as e:
            logger.error(f"获取队列统计失败: {e}")
            return QueueStats(0, 0, 0, 0, 0, 0.0, 0)
    
    async def get_recent_tasks(self, limit: int = 10) -> List[TaskStatus]:
        """获取最近的任务"""
        try:
            # 获取所有任务ID
            task_keys = self.redis_client.keys(f"{self.task_status_prefix}*")
            
            tasks = []
            for key in task_keys[-limit:]:  # 获取最近的任务
                task_data = self.redis_client.get(key)
                if task_data:
                    data = json.loads(task_data)
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                    data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                    tasks.append(TaskStatus(**data))
            
            # 按创建时间排序
            tasks.sort(key=lambda x: x.created_at, reverse=True)
            return tasks[:limit]
            
        except Exception as e:
            logger.error(f"获取最近任务失败: {e}")
            return []
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            # 撤销Celery任务
            self.celery_app.control.revoke(task_id, terminate=True)
            
            # 更新任务状态
            await self.update_task_status(
                task_id,
                status="cancelled",
                message="任务已取消"
            )
            
            logger.info(f"任务已取消: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
    
    async def cleanup_old_tasks(self, days: int = 7) -> int:
        """清理旧任务记录"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            cleaned_count = 0
            
            # 获取所有任务
            task_keys = self.redis_client.keys(f"{self.task_status_prefix}*")
            
            for key in task_keys:
                task_data = self.redis_client.get(key)
                if task_data:
                    data = json.loads(task_data)
                    created_at = datetime.fromisoformat(data['created_at'])
                    
                    if created_at < cutoff_time:
                        self.redis_client.delete(key)
                        cleaned_count += 1
            
            logger.info(f"清理了 {cleaned_count} 个旧任务记录")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理旧任务失败: {e}")
            return 0
    
    async def get_worker_status(self) -> Dict[str, Any]:
        """获取Worker状态"""
        try:
            inspect = self.celery_app.control.inspect()
            
            active_tasks = inspect.active() or {}
            scheduled_tasks = inspect.scheduled() or {}
            reserved_tasks = inspect.reserved() or {}
            
            worker_stats = {}
            for worker, tasks in active_tasks.items():
                worker_stats[worker] = {
                    'active_tasks': len(tasks),
                    'scheduled_tasks': len(scheduled_tasks.get(worker, [])),
                    'reserved_tasks': len(reserved_tasks.get(worker, [])),
                    'status': 'online'
                }
            
            return {
                'workers': worker_stats,
                'total_workers': len(worker_stats),
                'total_active_tasks': sum(len(tasks) for tasks in active_tasks.values()),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取Worker状态失败: {e}")
            return {'workers': {}, 'total_workers': 0, 'total_active_tasks': 0}
    
    async def _save_task_status(self, task_status: TaskStatus):
        """保存任务状态到Redis"""
        try:
            # 转换为字典并序列化日期
            data = asdict(task_status)
            data['created_at'] = task_status.created_at.isoformat()
            data['updated_at'] = task_status.updated_at.isoformat()
            
            # 保存到Redis，设置过期时间
            self.redis_client.setex(
                f"{self.task_status_prefix}{task_status.task_id}",
                timedelta(days=7),  # 7天过期
                json.dumps(data)
            )
            
        except Exception as e:
            logger.error(f"保存任务状态失败: {e}")
            raise
    
    async def _save_task_history(self, task_status: TaskStatus):
        """保存任务到历史记录"""
        try:
            # 只保存已完成或失败的任务
            if task_status.status in ['completed', 'failed']:
                history_key = f"{self.task_history_prefix}{task_status.task_id}"
                data = asdict(task_status)
                data['created_at'] = task_status.created_at.isoformat()
                data['updated_at'] = task_status.updated_at.isoformat()
                
                # 保存到历史记录，保存更长时间
                self.redis_client.setex(
                    history_key,
                    timedelta(days=30),  # 30天过期
                    json.dumps(data)
                )
                
        except Exception as e:
            logger.error(f"保存任务历史失败: {e}")
    
    async def _update_queue_stats(self, stat_type: str, increment: int):
        """更新队列统计"""
        try:
            stats_key = f"{self.queue_stats_prefix}current"
            self.redis_client.hincrby(stats_key, stat_type + "_tasks", increment)
            
            # 设置过期时间
            self.redis_client.expire(stats_key, timedelta(days=1))
            
        except Exception as e:
            logger.error(f"更新队列统计失败: {e}")
    
    def _convert_celery_result_to_status(self, celery_result: AsyncResult) -> TaskStatus:
        """将Celery结果转换为TaskStatus"""
        status_map = {
            'PENDING': 'pending',
            'STARTED': 'processing', 
            'SUCCESS': 'completed',
            'FAILURE': 'failed',
            'RETRY': 'processing',
            'REVOKED': 'cancelled'
        }
        
        return TaskStatus(
            task_id=celery_result.id,
            task_type="unknown",
            status=status_map.get(celery_result.state, 'unknown'),
            progress=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            message=f"Celery状态: {celery_result.state}",
            result=celery_result.result if celery_result.successful() else None,
            error=str(celery_result.result) if celery_result.failed() else None
        )


# 全局任务管理器实例
task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取任务管理器实例"""
    global task_manager
    if task_manager is None:
        from celery_app import celery_app
        task_manager = TaskManager(celery_app)
    return task_manager


def init_task_manager(celery_app: Celery) -> TaskManager:
    """初始化任务管理器"""
    global task_manager
    task_manager = TaskManager(celery_app)
    return task_manager 