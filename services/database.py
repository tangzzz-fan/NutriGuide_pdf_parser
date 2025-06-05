"""
Database Service - MongoDB 数据库操作服务
处理解析结果的存储、查询和管理
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson import ObjectId
import json

from config.settings import get_settings
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


class DatabaseService:
    """MongoDB 数据库服务"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.collections = {
            'parsing_results': 'parsing_results',
            'batch_operations': 'batch_operations',
            'user_uploads': 'user_uploads',
            'parsing_stats': 'parsing_stats'
        }
    
    async def connect(self):
        """连接到 MongoDB"""
        try:
            # 使用环境变量或默认值
            mongo_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
            db_name = os.getenv('MONGODB_DATABASE', 'nutriguide_pdf')
            
            self.client = AsyncIOMotorClient(mongo_url)
            self.db = self.client[db_name]
            
            # 测试连接
            await self.client.admin.command('ping')
            logger.info(f"MongoDB 连接成功: {db_name}")
            
            # 创建索引
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"MongoDB 连接失败: {e}")
            raise
    
    async def disconnect(self):
        """断开 MongoDB 连接"""
        if self.client:
            self.client.close()
            logger.info("MongoDB 连接已关闭")
    
    async def check_connection(self) -> bool:
        """检查数据库连接状态"""
        try:
            if not self.client:
                return False
            await self.client.admin.command('ping')
            return True
        except Exception:
            return False
    
    async def _create_indexes(self):
        """创建数据库索引"""
        try:
            # parsing_results 集合索引
            collection = self.db[self.collections['parsing_results']]
            await collection.create_index("file_id", unique=True)
            await collection.create_index("created_at")
            await collection.create_index("status")
            await collection.create_index("parsing_type")
            
            # batch_operations 集合索引
            batch_collection = self.db[self.collections['batch_operations']]
            await batch_collection.create_index("batch_id", unique=True)
            await batch_collection.create_index("created_at")
            
            # user_uploads 集合索引
            uploads_collection = self.db[self.collections['user_uploads']]
            await uploads_collection.create_index("user_id")
            await uploads_collection.create_index("created_at")
            
            logger.info("数据库索引创建完成")
            
        except Exception as e:
            logger.warning(f"索引创建失败: {e}")
    
    async def save_parsing_result(
        self,
        file_id: str,
        filename: str,
        parsing_type: str,
        result: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        user_id: Optional[str] = None
    ) -> str:
        """保存解析结果"""
        try:
            document = {
                "file_id": file_id,
                "filename": filename,
                "parsing_type": parsing_type,
                "status": status,
                "result": result,
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "error_message": None,
                "processing_time": None,
                "quality_score": None
            }
            
            collection = self.db[self.collections['parsing_results']]
            insert_result = await collection.insert_one(document)
            
            document_id = str(insert_result.inserted_id)
            logger.info(f"解析结果已保存: {document_id}")
            
            return document_id
            
        except DuplicateKeyError:
            logger.warning(f"文件 {file_id} 已存在")
            raise ValueError(f"文件 {file_id} 已存在")
        except Exception as e:
            logger.error(f"保存解析结果失败: {e}")
            raise
    
    async def update_parsing_result(
        self,
        document_id: str,
        result: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        processing_time: Optional[float] = None,
        quality_score: Optional[float] = None
    ) -> bool:
        """更新解析结果"""
        try:
            update_data = {
                "updated_at": datetime.utcnow()
            }
            
            if result is not None:
                update_data["result"] = result
            if status is not None:
                update_data["status"] = status
            if error_message is not None:
                update_data["error_message"] = error_message
            if processing_time is not None:
                update_data["processing_time"] = processing_time
            if quality_score is not None:
                update_data["quality_score"] = quality_score
            
            collection = self.db[self.collections['parsing_results']]
            update_result = await collection.update_one(
                {"_id": ObjectId(document_id)},
                {"$set": update_data}
            )
            
            if update_result.modified_count > 0:
                logger.info(f"解析结果已更新: {document_id}")
                return True
            else:
                logger.warning(f"未找到文档或无需更新: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新解析结果失败: {e}")
            raise
    
    async def get_parsing_result(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取解析结果"""
        try:
            collection = self.db[self.collections['parsing_results']]
            result = await collection.find_one({"_id": ObjectId(document_id)})
            
            if result:
                result["_id"] = str(result["_id"])
                return result
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取解析结果失败: {e}")
            return None
    
    async def get_parsing_history(
        self,
        limit: int = 10,
        offset: int = 0,
        status: Optional[str] = None,
        parsing_type: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取解析历史"""
        try:
            collection = self.db[self.collections['parsing_results']]
            
            # 构建查询条件
            query = {}
            if status:
                query["status"] = status
            if parsing_type:
                query["parsing_type"] = parsing_type
            if user_id:
                query["user_id"] = user_id
            
            # 获取总数
            total = await collection.count_documents(query)
            
            # 获取分页数据
            cursor = collection.find(query).sort("created_at", -1).skip(offset).limit(limit)
            results = []
            
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                # 只返回必要字段
                results.append({
                    "document_id": doc["_id"],
                    "filename": doc["filename"],
                    "parsing_type": doc["parsing_type"],
                    "status": doc["status"],
                    "created_at": doc["created_at"],
                    "quality_score": doc.get("quality_score"),
                    "processing_time": doc.get("processing_time")
                })
            
            return {
                "results": results,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"获取解析历史失败: {e}")
            raise
    
    async def delete_parsing_result(self, document_id: str) -> bool:
        """删除解析结果"""
        try:
            collection = self.db[self.collections['parsing_results']]
            delete_result = await collection.delete_one({"_id": ObjectId(document_id)})
            
            if delete_result.deleted_count > 0:
                logger.info(f"解析结果已删除: {document_id}")
                return True
            else:
                logger.warning(f"未找到要删除的文档: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"删除解析结果失败: {e}")
            raise
    
    async def save_batch_operation(
        self,
        batch_id: str,
        files_info: List[Dict[str, Any]],
        parsing_type: str,
        user_id: Optional[str] = None
    ) -> str:
        """保存批量操作记录"""
        try:
            document = {
                "batch_id": batch_id,
                "files_info": files_info,
                "parsing_type": parsing_type,
                "user_id": user_id,
                "status": "pending",
                "total_files": len(files_info),
                "completed_files": 0,
                "failed_files": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            collection = self.db[self.collections['batch_operations']]
            insert_result = await collection.insert_one(document)
            
            operation_id = str(insert_result.inserted_id)
            logger.info(f"批量操作记录已保存: {operation_id}")
            
            return operation_id
            
        except Exception as e:
            logger.error(f"保存批量操作记录失败: {e}")
            raise
    
    async def update_batch_operation(
        self,
        batch_id: str,
        completed_files: Optional[int] = None,
        failed_files: Optional[int] = None,
        status: Optional[str] = None
    ) -> bool:
        """更新批量操作状态"""
        try:
            update_data = {
                "updated_at": datetime.utcnow()
            }
            
            if completed_files is not None:
                update_data["completed_files"] = completed_files
            if failed_files is not None:
                update_data["failed_files"] = failed_files
            if status is not None:
                update_data["status"] = status
            
            collection = self.db[self.collections['batch_operations']]
            update_result = await collection.update_one(
                {"batch_id": batch_id},
                {"$set": update_data}
            )
            
            return update_result.modified_count > 0
            
        except Exception as e:
            logger.error(f"更新批量操作状态失败: {e}")
            raise
    
    async def get_batch_operation(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """获取批量操作状态"""
        try:
            collection = self.db[self.collections['batch_operations']]
            result = await collection.find_one({"batch_id": batch_id})
            
            if result:
                result["_id"] = str(result["_id"])
                return result
            else:
                return None
                
        except Exception as e:
            logger.error(f"获取批量操作状态失败: {e}")
            return None
    
    async def cleanup_old_records(self, days: int = 30) -> int:
        """清理旧记录"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # 清理解析结果
            collection = self.db[self.collections['parsing_results']]
            delete_result = await collection.delete_many({
                "created_at": {"$lt": cutoff_date},
                "status": {"$in": ["completed", "failed"]}
            })
            
            deleted_count = delete_result.deleted_count
            logger.info(f"清理了 {deleted_count} 条旧记录")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")
            raise
    
    async def get_parsing_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取解析统计信息"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            collection = self.db[self.collections['parsing_results']]
            
            # 聚合统计
            pipeline = [
                {"$match": {"created_at": {"$gte": start_date}}},
                {"$group": {
                    "_id": {
                        "status": "$status",
                        "parsing_type": "$parsing_type"
                    },
                    "count": {"$sum": 1},
                    "avg_quality": {"$avg": "$quality_score"},
                    "avg_processing_time": {"$avg": "$processing_time"}
                }}
            ]
            
            cursor = collection.aggregate(pipeline)
            stats = []
            
            async for doc in cursor:
                stats.append(doc)
            
            # 计算总体统计
            total_docs = await collection.count_documents({
                "created_at": {"$gte": start_date}
            })
            
            return {
                "period_days": days,
                "total_documents": total_docs,
                "detailed_stats": stats,
                "generated_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise 