"""
PDF Parser Service - 集成多种解析库的PDF解析服务
支持营养标签、食谱、膳食指南等不同类型的PDF文档解析
"""

import os
import io
import re
import fitz  # pymupdf
import pdfplumber
import pytesseract
import cv2
import numpy as np
from PIL import Image
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import pandas as pd
import jieba

from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class PDFParserService:
    """PDF解析服务主类"""
    
    def __init__(self):
        self.extractors = {
            'auto': AutoDetectExtractor(),
            'nutrition_label': NutritionLabelExtractor(),
            'recipe': RecipeExtractor(),
            'diet_guide': DietGuideExtractor(),
            'food': FoodInfoExtractor()
        }
        
        # 配置OCR
        if hasattr(settings, 'tesseract_cmd'):
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
    
    async def parse_pdf(self, file_path: str, parsing_type: str = "auto") -> Dict[str, Any]:
        """
        解析PDF文件主入口
        
        Args:
            file_path: PDF文件路径
            parsing_type: 解析类型 (auto, nutrition_label, recipe, diet_guide, food)
            
        Returns:
            解析结果字典
        """
        try:
            logger.info(f"开始解析PDF: {file_path}, 类型: {parsing_type}")
            
            # 1. 基础信息提取
            basic_info = self._extract_basic_info(file_path)
            logger.info(f"PDF基础信息: {basic_info}")
            
            # 2. 选择合适的解析器
            extractor = self.extractors.get(parsing_type, self.extractors['auto'])
            
            # 3. 执行解析
            extracted_data = await extractor.extract(file_path)
            
            # 4. 数据标准化
            standardized_data = self._standardize_data(extracted_data, parsing_type)
            
            # 5. 质量评估
            quality_score = self._assess_quality(standardized_data)
            
            result = {
                "basic_info": basic_info,
                "extracted_data": standardized_data,
                "quality_score": quality_score,
                "parsing_type": parsing_type,
                "status": "completed",
                "processed_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"解析完成，质量分数: {quality_score}")
            return result
            
        except Exception as e:
            logger.error(f"PDF解析失败: {str(e)}")
            return {
                "basic_info": {"filename": os.path.basename(file_path)},
                "error": str(e),
                "status": "failed",
                "processed_at": datetime.utcnow().isoformat()
            }
    
    def _extract_basic_info(self, file_path: str) -> Dict[str, Any]:
        """提取PDF基础信息"""
        try:
            with fitz.open(file_path) as doc:
                return {
                    "filename": os.path.basename(file_path),
                    "file_size": os.path.getsize(file_path),
                    "page_count": len(doc),
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "creator": doc.metadata.get("creator", ""),
                    "creation_date": doc.metadata.get("creationDate", ""),
                    "modification_date": doc.metadata.get("modDate", "")
                }
        except Exception as e:
            logger.warning(f"无法提取PDF元数据: {e}")
            return {
                "filename": os.path.basename(file_path),
                "file_size": os.path.getsize(file_path),
                "page_count": 0
            }
    
    def _standardize_data(self, data: Dict[str, Any], parsing_type: str) -> Dict[str, Any]:
        """数据标准化处理"""
        if not data or data.get('type') is None:
            return data
            
        if data.get('type') == 'food' or parsing_type == 'nutrition_label':
            return self._standardize_nutrition_data(data)
        elif data.get('type') == 'recipe' or parsing_type == 'recipe':
            return self._standardize_recipe_data(data)
        else:
            return data
    
    def _standardize_nutrition_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化营养数据"""
        nutrition = data.get('nutrition', {})
        
        # 营养成分单位标准化
        standardized_nutrition = {}
        for key, value in nutrition.items():
            if isinstance(value, (int, float)):
                standardized_nutrition[key] = {
                    "value": float(value),
                    "unit": self._get_standard_unit(key)
                }
            elif isinstance(value, str):
                # 尝试从字符串中提取数值和单位
                parsed = self._parse_nutrition_value(value)
                if parsed:
                    standardized_nutrition[key] = parsed
        
        return {
            **data,
            "nutrition": standardized_nutrition
        }
    
    def _standardize_recipe_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化食谱数据"""
        # 食谱数据标准化逻辑
        return data
    
    def _get_standard_unit(self, nutrient_key: str) -> str:
        """获取营养成分的标准单位"""
        unit_mapping = {
            'calories': 'kcal',
            'energy': 'kcal', 
            'protein': 'g',
            'fat': 'g',
            'carbohydrates': 'g',
            'fiber': 'g',
            'sugar': 'g',
            'sodium': 'mg',
            'potassium': 'mg',
            'calcium': 'mg',
            'iron': 'mg',
            'vitamin_c': 'mg',
            'vitamin_a': 'μg'
        }
        return unit_mapping.get(nutrient_key.lower(), 'g')
    
    def _parse_nutrition_value(self, value_str: str) -> Optional[Dict[str, Any]]:
        """从字符串解析营养值和单位"""
        pattern = r'(\d+(?:\.\d+)?)\s*(g|mg|μg|kcal|kj|毫克|克|千卡|大卡)?'
        match = re.search(pattern, value_str.lower())
        
        if match:
            value = float(match.group(1))
            unit = match.group(2) or 'g'
            
            # 单位标准化
            unit_conversion = {
                '毫克': 'mg',
                '克': 'g', 
                '千卡': 'kcal',
                '大卡': 'kcal',
                'kj': 'kcal'  # 简化转换
            }
            unit = unit_conversion.get(unit, unit)
            
            return {"value": value, "unit": unit}
        
        return None
    
    def _assess_quality(self, data: Dict[str, Any]) -> float:
        """评估解析质量"""
        if not data:
            return 0.0
        
        score = 0.0
        max_score = 10.0
        
        # 基础信息完整性 (2分)
        if data.get('basic_info', {}).get('filename'):
            score += 1.0
        if data.get('extracted_data'):
            score += 1.0
        
        # 核心数据存在性 (4分)  
        extracted = data.get('extracted_data', {})
        if extracted.get('nutrition'):
            score += 2.0
        if extracted.get('food_info') or extracted.get('recipe_info'):
            score += 2.0
        
        # 数据字段完整性 (4分)
        nutrition = extracted.get('nutrition', {})
        if len(nutrition) >= 3:  # 至少3个营养成分
            score += 2.0
        if len(nutrition) >= 6:  # 至少6个营养成分  
            score += 2.0
        
        return min(score / max_score * 100, 100.0)


class BaseExtractor:
    """解析器基类"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    async def extract(self, file_path: str) -> Dict[str, Any]:
        """提取数据的抽象方法"""
        raise NotImplementedError
    
    def _extract_text_with_pdfplumber(self, file_path: str) -> List[Dict[str, Any]]:
        """使用pdfplumber提取文本"""
        pages_data = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_data = {
                        "page_number": page_num + 1,
                        "text": page.extract_text() or "",
                        "tables": page.extract_tables() or []
                    }
                    pages_data.append(page_data)
        except Exception as e:
            self.logger.error(f"pdfplumber提取失败: {e}")
        
        return pages_data
    
    def _extract_text_with_pymupdf(self, file_path: str) -> List[Dict[str, Any]]:
        """使用pymupdf提取文本和图像"""
        pages_data = []
        
        try:
            with fitz.open(file_path) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    
                    # 提取文本
                    text = page.get_text()
                    
                    # 提取图像
                    images = []
                    image_list = page.get_images()
                    for img_index, img in enumerate(image_list):
                        try:
                            xref = img[0]
                            pix = fitz.Pixmap(doc, xref)
                            if pix.n - pix.alpha < 4:  # 支持的图像格式
                                img_data = pix.tobytes("png")
                                images.append({
                                    "index": img_index,
                                    "data": img_data,
                                    "width": pix.width,
                                    "height": pix.height
                                })
                            pix = None
                        except Exception as e:
                            self.logger.warning(f"图像提取失败: {e}")
                    
                    pages_data.append({
                        "page_number": page_num + 1,
                        "text": text,
                        "images": images
                    })
                    
        except Exception as e:
            self.logger.error(f"pymupdf提取失败: {e}")
        
        return pages_data
    
    def _ocr_image(self, image_data: bytes) -> str:
        """对图像进行OCR识别"""
        try:
            # 将bytes转换为PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为OpenCV格式进行预处理
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 图像预处理
            processed_image = self._preprocess_image(opencv_image)
            
            # OCR识别
            text = pytesseract.image_to_string(
                processed_image, 
                lang='chi_sim+eng',  # 中英文识别
                config='--psm 6'
            )
            
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"OCR识别失败: {e}")
            return ""
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理，提高OCR效果"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 去噪
        denoised = cv2.medianBlur(gray, 3)
        
        # 二值化
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return binary


class AutoDetectExtractor(BaseExtractor):
    """自动识别解析器"""
    
    async def extract(self, file_path: str) -> Dict[str, Any]:
        """自动识别文档类型并解析"""
        # 先用pdfplumber提取文本
        pages_data = self._extract_text_with_pdfplumber(file_path)
        
        # 合并所有页面文本
        full_text = " ".join([page["text"] for page in pages_data])
        
        # 识别文档类型
        doc_type = self._detect_document_type(full_text)
        self.logger.info(f"自动识别文档类型: {doc_type}")
        
        # 根据类型选择对应的提取器
        from services.pdf_parser import PDFParserService  # 避免循环导入
        
        parser_service = PDFParserService()
        if doc_type in parser_service.extractors and doc_type != 'auto':
            extractor = parser_service.extractors[doc_type]
            return await extractor.extract(file_path)
        
        # 默认通用提取
        return {
            "type": "general",
            "content": {
                "text": full_text,
                "pages": len(pages_data),
                "tables": sum([len(page.get("tables", [])) for page in pages_data])
            }
        }
    
    def _detect_document_type(self, text: str) -> str:
        """检测文档类型"""
        text_lower = text.lower()
        
        # 营养标签关键词
        nutrition_keywords = ['营养成分', '营养标签', '热量', '蛋白质', '脂肪', '碳水化合物', 
                              'nutrition facts', 'calories', 'protein', 'fat', 'carbohydrates']
        
        # 食谱关键词
        recipe_keywords = ['食谱', '制作方法', '烹饪步骤', '配料', '食材', '做法',
                          'recipe', 'ingredients', 'cooking', 'preparation']
        
        # 膳食指南关键词
        guide_keywords = ['膳食指南', '饮食建议', '营养指导', '健康饮食', 'dietary guidelines']
        
        # 统计关键词出现次数
        nutrition_count = sum([text_lower.count(kw) for kw in nutrition_keywords])
        recipe_count = sum([text_lower.count(kw) for kw in recipe_keywords])
        guide_count = sum([text_lower.count(kw) for kw in guide_keywords])
        
        # 返回得分最高的类型
        if nutrition_count >= recipe_count and nutrition_count >= guide_count:
            return 'nutrition_label'
        elif recipe_count >= guide_count:
            return 'recipe'
        elif guide_count > 0:
            return 'diet_guide'
        else:
            return 'general'


class NutritionLabelExtractor(BaseExtractor):
    """营养标签提取器"""
    
    async def extract(self, file_path: str) -> Dict[str, Any]:
        """提取营养标签信息"""
        # 文本提取
        pages_data = self._extract_text_with_pdfplumber(file_path)
        full_text = " ".join([page["text"] for page in pages_data])
        
        # 如果文本提取效果不好，尝试OCR
        if len(full_text.strip()) < 50:
            self.logger.info("文本提取不足，尝试OCR识别")
            pymupdf_data = self._extract_text_with_pymupdf(file_path)
            ocr_text = ""
            for page in pymupdf_data:
                for image in page.get("images", []):
                    ocr_text += self._ocr_image(image["data"]) + "\n"
            
            if ocr_text.strip():
                full_text = ocr_text
        
        # 提取营养信息
        nutrition_data = self._extract_nutrition_facts(full_text)
        food_info = self._extract_food_info(full_text)
        
        return {
            "type": "food",
            "food_info": food_info,
            "nutrition": nutrition_data,
            "raw_text": full_text,
            "tables": self._extract_nutrition_tables(pages_data)
        }
    
    def _extract_nutrition_facts(self, text: str) -> Dict[str, Any]:
        """提取营养成分"""
        nutrition = {}
        
        # 中文营养成分模式
        chinese_patterns = {
            'energy': r'(?:能量|热量)[：:\s]*(\d+(?:\.\d+)?)\s*(?:千?焦|kj|kcal|千?卡|大卡)',
            'calories': r'(?:热量|卡路里)[：:\s]*(\d+(?:\.\d+)?)\s*(?:kcal|千?卡|大卡)',
            'protein': r'蛋白质[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'fat': r'(?:脂肪|总脂肪)[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'saturated_fat': r'饱和脂肪[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'carbohydrates': r'(?:碳水化合物|糖类)[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'sugar': r'(?:糖|添加糖)[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'fiber': r'(?:膳食纤维|纤维)[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'sodium': r'钠[：:\s]*(\d+(?:\.\d+)?)\s*(?:mg|毫?克)',
            'potassium': r'钾[：:\s]*(\d+(?:\.\d+)?)\s*(?:mg|毫?克)',
            'calcium': r'钙[：:\s]*(\d+(?:\.\d+)?)\s*(?:mg|毫?克)',
            'iron': r'铁[：:\s]*(\d+(?:\.\d+)?)\s*(?:mg|毫?克)',
            'vitamin_c': r'维生素\s*c[：:\s]*(\d+(?:\.\d+)?)\s*(?:mg|毫?克)',
            'vitamin_a': r'维生素\s*a[：:\s]*(\d+(?:\.\d+)?)\s*(?:μg|微?克)'
        }
        
        # 英文营养成分模式
        english_patterns = {
            'calories': r'calories[：:\s]*(\d+(?:\.\d+)?)',
            'protein': r'protein[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'fat': r'total\s+fat[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'saturated_fat': r'saturated\s+fat[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'carbohydrates': r'(?:total\s+)?carbohydrate[s]?[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'sugar': r'(?:total\s+)?sugar[s]?[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'fiber': r'dietary\s+fiber[：:\s]*(\d+(?:\.\d+)?)\s*g',
            'sodium': r'sodium[：:\s]*(\d+(?:\.\d+)?)\s*mg'
        }
        
        # 合并模式
        all_patterns = {**chinese_patterns, **english_patterns}
        
        for nutrient, pattern in all_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                value = float(match.group(1))
                if nutrient not in nutrition or value > 0:  # 优先保存非零值
                    nutrition[nutrient] = value
        
        return nutrition
    
    def _extract_food_info(self, text: str) -> Dict[str, Any]:
        """提取食品基础信息"""
        food_info = {}
        
        # 食品名称提取（简化版）
        name_patterns = [
            r'(?:产品名称|食品名称|商品名称)[：:\s]*([^\n\r]+)',
            r'(?:product\s+name|food\s+name)[：:\s]*([^\n\r]+)'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                food_info['name'] = match.group(1).strip()
                break
        
        # 品牌提取
        brand_patterns = [
            r'(?:品牌|商标)[：:\s]*([^\n\r]+)',
            r'(?:brand)[：:\s]*([^\n\r]+)'
        ]
        
        for pattern in brand_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                food_info['brand'] = match.group(1).strip()
                break
        
        # 规格提取
        spec_patterns = [
            r'(?:规格|净含量|重量)[：:\s]*(\d+(?:\.\d+)?)\s*(?:g|kg|ml|l|克|千克|毫升|升)',
            r'(?:net\s+weight|weight)[：:\s]*(\d+(?:\.\d+)?)\s*(?:g|kg|oz|lb)'
        ]
        
        for pattern in spec_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                food_info['net_weight'] = match.group(1) + match.group(0).split()[-1]
                break
        
        return food_info
    
    def _extract_nutrition_tables(self, pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取营养表格数据"""
        all_tables = []
        
        for page in pages_data:
            tables = page.get("tables", [])
            for table in tables:
                if self._is_nutrition_table(table):
                    parsed_table = self._parse_nutrition_table(table)
                    if parsed_table:
                        all_tables.append(parsed_table)
        
        return all_tables
    
    def _is_nutrition_table(self, table: List[List[str]]) -> bool:
        """判断是否为营养表格"""
        if not table or len(table) < 2:
            return False
        
        # 检查表格内容是否包含营养相关关键词
        table_text = " ".join([" ".join(row) for row in table if row])
        nutrition_keywords = ['营养', '热量', '蛋白质', '脂肪', '碳水', 'calories', 'protein', 'fat']
        
        return any(keyword in table_text.lower() for keyword in nutrition_keywords)
    
    def _parse_nutrition_table(self, table: List[List[str]]) -> Optional[Dict[str, Any]]:
        """解析营养表格"""
        try:
            # 转换为DataFrame便于处理
            df = pd.DataFrame(table)
            df = df.dropna(how='all').fillna('')
            
            # 查找营养成分列
            nutrition_data = {}
            
            for index, row in df.iterrows():
                for col_idx, cell in enumerate(row):
                    if cell and any(keyword in cell for keyword in ['蛋白质', '脂肪', '碳水', 'protein', 'fat']):
                        # 尝试提取数值
                        if col_idx + 1 < len(row):
                            value_cell = row.iloc[col_idx + 1]
                            if value_cell:
                                nutrition_data[cell] = value_cell
            
            return nutrition_data if nutrition_data else None
            
        except Exception as e:
            self.logger.error(f"表格解析失败: {e}")
            return None


class RecipeExtractor(BaseExtractor):
    """食谱提取器"""
    
    async def extract(self, file_path: str) -> Dict[str, Any]:
        """提取食谱信息"""
        # 文本提取 
        pages_data = self._extract_text_with_pdfplumber(file_path)
        full_text = " ".join([page["text"] for page in pages_data])
        
        # 提取食谱各部分
        recipe_name = self._extract_recipe_name(full_text)
        ingredients = self._extract_ingredients(full_text)
        instructions = self._extract_instructions(full_text)
        nutrition = self._extract_recipe_nutrition(full_text)
        
        return {
            "type": "recipe",
            "recipe_info": {
                "name": recipe_name,
                "ingredients": ingredients,
                "instructions": instructions,
                "servings": self._extract_servings(full_text),
                "prep_time": self._extract_prep_time(full_text),
                "cook_time": self._extract_cook_time(full_text)
            },
            "nutrition": nutrition,
            "raw_text": full_text
        }
    
    def _extract_recipe_name(self, text: str) -> str:
        """提取食谱名称"""
        # 简化的标题提取逻辑
        lines = text.split('\n')
        for line in lines[:5]:  # 检查前5行
            if line.strip() and len(line.strip()) < 50:
                return line.strip()
        return "未识别的食谱"
    
    def _extract_ingredients(self, text: str) -> List[Dict[str, str]]:
        """提取食材列表"""
        ingredients = []
        
        # 查找食材部分
        ingredient_section = re.search(r'(?:食材|配料|原料|ingredients)[：:\s]*\n(.*?)(?:\n\n|制作|步骤|instructions)', 
                                       text, re.IGNORECASE | re.DOTALL)
        
        if ingredient_section:
            ingredient_text = ingredient_section.group(1)
            lines = ingredient_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 尝试分离食材和用量
                    parts = re.split(r'[：:\s]+', line, 1)
                    if len(parts) >= 2:
                        ingredients.append({
                            "name": parts[0].strip(),
                            "amount": parts[1].strip()
                        })
                    else:
                        ingredients.append({
                            "name": line,
                            "amount": ""
                        })
        
        return ingredients
    
    def _extract_instructions(self, text: str) -> List[str]:
        """提取制作步骤"""
        instructions = []
        
        # 查找步骤部分
        instruction_section = re.search(r'(?:制作|步骤|做法|方法|instructions)[：:\s]*\n(.*?)(?:\n\n|营养|tips)', 
                                        text, re.IGNORECASE | re.DOTALL)
        
        if instruction_section:
            instruction_text = instruction_section.group(1)
            
            # 按数字序号分割步骤
            steps = re.split(r'\n(?=\d+[\.、])', instruction_text)
            
            for step in steps:
                step = step.strip()
                if step:
                    # 移除序号
                    cleaned_step = re.sub(r'^\d+[\.、]\s*', '', step)
                    if cleaned_step:
                        instructions.append(cleaned_step.strip())
        
        return instructions
    
    def _extract_servings(self, text: str) -> str:
        """提取份数"""
        patterns = [
            r'(?:份数|人份|servings)[：:\s]*(\d+)',
            r'(\d+)\s*(?:人份|份)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""
    
    def _extract_prep_time(self, text: str) -> str:
        """提取准备时间"""
        patterns = [
            r'(?:准备时间|prep\s+time)[：:\s]*(\d+)\s*(?:分钟|minutes|min)',
            r'准备[：:\s]*(\d+)\s*(?:分钟|minutes|min)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}分钟"
        
        return ""
    
    def _extract_cook_time(self, text: str) -> str:
        """提取烹饪时间"""
        patterns = [
            r'(?:烹饪时间|cook\s+time)[：:\s]*(\d+)\s*(?:分钟|minutes|min)',
            r'烹饪[：:\s]*(\d+)\s*(?:分钟|minutes|min)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}分钟"
        
        return ""
    
    def _extract_recipe_nutrition(self, text: str) -> Dict[str, Any]:
        """提取食谱营养信息"""
        # 复用营养标签提取器的逻辑
        nutrition_extractor = NutritionLabelExtractor()
        return nutrition_extractor._extract_nutrition_facts(text)


class DietGuideExtractor(BaseExtractor):
    """膳食指南提取器"""
    
    async def extract(self, file_path: str) -> Dict[str, Any]:
        """提取膳食指南信息"""
        pages_data = self._extract_text_with_pdfplumber(file_path)
        full_text = " ".join([page["text"] for page in pages_data])
        
        # 提取指南结构
        guide_structure = self._extract_guide_structure(full_text)
        recommendations = self._extract_recommendations(full_text)
        
        return {
            "type": "diet_guide",
            "guide_info": {
                "title": self._extract_guide_title(full_text),
                "structure": guide_structure,
                "recommendations": recommendations,
                "target_group": self._extract_target_group(full_text)
            },
            "raw_text": full_text
        }
    
    def _extract_guide_title(self, text: str) -> str:
        """提取指南标题"""
        lines = text.split('\n')
        for line in lines[:3]:
            if line.strip() and '指南' in line:
                return line.strip()
        return "膳食指南"
    
    def _extract_guide_structure(self, text: str) -> List[Dict[str, str]]:
        """提取指南结构"""
        # 简化的章节提取
        sections = []
        
        # 查找编号章节
        section_pattern = r'(?:第\s*\d+\s*章|第\s*\d+\s*节|\d+\.)\s*([^\n]+)'
        matches = re.finditer(section_pattern, text)
        
        for match in matches:
            sections.append({
                "title": match.group(1).strip(),
                "position": match.start()
            })
        
        return sections
    
    def _extract_recommendations(self, text: str) -> List[Dict[str, str]]:
        """提取建议事项"""
        recommendations = []
        
        # 查找建议关键词后的内容
        recommendation_patterns = [
            r'建议[：:\s]*([^\n\.。]+)',
            r'推荐[：:\s]*([^\n\.。]+)',
            r'应该[：:\s]*([^\n\.。]+)'
        ]
        
        for pattern in recommendation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                recommendations.append({
                    "type": "recommendation",
                    "content": match.group(1).strip()
                })
        
        return recommendations
    
    def _extract_target_group(self, text: str) -> str:
        """提取目标人群"""
        target_patterns = [
            r'(?:适用于|针对|目标人群)[：:\s]*([^\n]+)',
            r'(?:儿童|成人|老年人|孕妇|哺乳期)'
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip() if len(match.groups()) > 0 else match.group(0)
        
        return "一般人群"


class FoodInfoExtractor(BaseExtractor):
    """食品信息提取器"""
    
    async def extract(self, file_path: str) -> Dict[str, Any]:
        """提取一般食品信息"""
        pages_data = self._extract_text_with_pdfplumber(file_path)
        full_text = " ".join([page["text"] for page in pages_data])
        
        # 综合提取
        food_info = self._extract_comprehensive_food_info(full_text)
        nutrition = self._extract_any_nutrition_info(full_text)
        
        return {
            "type": "food",
            "food_info": food_info,
            "nutrition": nutrition,
            "raw_text": full_text
        }
    
    def _extract_comprehensive_food_info(self, text: str) -> Dict[str, Any]:
        """综合提取食品信息"""
        info = {}
        
        # 使用jieba分词帮助识别关键信息
        words = jieba.lcut(text)
        
        # 食品类别识别
        food_categories = ['肉类', '蔬菜', '水果', '谷物', '奶制品', '坚果', '海鲜', '饮料']
        for category in food_categories:
            if category in text:
                info['category'] = category
                break
        
        # 基础信息提取（复用之前的逻辑）
        nutrition_extractor = NutritionLabelExtractor()
        basic_info = nutrition_extractor._extract_food_info(text)
        info.update(basic_info)
        
        return info
    
    def _extract_any_nutrition_info(self, text: str) -> Dict[str, Any]:
        """提取任何可能的营养信息"""
        # 复用营养标签提取器
        nutrition_extractor = NutritionLabelExtractor()
        return nutrition_extractor._extract_nutrition_facts(text) 