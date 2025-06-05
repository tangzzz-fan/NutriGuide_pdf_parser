"""
Settings Configuration - 应用配置管理
支持多环境配置和敏感信息管理
"""

import os
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基础配置
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=7800, env="PORT")
    
    # API 配置
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    backend_api_url: str = Field(default="http://localhost:7800", env="BACKEND_API_URL")
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    
    # 数据库配置
    mongodb_url: str = Field(default="mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_database: str = Field(default="nutriguide_pdf", env="MONGODB_DATABASE")
    mongodb_max_pool_size: int = Field(default=10, env="MONGODB_MAX_POOL_SIZE")
    mongodb_min_pool_size: int = Field(default=5, env="MONGODB_MIN_POOL_SIZE")
    
    # Redis 配置 (Celery)
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    
    # 文件处理配置
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    max_file_size_sync: int = Field(default=5 * 1024 * 1024, env="MAX_FILE_SIZE_SYNC")  # 5MB
    allowed_extensions: List[str] = Field(default=["pdf"], env="ALLOWED_EXTENSIONS")
    upload_dir: str = Field(default="uploads", env="UPLOAD_DIR")
    temp_dir: str = Field(default="temp", env="TEMP_DIR")
    
    # PDF 解析配置
    default_parsing_type: str = Field(default="auto", env="DEFAULT_PARSING_TYPE")
    ocr_enabled: bool = Field(default=True, env="OCR_ENABLED")
    tesseract_cmd: Optional[str] = Field(default=None, env="TESSERACT_CMD")
    tesseract_languages: str = Field(default="eng+chi_sim", env="TESSERACT_LANGUAGES")
    
    # 异步任务配置
    celery_task_time_limit: int = Field(default=1800, env="CELERY_TASK_TIME_LIMIT")  # 30分钟
    celery_task_soft_time_limit: int = Field(default=1500, env="CELERY_TASK_SOFT_TIME_LIMIT")  # 25分钟
    celery_worker_prefetch_multiplier: int = Field(default=1, env="CELERY_WORKER_PREFETCH_MULTIPLIER")
    celery_max_tasks_per_child: int = Field(default=50, env="CELERY_MAX_TASKS_PER_CHILD")
    
    # 日志配置
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_rotation: str = Field(default="1 day", env="LOG_ROTATION")
    log_retention: str = Field(default="30 days", env="LOG_RETENTION")
    
    # 安全配置
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # API 限流配置
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # 缓存配置
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1小时
    
    # 监控配置
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    health_check_interval: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")  # 秒
    
    # 数据清理配置
    cleanup_enabled: bool = Field(default=True, env="CLEANUP_ENABLED")
    cleanup_interval_hours: int = Field(default=24, env="CLEANUP_INTERVAL_HOURS")
    cleanup_retention_days: int = Field(default=30, env="CLEANUP_RETENTION_DAYS")
    
    # 第三方服务配置
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    webhook_retries: int = Field(default=3, env="WEBHOOK_RETRIES")
    
    # AI/ML 配置
    ai_confidence_threshold: float = Field(default=0.7, env="AI_CONFIDENCE_THRESHOLD")
    nutrition_extraction_model: str = Field(default="default", env="NUTRITION_EXTRACTION_MODEL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._setup_directories()
        self._validate_config()
    
    def _setup_directories(self):
        """创建必要的目录"""
        directories = [
            self.upload_dir,
            self.temp_dir,
            "logs",
            "static",
            "templates"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _validate_config(self):
        """验证配置"""
        # 验证文件大小限制
        if self.max_file_size_sync > self.max_file_size:
            raise ValueError("同步解析文件大小限制不能超过总体限制")
        
        # 验证 Celery 时间限制
        if self.celery_task_soft_time_limit >= self.celery_task_time_limit:
            raise ValueError("Celery 软时间限制必须小于硬时间限制")
        
        # 验证环境
        if self.environment not in ["development", "testing", "staging", "production", "dev", "qa", "prod"]:
            raise ValueError(f"不支持的环境: {self.environment}")
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.environment == "testing"
    
    def get_mongodb_settings(self) -> dict:
        """获取 MongoDB 连接设置"""
        return {
            "host": self.mongodb_url,
            "maxPoolSize": self.mongodb_max_pool_size,
            "minPoolSize": self.mongodb_min_pool_size,
            "serverSelectionTimeoutMS": 5000,
            "connectTimeoutMS": 10000,
            "socketTimeoutMS": 30000
        }
    
    def get_celery_config(self) -> dict:
        """获取 Celery 配置"""
        return {
            "broker_url": self.celery_broker_url,
            "result_backend": self.celery_result_backend,
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": "UTC",
            "enable_utc": True,
            "task_track_started": True,
            "task_time_limit": self.celery_task_time_limit,
            "task_soft_time_limit": self.celery_task_soft_time_limit,
            "worker_prefetch_multiplier": self.celery_worker_prefetch_multiplier,
            "worker_max_tasks_per_child": self.celery_max_tasks_per_child,
            "result_expires": 3600,
            "task_default_queue": "pdf_parsing",
            "task_routes": {
                "parse_pdf_task": {"queue": "pdf_parsing"},
                "batch_parse_task": {"queue": "batch_processing"},
                "cleanup_old_files": {"queue": "maintenance"}
            }
        }
    
    def get_cors_config(self) -> dict:
        """获取 CORS 配置"""
        origins = self.cors_origins
        if self.is_development and "*" not in origins:
            origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])
        
        return {
            "allow_origins": origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["*"]
        }
    
    def get_log_config(self) -> dict:
        """获取日志配置"""
        config = {
            "level": self.log_level,
            "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
            "rotation": self.log_rotation,
            "retention": self.log_retention,
            "compression": "zip" if self.is_production else None
        }
        
        if self.log_file:
            config["sink"] = self.log_file
        
        return config


@lru_cache()
def get_settings() -> Settings:
    """获取设置实例 (缓存)"""
    return Settings()


# 导出常用设置
settings = get_settings() 