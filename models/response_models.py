"""
Response Models - API响应数据模型
定义各种API接口的响应格式
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class ParsingStatus(str, Enum):
    """解析状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"


class ParsingType(str, Enum):
    """解析类型枚举"""
    AUTO = "auto"
    NUTRITION_LABEL = "nutrition_label"
    RECIPE = "recipe"
    DIET_GUIDE = "diet_guide"
    FOOD = "food"


# 基础响应模型
class BaseResponse(BaseModel):
    """基础响应模型"""
    status: str = Field(..., description="响应状态")
    message: str = Field("", description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="响应时间戳")


class HealthResponse(BaseResponse):
    """健康检查响应"""
    services: Dict[str, str] = Field(..., description="服务状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "message": "All services are running",
                "timestamp": "2024-01-01T12:00:00Z",
                "services": {
                    "database": "connected",
                    "redis": "connected",
                    "pdf_parser": "ready"
                }
            }
        }


class ErrorResponse(BaseResponse):
    """错误响应"""
    error_code: Optional[str] = Field(None, description="错误代码")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "File parsing failed",
                "timestamp": "2024-01-01T12:00:00Z",
                "error_code": "PARSE_ERROR",
                "error_details": {
                    "file_id": "abc123",
                    "reason": "Unsupported file format"
                }
            }
        }


# 营养数据模型
class NutritionValue(BaseModel):
    """营养成分值"""
    value: float = Field(..., description="数值")
    unit: str = Field(..., description="单位")
    
    class Config:
        json_schema_extra = {
            "example": {
                "value": 250.0,
                "unit": "kcal"
            }
        }


class NutritionData(BaseModel):
    """营养数据"""
    calories: Optional[NutritionValue] = Field(None, description="热量")
    protein: Optional[NutritionValue] = Field(None, description="蛋白质")
    fat: Optional[NutritionValue] = Field(None, description="脂肪")
    carbohydrates: Optional[NutritionValue] = Field(None, description="碳水化合物")
    fiber: Optional[NutritionValue] = Field(None, description="膳食纤维")
    sugar: Optional[NutritionValue] = Field(None, description="糖")
    sodium: Optional[NutritionValue] = Field(None, description="钠")
    calcium: Optional[NutritionValue] = Field(None, description="钙")
    iron: Optional[NutritionValue] = Field(None, description="铁")
    vitamin_c: Optional[NutritionValue] = Field(None, description="维生素C")
    vitamin_a: Optional[NutritionValue] = Field(None, description="维生素A")
    
    class Config:
        json_schema_extra = {
            "example": {
                "calories": {"value": 250.0, "unit": "kcal"},
                "protein": {"value": 15.0, "unit": "g"},
                "fat": {"value": 8.0, "unit": "g"},
                "carbohydrates": {"value": 35.0, "unit": "g"}
            }
        }


# 食品信息模型
class FoodInfo(BaseModel):
    """食品基础信息"""
    name: Optional[str] = Field(None, description="食品名称")
    brand: Optional[str] = Field(None, description="品牌")
    category: Optional[str] = Field(None, description="食品类别")
    net_weight: Optional[str] = Field(None, description="净含量")
    serving_size: Optional[str] = Field(None, description="每份用量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "牛奶",
                "brand": "伊利",
                "category": "奶制品",
                "net_weight": "250ml",
                "serving_size": "100ml"
            }
        }


# 食谱相关模型
class Ingredient(BaseModel):
    """食材"""
    name: str = Field(..., description="食材名称")
    amount: str = Field("", description="用量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "鸡蛋",
                "amount": "2个"
            }
        }


