"""
Logger Utility - 基于loguru的日志管理工具
统一管理整个服务的日志输出
"""

import sys
import os
from pathlib import Path
from loguru import logger
from typing import Optional

from config.settings import get_settings

settings = get_settings()


def setup_logger():
    """设置日志配置"""
    # 移除默认handler
    logger.remove()
    
    # 确保logs目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 控制台输出格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件输出格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 控制台输出
    logger.add(
        sys.stdout,
        format=console_format,
        level="INFO" if settings.environment == "production" else "DEBUG",
        colorize=True
    )
    
    # 一般日志文件
    logger.add(
        "logs/app.log",
        format=file_format,
        level="INFO",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # 错误日志文件
    logger.add(
        "logs/error.log",
        format=file_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # 解析专用日志
    logger.add(
        "logs/parsing.log",
        format=file_format,
        level="DEBUG",
        rotation="20 MB",
        retention="15 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: "pdf_parser" in record["name"] or "parsing" in record["extra"]
    )
    
    # 性能日志
    logger.add(
        "logs/performance.log",
        format=file_format,
        level="INFO",
        rotation="5 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
        filter=lambda record: "performance" in record["extra"]
    )


def get_logger(name: Optional[str] = None):
    """
    获取logger实例
    
    Args:
        name: logger名称，通常使用__name__
        
    Returns:
        logger实例
    """
    if name:
        return logger.bind(name=name)
    return logger


# 在模块加载时初始化日志配置
setup_logger()


# 为解析任务添加专用的日志记录器
def log_parsing_start(file_id: str, filename: str, parsing_type: str):
    """记录解析开始"""
    logger.bind(parsing=True).info(
        f"开始解析文件 - File ID: {file_id}, 文件名: {filename}, 类型: {parsing_type}"
    )


def log_parsing_progress(file_id: str, progress: int, message: str = ""):
    """记录解析进度"""
    logger.bind(parsing=True).info(
        f"解析进度更新 - File ID: {file_id}, 进度: {progress}%, 消息: {message}"
    )


def log_parsing_complete(file_id: str, quality_score: float, duration: float):
    """记录解析完成"""
    logger.bind(parsing=True, performance=True).info(
        f"解析完成 - File ID: {file_id}, 质量分数: {quality_score:.2f}, 耗时: {duration:.2f}秒"
    )


def log_parsing_error(file_id: str, error: str, duration: float = 0):
    """记录解析错误"""
    logger.bind(parsing=True).error(
        f"解析失败 - File ID: {file_id}, 错误: {error}, 耗时: {duration:.2f}秒"
    )


def log_performance(operation: str, duration: float, **kwargs):
    """记录性能信息"""
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.bind(performance=True).info(
        f"性能统计 - 操作: {operation}, 耗时: {duration:.3f}秒, 详情: {extra_info}"
    )


def log_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录API请求"""
    logger.bind(api=True).info(
        f"API请求 - {method} {endpoint} -> {status_code} ({duration:.3f}s)"
    )


def log_database_operation(operation: str, collection: str, duration: float, success: bool):
    """记录数据库操作"""
    status = "成功" if success else "失败"
    logger.bind(database=True, performance=True).info(
        f"数据库操作 - {operation} {collection} -> {status} ({duration:.3f}s)"
    )


# 自定义异常日志记录器
class ExceptionLogger:
    """异常日志记录器"""
    
    @staticmethod
    def log_exception(exc: Exception, context: str = "", **kwargs):
        """记录异常信息"""
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        logger.bind(exception=True).error(
            f"异常发生 - 上下文: {context}, 异常: {type(exc).__name__}: {str(exc)}, 详情: {extra_info}",
            exc_info=exc
        )
    
    @staticmethod
    def log_critical_error(error: str, **kwargs):
        """记录严重错误"""
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        logger.bind(critical=True).critical(
            f"严重错误 - {error}, 详情: {extra_info}"
        )


# 导出常用功能
__all__ = [
    'get_logger',
    'log_parsing_start',
    'log_parsing_progress', 
    'log_parsing_complete',
    'log_parsing_error',
    'log_performance',
    'log_api_request',
    'log_database_operation',
    'ExceptionLogger'
] 