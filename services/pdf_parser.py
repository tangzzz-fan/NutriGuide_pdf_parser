"""
Mock PDF Parser Service - temporary version without PDF processing dependencies
This allows the service to start while the actual PDF libraries are being installed
"""

import os
from typing import Dict, Any
from datetime import datetime

from utils.logger import get_logger

logger = get_logger(__name__)


class PDFParserService:
    """Mock PDF解析服务 - 临时版本"""
    
    def __init__(self):
        logger.info("Using mock PDF parser service")
    
    async def parse_pdf(self, file_path: str, parsing_type: str = "auto") -> Dict[str, Any]:
        """
        Mock PDF解析 - 返回示例数据
        """
        try:
            logger.info(f"Mock parsing PDF: {file_path}, type: {parsing_type}")
            
            # Return mock data structure
            return {
                "basic_info": {
                    "filename": os.path.basename(file_path),
                    "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    "page_count": 1,
                    "title": "Mock Document",
                    "author": "Mock System",
                },
                "extracted_data": {
                    "type": "food",
                    "name": "Mock Food Item",
                    "nutrition": {
                        "calories": {"value": 100, "unit": "kcal"},
                        "protein": {"value": 5.0, "unit": "g"},
                        "carbohydrates": {"value": 15.0, "unit": "g"},
                        "fat": {"value": 2.0, "unit": "g"}
                    }
                },
                "quality_score": 0.8,
                "parsing_type": parsing_type,
                "status": "completed",
                "processed_at": datetime.utcnow().isoformat(),
                "mock": True  # Indicator that this is mock data
            }
            
        except Exception as e:
            logger.error(f"Mock PDF parsing failed: {str(e)}")
            return {
                "basic_info": {"filename": os.path.basename(file_path)},
                "error": str(e),
                "status": "failed",
                "processed_at": datetime.utcnow().isoformat(),
                "mock": True
            } 