class RecipeInfo(BaseModel):
    """食谱信息"""
    name: Optional[str] = Field(None, description="食谱名称")
    ingredients: List[Ingredient] = Field(default_factory=list, description="食材列表")
    instructions: List[str] = Field(default_factory=list, description="制作步骤")
    servings: Optional[str] = Field(None, description="份数")
    prep_time: Optional[str] = Field(None, description="准备时间")
    cook_time: Optional[str] = Field(None, description="烹饪时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "番茄炒蛋",
                "ingredients": [
                    {"name": "鸡蛋", "amount": "2个"},
                    {"name": "番茄", "amount": "1个"}
                ],
                "instructions": [
                    "将鸡蛋打散备用",
                    "番茄切块炒制"
                ],
                "servings": "2人份",
                "prep_time": "10分钟",
                "cook_time": "5分钟"
            }
        }


# 膳食指南模型
class GuideRecommendation(BaseModel):
    """指南建议"""
    type: str = Field(..., description="建议类型")
    content: str = Field(..., description="建议内容")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "recommendation",
                "content": "每天饮用300ml牛奶"
            }
        }


class GuideSection(BaseModel):
    """指南章节"""
    title: str = Field(..., description="章节标题")
    position: int = Field(..., description="位置")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "合理膳食",
                "position": 0
            }
        }


class DietGuideInfo(BaseModel):
    """膳食指南信息"""
    title: Optional[str] = Field(None, description="指南标题")
    structure: List[GuideSection] = Field(default_factory=list, description="指南结构")
    recommendations: List[GuideRecommendation] = Field(default_factory=list, description="建议列表")
    target_group: Optional[str] = Field(None, description="目标人群")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "中国居民膳食指南",
                "structure": [
                    {"title": "合理膳食", "position": 0}
                ],
                "recommendations": [
                    {"type": "recommendation", "content": "每天饮用300ml牛奶"}
                ],
                "target_group": "一般人群"
            }
        }


# PDF基础信息模型
class PDFBasicInfo(BaseModel):
    """PDF基础信息"""
    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小(字节)")
    page_count: int = Field(..., description="页数")
    title: Optional[str] = Field(None, description="文档标题")
    author: Optional[str] = Field(None, description="作者")
    creator: Optional[str] = Field(None, description="创建程序")
    creation_date: Optional[str] = Field(None, description="创建日期")
    modification_date: Optional[str] = Field(None, description="修改日期")
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "nutrition_label.pdf",
                "file_size": 1024000,
                "page_count": 1,
                "title": "营养标签",
                "author": "食品公司",
                "creator": "PDF Creator",
                "creation_date": "2024-01-01",
                "modification_date": "2024-01-01"
            }
        }


# 解析结果模型
class ExtractedData(BaseModel):
    """提取的数据"""
    type: str = Field(..., description="数据类型")
    food_info: Optional[FoodInfo] = Field(None, description="食品信息")
    recipe_info: Optional[RecipeInfo] = Field(None, description="食谱信息")
    guide_info: Optional[DietGuideInfo] = Field(None, description="指南信息")
    nutrition: Optional[Union[NutritionData, Dict[str, Any]]] = Field(None, description="营养数据")
    raw_text: Optional[str] = Field(None, description="原始文本")
    tables: Optional[List[Dict[str, Any]]] = Field(None, description="表格数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "food",
                "food_info": {
                    "name": "牛奶",
                    "brand": "伊利"
                },
                "nutrition": {
                    "calories": {"value": 250.0, "unit": "kcal"}
                },
                "raw_text": "营养标签内容..."
            }
        }


class ParseResult(BaseModel):
    """完整解析结果"""
    basic_info: PDFBasicInfo = Field(..., description="PDF基础信息")
    extracted_data: ExtractedData = Field(..., description="提取的数据")
    quality_score: float = Field(..., description="质量分数(0-100)")
    parsing_type: ParsingType = Field(..., description="解析类型")
    status: ParsingStatus = Field(..., description="解析状态")
    processed_at: str = Field(..., description="处理时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "basic_info": {
                    "filename": "nutrition_label.pdf",
                    "file_size": 1024000,
                    "page_count": 1
                },
                "extracted_data": {
                    "type": "food",
                    "nutrition": {
                        "calories": {"value": 250.0, "unit": "kcal"}
                    }
                },
                "quality_score": 85.5,
                "parsing_type": "nutrition_label",
                "status": "completed",
                "processed_at": "2024-01-01T12:00:00Z"
            }
        }


# API响应模型
class ParseResponse(BaseResponse):
    """解析响应"""
    document_id: str = Field(..., description="文档ID")
    data: Optional[ParseResult] = Field(None, description="解析结果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "message": "PDF parsed successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "document_id": "abc123",
                "data": {
                    "quality_score": 85.5,
                    "parsing_type": "nutrition_label",
                    "status": "completed"
                }
            }
        }


class AsyncParseResponse(BaseResponse):
    """异步解析响应"""
    document_id: str = Field(..., description="文档ID")
    task_id: str = Field(..., description="任务ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "queued",
                "message": "PDF parsing queued for processing",
                "timestamp": "2024-01-01T12:00:00Z",
                "document_id": "abc123",
                "task_id": "task_456"
            }
        }


class ProcessingStatus(BaseResponse):
    """处理状态"""
    document_id: str = Field(..., description="文档ID")
    progress: int = Field(..., description="进度百分比(0-100)")
    data: Optional[ParseResult] = Field(None, description="解析结果(完成时)")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "processing",
                "message": "PDF parsing in progress",
                "timestamp": "2024-01-01T12:00:00Z",
                "document_id": "abc123",
                "progress": 75,
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:05:00Z"
            }
        }


# 批处理相关模型
class BatchFileInfo(BaseModel):
    """批处理文件信息"""
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    file_path: str = Field(..., description="文件路径")
    status: ParsingStatus = Field(..., description="处理状态")
    
    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "file123",
                "filename": "nutrition_label.pdf",
                "file_path": "uploads/batch_abc/nutrition_label.pdf",
                "status": "completed"
            }
        }


class BatchInfo(BaseModel):
    """批处理信息"""
    batch_id: str = Field(..., description="批次ID")
    file_count: int = Field(..., description="文件数量")
    parse_type: ParsingType = Field(..., description="解析类型")
    description: str = Field("", description="批次描述")
    status: str = Field(..., description="批次状态")
    files: List[BatchFileInfo] = Field(default_factory=list, description="文件列表")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch_abc123",
                "file_count": 5,
                "parse_type": "nutrition_label",
                "description": "营养标签批量解析",
                "status": "completed",
                "files": [],
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-01T12:30:00Z"
            }
        }


class BatchResponse(BaseResponse):
    """批处理响应"""
    batch_id: str = Field(..., description="批次ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "queued",
                "message": "Batch processing queued",
                "timestamp": "2024-01-01T12:00:00Z",
                "batch_id": "batch_abc123"
            }
        }


class HistoryResponse(BaseResponse):
    """历史记录响应"""
    total: int = Field(..., description="总数量")
    items: List[Dict[str, Any]] = Field(..., description="记录列表")
    limit: int = Field(..., description="每页限制")
    offset: int = Field(..., description="偏移量")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "History retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "total": 100,
                "items": [],
                "limit": 10,
                "offset": 0
            }
        }


# 统计相关模型
class StatisticsData(BaseModel):
    """统计数据"""
    total_count: int = Field(..., description="总解析数量")
    status_breakdown: Dict[str, int] = Field(..., description="按状态统计")
    type_breakdown: Dict[str, int] = Field(..., description="按类型统计")
    success_rate: float = Field(..., description="成功率(%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_count": 1000,
                "status_breakdown": {
                    "completed": 850,
                    "failed": 100,
                    "processing": 50
                },
                "type_breakdown": {
                    "nutrition_label": 600,
                    "recipe": 300,
                    "diet_guide": 100
                },
                "success_rate": 85.0
            }
        }


class StatisticsResponse(BaseResponse):
    """统计响应"""
    data: StatisticsData = Field(..., description="统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Statistics retrieved successfully",
                "timestamp": "2024-01-01T12:00:00Z",
                "data": {
                    "total_count": 1000,
                    "success_rate": 85.0
                }
            }
        } 