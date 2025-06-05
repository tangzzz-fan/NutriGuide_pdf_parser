"""
PDF Parser Service - 核心解析引擎
支持多种PDF文档类型的解析，包括营养标签、食谱、膳食指南等
"""

import os
import re
import io
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json

import pdfplumber
# import fitz  # PyMuPDF - 临时注释，使用备用方案
import pytesseract
from PIL import Image
# import cv2  # 临时注释，避免NumPy版本冲突
import numpy as np
import pandas as pd

from utils.logger import get_logger

logger = get_logger(__name__)


class PDFParserService:
    """高级PDF解析服务"""
    
    def __init__(self):
        self.extractors = {
            'nutrition_label': NutritionLabelExtractor(),
            'recipe': RecipeExtractor(),
            'diet_guide': DietGuideExtractor(),
            'auto': AutoDetectExtractor()
        }
        logger.info("PDF Parser Service initialized with real parsing capabilities")
    
    async def parse_pdf(self, file_path: str, parsing_type: str = "auto") -> Dict[str, Any]:
        """
        核心PDF解析方法
        
        Args:
            file_path: PDF文件路径
            parsing_type: 解析类型 (auto, nutrition_label, recipe, diet_guide)
            
        Returns:
            解析结果字典
        """
        try:
            logger.info(f"Starting PDF parsing: {file_path}, type: {parsing_type}")
            
            # 1. 基础信息提取
            basic_info = await self._extract_basic_info(file_path)
            
            # 2. 文本提取
            text_content = await self._extract_text(file_path)
            
            # 3. 图像提取和OCR (暂时跳过，使用文本提取)
            ocr_content = await self._extract_ocr_content_alternative(file_path)
            
            # 4. 选择合适的解析器
            extractor = self.extractors.get(parsing_type, self.extractors['auto'])
            
            # 5. 智能内容解析
            extracted_data = await extractor.extract(text_content, ocr_content, file_path)
            
            # 6. 数据标准化
            standardized_data = await self._standardize_data(extracted_data)
            
            # 7. 质量评估
            quality_score = await self._assess_quality(standardized_data, text_content)
            
            result = {
                "basic_info": basic_info,
                "text_content": text_content[:1000] if text_content else "",  # 截断保存
                "extracted_data": standardized_data,
                "quality_score": quality_score,
                "parsing_type": parsing_type,
                "status": "completed",
                "processed_at": datetime.utcnow().isoformat(),
                "mock": False
            }
            
            logger.info(f"PDF parsing completed successfully: {file_path}")
            return result
            
        except Exception as e:
            logger.error(f"PDF parsing failed for {file_path}: {str(e)}")
            return {
                "basic_info": {"filename": os.path.basename(file_path)},
                "error": str(e),
                "status": "failed",
                "processed_at": datetime.utcnow().isoformat(),
                "mock": False
            }
    
    async def _extract_basic_info(self, file_path: str) -> Dict[str, Any]:
        """提取PDF基础信息 - 使用pdfplumber"""
        try:
            with pdfplumber.open(file_path) as pdf:
                metadata = pdf.metadata or {}
                
                return {
                    "filename": os.path.basename(file_path),
                    "file_size": os.path.getsize(file_path),
                    "page_count": len(pdf.pages),
                    "title": metadata.get('Title', ''),
                    "author": metadata.get('Author', ''),
                    "subject": metadata.get('Subject', ''),
                    "creator": metadata.get('Creator', ''),
                    "created": str(metadata.get('CreationDate', '')),
                    "modified": str(metadata.get('ModDate', '')),
                }
        except Exception as e:
            logger.error(f"Failed to extract basic info: {e}")
            return {
                "filename": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                "error": str(e)
            }
    
    async def _extract_text(self, file_path: str) -> str:
        """使用pdfplumber提取文本内容"""
        try:
            text_content = []
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取文本
                    page_text = page.extract_text()
                    if page_text:
                        text_content.append(f"--- Page {page_num} ---\n{page_text}")
                    
                    # 提取表格
                    tables = page.extract_tables()
                    for table_idx, table in enumerate(tables):
                        if table:
                            text_content.append(f"--- Page {page_num} Table {table_idx + 1} ---")
                            for row in table:
                                if row:
                                    text_content.append(" | ".join(str(cell) if cell else "" for cell in row))
            
            return "\n".join(text_content)
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ""
    
    async def _extract_ocr_content_alternative(self, file_path: str) -> str:
        """备用OCR提取方法 - 跳过图像OCR，仅依赖文本提取"""
        try:
            # 暂时返回空字符串，避免fitz依赖
            # 可以在安装Tesseract和相关依赖后再启用完整OCR功能
            logger.info("OCR extraction temporarily disabled - using text extraction only")
            return ""
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""
    
    async def _extract_ocr_content(self, file_path: str) -> str:
        """提取图像并进行OCR识别 - 需要fitz，暂时禁用"""
        # 暂时禁用此方法，因为依赖fitz
        return await self._extract_ocr_content_alternative(file_path)
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """图像预处理，提高OCR识别率 - 使用PIL代替cv2"""
        try:
            # 转换为灰度图
            if image.mode != 'L':
                gray_image = image.convert('L')
            else:
                gray_image = image
            
            # 简单的阈值处理（使用PIL）
            # 转换为numpy数组进行处理
            img_array = np.array(gray_image)
            
            # 简单的二值化处理
            threshold = 128
            binary_array = np.where(img_array > threshold, 255, 0).astype(np.uint8)
            
            return Image.fromarray(binary_array)
            
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            return image
    
    async def _standardize_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """数据标准化处理"""
        try:
            if not extracted_data:
                return {}
            
            data_type = extracted_data.get('type', 'unknown')
            
            if data_type == 'food':
                return self._standardize_food_data(extracted_data)
            elif data_type == 'recipe':
                return self._standardize_recipe_data(extracted_data)
            elif data_type == 'diet_guide':
                return self._standardize_diet_guide_data(extracted_data)
            else:
                return extracted_data
                
        except Exception as e:
            logger.error(f"Data standardization failed: {e}")
            return extracted_data
    
    def _standardize_food_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化食品数据"""
        standardized = {
            "type": "food",
            "name": data.get('name', ''),
            "brand": data.get('brand', ''),
            "category": data.get('category', ''),
            "nutrition": {}
        }
        
        # 标准化营养成分
        nutrition = data.get('nutrition', {})
        for nutrient, value in nutrition.items():
            if isinstance(value, dict) and 'value' in value:
                standardized['nutrition'][nutrient] = {
                    'value': float(value['value']) if value['value'] else 0,
                    'unit': value.get('unit', 'g')
                }
            elif isinstance(value, (int, float)):
                standardized['nutrition'][nutrient] = {
                    'value': float(value),
                    'unit': 'g'
                }
        
        return standardized
    
    def _standardize_recipe_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化食谱数据"""
        return {
            "type": "recipe",
            "name": data.get('name', ''),
            "ingredients": data.get('ingredients', []),
            "instructions": data.get('instructions', []),
            "serving_size": data.get('serving_size', ''),
            "prep_time": data.get('prep_time', ''),
            "cook_time": data.get('cook_time', ''),
            "nutrition": data.get('nutrition', {})
        }
    
    def _standardize_diet_guide_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化膳食指南数据"""
        return {
            "type": "diet_guide",
            "title": data.get('title', ''),
            "recommendations": data.get('recommendations', []),
            "food_groups": data.get('food_groups', {}),
            "daily_intake": data.get('daily_intake', {})
        }
    
    async def _assess_quality(self, data: Dict[str, Any], text_content: str) -> float:
        """评估解析质量"""
        try:
            score = 0.0
            
            # 基础分数
            if data and data.get('type'):
                score += 0.3
            
            # 内容完整性
            if data.get('name'):
                score += 0.2
            
            if data.get('nutrition') and len(data['nutrition']) > 0:
                score += 0.3
            
            # 文本质量
            if text_content and len(text_content) > 100:
                score += 0.2
            
            return min(score, 1.0)
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return 0.0


class NutritionLabelExtractor:
    """营养标签专用解析器"""
    
    async def extract(self, text_content: str, ocr_content: str, file_path: str) -> Dict[str, Any]:
        """提取营养标签信息"""
        try:
            combined_text = f"{text_content}\n{ocr_content}"
            
            # 提取食品基础信息
            food_info = self._extract_food_info(combined_text)
            
            # 提取营养成分
            nutrition_data = self._extract_nutrition_facts(combined_text)
            
            return {
                "type": "food",
                "name": food_info.get('name', ''),
                "brand": food_info.get('brand', ''),
                "category": food_info.get('category', ''),
                "nutrition": nutrition_data,
                "raw_text": combined_text[:500]  # 保存部分原文用于调试
            }
            
        except Exception as e:
            logger.error(f"Nutrition label extraction failed: {e}")
            return {"type": "food", "error": str(e)}
    
    def _extract_food_info(self, text: str) -> Dict[str, str]:
        """提取食品基础信息"""
        info = {}
        
        # 食品名称提取
        name_patterns = [
            r'产品名称[：:]\s*([^\n\r]+)',
            r'食品名称[：:]\s*([^\n\r]+)',
            r'品名[：:]\s*([^\n\r]+)',
            r'^([^\n\r]+)营养成分表',
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.MULTILINE)
            if match:
                info['name'] = match.group(1).strip()
                break
        
        # 品牌提取
        brand_patterns = [
            r'品牌[：:]\s*([^\n\r]+)',
            r'商标[：:]\s*([^\n\r]+)',
            r'厂家[：:]\s*([^\n\r]+)',
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, text)
            if match:
                info['brand'] = match.group(1).strip()
                break
        
        return info
    
    def _extract_nutrition_facts(self, text: str) -> Dict[str, Dict[str, Any]]:
        """提取营养成分信息"""
        nutrition = {}
        
        # 营养成分模式 - 支持中英文
        patterns = {
            'calories': [
                r'能量[：:]\s*(\d+(?:\.\d+)?)\s*(?:kcal|千卡|大卡|KJ|千焦)',
                r'热量[：:]\s*(\d+(?:\.\d+)?)\s*(?:kcal|千卡|大卡)',
                r'Calories[：:]\s*(\d+(?:\.\d+)?)',
            ],
            'protein': [
                r'蛋白质[：:]\s*(\d+(?:\.\d+)?)\s*g',
                r'Protein[：:]\s*(\d+(?:\.\d+)?)\s*g',
            ],
            'fat': [
                r'脂肪[：:]\s*(\d+(?:\.\d+)?)\s*g',
                r'Fat[：:]\s*(\d+(?:\.\d+)?)\s*g',
            ],
            'carbohydrates': [
                r'碳水化合物[：:]\s*(\d+(?:\.\d+)?)\s*g',
                r'Carbohydrates?[：:]\s*(\d+(?:\.\d+)?)\s*g',
            ],
            'sodium': [
                r'钠[：:]\s*(\d+(?:\.\d+)?)\s*mg',
                r'Sodium[：:]\s*(\d+(?:\.\d+)?)\s*mg',
            ],
            'fiber': [
                r'膳食纤维[：:]\s*(\d+(?:\.\d+)?)\s*g',
                r'纤维[：:]\s*(\d+(?:\.\d+)?)\s*g',
                r'Fiber[：:]\s*(\d+(?:\.\d+)?)\s*g',
            ],
            'sugar': [
                r'糖[：:]\s*(\d+(?:\.\d+)?)\s*g',
                r'Sugar[：:]\s*(\d+(?:\.\d+)?)\s*g',
            ]
        }
        
        for nutrient, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = float(match.group(1))
                    unit = 'kcal' if nutrient == 'calories' else ('mg' if nutrient == 'sodium' else 'g')
                    nutrition[nutrient] = {
                        'value': value,
                        'unit': unit
                    }
                    break
        
        return nutrition


class RecipeExtractor:
    """食谱解析器"""
    
    async def extract(self, text_content: str, ocr_content: str, file_path: str) -> Dict[str, Any]:
        """提取食谱信息"""
        try:
            combined_text = f"{text_content}\n{ocr_content}"
            
            recipe_data = {
                "type": "recipe",
                "name": self._extract_recipe_name(combined_text),
                "ingredients": self._extract_ingredients(combined_text),
                "instructions": self._extract_instructions(combined_text),
                "serving_size": self._extract_serving_size(combined_text),
                "prep_time": self._extract_time(combined_text, "prep"),
                "cook_time": self._extract_time(combined_text, "cook"),
            }
            
            return recipe_data
            
        except Exception as e:
            logger.error(f"Recipe extraction failed: {e}")
            return {"type": "recipe", "error": str(e)}
    
    def _extract_recipe_name(self, text: str) -> str:
        """提取食谱名称"""
        patterns = [
            r'菜名[：:]\s*([^\n\r]+)',
            r'食谱[：:]\s*([^\n\r]+)',
            r'Recipe[：:]\s*([^\n\r]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_ingredients(self, text: str) -> List[str]:
        """提取食材列表"""
        ingredients = []
        # 实现食材提取逻辑
        # 这里可以根据实际需求完善
        return ingredients
    
    def _extract_instructions(self, text: str) -> List[str]:
        """提取制作步骤"""
        instructions = []
        # 实现步骤提取逻辑
        return instructions
    
    def _extract_serving_size(self, text: str) -> str:
        """提取份量信息"""
        patterns = [
            r'份量[：:]\s*([^\n\r]+)',
            r'Serving[：:]\s*([^\n\r]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_time(self, text: str, time_type: str) -> str:
        """提取时间信息"""
        if time_type == "prep":
            patterns = [r'准备时间[：:]\s*([^\n\r]+)', r'Prep time[：:]\s*([^\n\r]+)']
        else:
            patterns = [r'烹饪时间[：:]\s*([^\n\r]+)', r'Cook time[：:]\s*([^\n\r]+)']
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""


class DietGuideExtractor:
    """膳食指南解析器"""
    
    async def extract(self, text_content: str, ocr_content: str, file_path: str) -> Dict[str, Any]:
        """提取膳食指南信息"""
        try:
            combined_text = f"{text_content}\n{ocr_content}"
            
            return {
                "type": "diet_guide",
                "title": self._extract_title(combined_text),
                "recommendations": self._extract_recommendations(combined_text),
                "food_groups": self._extract_food_groups(combined_text),
                "daily_intake": self._extract_daily_intake(combined_text)
            }
            
        except Exception as e:
            logger.error(f"Diet guide extraction failed: {e}")
            return {"type": "diet_guide", "error": str(e)}
    
    def _extract_title(self, text: str) -> str:
        """提取标题"""
        lines = text.split('\n')
        if lines:
            return lines[0].strip()
        return ""
    
    def _extract_recommendations(self, text: str) -> List[str]:
        """提取建议列表"""
        recommendations = []
        # 实现建议提取逻辑
        return recommendations
    
    def _extract_food_groups(self, text: str) -> Dict[str, Any]:
        """提取食物分组信息"""
        return {}
    
    def _extract_daily_intake(self, text: str) -> Dict[str, Any]:
        """提取每日摄入建议"""
        return {}


class AutoDetectExtractor:
    """自动检测解析器"""
    
    def __init__(self):
        self.extractors = {
            'nutrition': NutritionLabelExtractor(),
            'recipe': RecipeExtractor(),
            'diet_guide': DietGuideExtractor()
        }
    
    async def extract(self, text_content: str, ocr_content: str, file_path: str) -> Dict[str, Any]:
        """自动检测文档类型并选择合适的解析器"""
        try:
            combined_text = f"{text_content}\n{ocr_content}"
            
            # 检测文档类型
            doc_type = self._detect_document_type(combined_text)
            
            # 选择对应的解析器
            extractor = self.extractors.get(doc_type, self.extractors['nutrition'])
            
            return await extractor.extract(text_content, ocr_content, file_path)
            
        except Exception as e:
            logger.error(f"Auto detection failed: {e}")
            return {"type": "unknown", "error": str(e)}
    
    def _detect_document_type(self, text: str) -> str:
        """检测文档类型"""
        text_lower = text.lower()
        
        # 营养标签关键词
        nutrition_keywords = ['营养成分', '热量', '蛋白质', '脂肪', '碳水化合物', 'nutrition', 'calories']
        nutrition_score = sum(1 for keyword in nutrition_keywords if keyword in text_lower)
        
        # 食谱关键词
        recipe_keywords = ['食材', '制作方法', '烹饪', '步骤', 'ingredients', 'recipe', 'cooking']
        recipe_score = sum(1 for keyword in recipe_keywords if keyword in text_lower)
        
        # 膳食指南关键词
        guide_keywords = ['膳食指南', '营养建议', '饮食建议', 'dietary guidelines', 'nutrition guide']
        guide_score = sum(1 for keyword in guide_keywords if keyword in text_lower)
        
        # 选择得分最高的类型
        scores = {
            'nutrition': nutrition_score,
            'recipe': recipe_score,
            'diet_guide': guide_score
        }
        
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'nutrition' 