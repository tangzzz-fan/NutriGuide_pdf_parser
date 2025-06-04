from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    # Environment
    environment: str = Field(default="development", description="Environment: development, qa, production")
    
    # Database
    mongodb_uri: str = Field(default="mongodb://localhost:27017/nutriguide_dev", description="MongoDB connection URI")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    
    # External APIs
    backend_api_url: str = Field(default="http://localhost:3000", description="Backend API URL")
    
    # File Storage
    upload_dir: str = Field(default="/app/uploads", description="Upload directory path")
    max_file_size: int = Field(default=50 * 1024 * 1024, description="Maximum file size in bytes (50MB)")
    
    # Processing
    max_sync_file_size: int = Field(default=5 * 1024 * 1024, description="Maximum file size for sync processing (5MB)")
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/0", description="Celery broker URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", description="Celery result backend URL")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_dir: str = Field(default="/app/logs", description="Log directory path")
    
    # API Keys (for future use)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for enhanced parsing")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
        # Environment variable mapping
        fields = {
            'mongodb_uri': {'env': 'MONGODB_URI'},
            'redis_url': {'env': 'REDIS_URL'},
            'backend_api_url': {'env': 'BACKEND_API_URL'},
            'celery_broker_url': {'env': 'REDIS_URL'},  # Use same Redis for Celery
            'celery_result_backend': {'env': 'REDIS_URL'},
        }

# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings 