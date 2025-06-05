#!/usr/bin/env python3
"""
数据库完整性验证脚本
直接连接 MongoDB 验证数据存储是否正确
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import sys

# MongoDB 配置
MONGODB_URL = "mongodb://admin:admin123@localhost:27017/nutriguide_dev?authSource=admin"
MONGODB_DATABASE = "nutriguide_dev"

class DatabaseTester:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def connect(self):
        """连接数据库"""
        print("🔌 连接 MongoDB...")
        try:
            self.client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.client[MONGODB_DATABASE]
            
            # 测试连接
            await self.client.admin.command('ping')
            print("✅ MongoDB 连接成功")
            return True
        except Exception as e:
            print(f"❌ MongoDB 连接失败: {e}")
            return False
    
    async def test_collections_exist(self):
        """测试集合是否存在"""
        print("\n📚 检查集合存在性...")
        
        try:
            collections = await self.db.list_collection_names()
            print(f"✅ 找到 {len(collections)} 个集合:")
            
            expected_collections = ['parsing_results', 'batch_operations', 'user_uploads', 'parsing_stats']
            
            for collection in expected_collections:
                if collection in collections:
                    print(f"   ✅ {collection}")
                else:
                    print(f"   ⚠️ {collection} (不存在，但会在首次使用时创建)")
            
            return True
        except Exception as e:
            print(f"❌ 检查集合失败: {e}")
            return False
    
    async def test_parsing_results(self):
        """测试解析结果数据"""
        print("\n📄 验证解析结果数据...")
        
        try:
            collection = self.db['parsing_results']
            
            # 获取所有记录
            cursor = collection.find({}).sort("created_at", -1)
            documents = await cursor.to_list(length=10)
            
            print(f"✅ 找到 {len(documents)} 条解析记录")
            
            # 验证每个文档的结构
            valid_documents = 0
            for i, doc in enumerate(documents):
                print(f"\n   📋 记录 {i+1}:")
                print(f"      ID: {doc.get('_id')}")
                print(f"      文件名: {doc.get('filename', 'N/A')}")
                print(f"      文件ID: {doc.get('file_id', 'N/A')}")
                print(f"      解析类型: {doc.get('parsing_type', 'N/A')}")
                print(f"      状态: {doc.get('status', 'N/A')}")
                print(f"      创建时间: {doc.get('created_at', 'N/A')}")
                
                # 验证必需字段
                required_fields = ['file_id', 'filename', 'parsing_type', 'status', 'created_at']
                missing_fields = [field for field in required_fields if field not in doc]
                
                if missing_fields:
                    print(f"      ⚠️ 缺少字段: {missing_fields}")
                else:
                    print(f"      ✅ 必需字段完整")
                    valid_documents += 1
                
                # 检查解析结果
                if doc.get('result'):
                    result = doc['result']
                    print(f"      📊 解析结果:")
                    print(f"         质量评分: {result.get('quality_score', 'N/A')}")
                    print(f"         解析状态: {result.get('status', 'N/A')}")
                    
                    if 'basic_info' in result:
                        basic = result['basic_info']
                        print(f"         文件大小: {basic.get('file_size', 'N/A')} bytes")
                        print(f"         页数: {basic.get('page_count', 'N/A')}")
                    
                    if 'extracted_data' in result:
                        extracted = result['extracted_data']
                        print(f"         数据类型: {extracted.get('type', 'N/A')}")
                        
                        # 检查营养数据
                        if extracted.get('nutrition'):
                            nutrition = extracted['nutrition']
                            nutrition_count = len(nutrition) if isinstance(nutrition, dict) else 0
                            print(f"         营养成分: {nutrition_count} 项")
                        
                        # 检查食谱数据
                        if extracted.get('recipe_info'):
                            recipe = extracted['recipe_info']
                            ingredients_count = len(recipe.get('ingredients', []))
                            print(f"         食谱配料: {ingredients_count} 项")
                else:
                    print(f"      ⚠️ 无解析结果数据")
            
            print(f"\n✅ 有效文档: {valid_documents}/{len(documents)}")
            return valid_documents == len(documents)
            
        except Exception as e:
            print(f"❌ 验证解析结果失败: {e}")
            return False
    
    async def test_data_consistency(self):
        """测试数据一致性"""
        print("\n🔍 验证数据一致性...")
        
        try:
            collection = self.db['parsing_results']
            
            # 统计不同状态的文档
            pipeline = [
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
            
            cursor = collection.aggregate(pipeline)
            status_stats = {}
            async for stat in cursor:
                status_stats[stat['_id']] = stat['count']
            
            print("📊 状态分布:")
            for status, count in status_stats.items():
                print(f"   {status}: {count} 条记录")
            
            # 检查时间戳
            recent_count = await collection.count_documents({
                "created_at": {"$gte": datetime.utcnow() - timedelta(hours=1)}
            })
            print(f"📅 最近1小时内的记录: {recent_count} 条")
            
            # 检查是否有异常数据
            no_result_count = await collection.count_documents({
                "$or": [
                    {"result": {"$exists": False}},
                    {"result": None}
                ],
                "status": "completed"
            })
            
            if no_result_count > 0:
                print(f"⚠️ 发现 {no_result_count} 条已完成但无结果的记录")
                return False
            else:
                print("✅ 数据一致性检查通过")
                return True
            
        except Exception as e:
            print(f"❌ 数据一致性检查失败: {e}")
            return False
    
    async def test_indexes(self):
        """测试索引"""
        print("\n🏗️ 验证数据库索引...")
        
        try:
            collection = self.db['parsing_results']
            indexes = await collection.list_indexes().to_list(length=None)
            
            print(f"✅ 找到 {len(indexes)} 个索引:")
            for index in indexes:
                name = index.get('name', 'unknown')
                keys = list(index.get('key', {}).keys())
                print(f"   📋 {name}: {keys}")
            
            # 检查关键索引是否存在
            index_names = [idx.get('name', '') for idx in indexes]
            expected_indexes = ['file_id_1', 'status_1', 'created_at_1']
            
            missing_indexes = []
            for expected in expected_indexes:
                if expected not in index_names:
                    missing_indexes.append(expected)
            
            if missing_indexes:
                print(f"⚠️ 缺少索引: {missing_indexes}")
                return False
            else:
                print("✅ 关键索引完整")
                return True
            
        except Exception as e:
            print(f"❌ 索引验证失败: {e}")
            return False
    
    async def test_query_performance(self):
        """测试查询性能"""
        print("\n⚡ 测试查询性能...")
        
        try:
            collection = self.db['parsing_results']
            
            # 测试按状态查询
            start_time = datetime.utcnow()
            completed_docs = await collection.find({"status": "completed"}).to_list(length=None)
            query_time = (datetime.utcnow() - start_time).total_seconds()
            
            print(f"✅ 状态查询: 找到 {len(completed_docs)} 条记录，耗时 {query_time:.3f} 秒")
            
            # 测试时间范围查询
            start_time = datetime.utcnow()
            recent_docs = await collection.find({
                "created_at": {"$gte": datetime.utcnow() - timedelta(days=1)}
            }).to_list(length=None)
            query_time = (datetime.utcnow() - start_time).total_seconds()
            
            print(f"✅ 时间查询: 找到 {len(recent_docs)} 条记录，耗时 {query_time:.3f} 秒")
            
            # 如果查询时间过长，提示优化
            if query_time > 1.0:
                print("⚠️ 查询时间较长，可能需要优化索引")
                return False
            else:
                print("✅ 查询性能良好")
                return True
            
        except Exception as e:
            print(f"❌ 查询性能测试失败: {e}")
            return False
    
    async def generate_summary_report(self):
        """生成汇总报告"""
        print("\n📋 生成数据库状态报告...")
        
        try:
            collection = self.db['parsing_results']
            
            # 基本统计
            total_count = await collection.count_documents({})
            completed_count = await collection.count_documents({"status": "completed"})
            failed_count = await collection.count_documents({"status": "failed"})
            
            # 最新记录
            latest_doc = await collection.find_one({}, sort=[("created_at", -1)])
            oldest_doc = await collection.find_one({}, sort=[("created_at", 1)])
            
            # 平均质量评分
            pipeline = [
                {"$match": {"result.quality_score": {"$exists": True}}},
                {"$group": {
                    "_id": None,
                    "avg_quality": {"$avg": "$result.quality_score"},
                    "max_quality": {"$max": "$result.quality_score"},
                    "min_quality": {"$min": "$result.quality_score"}
                }}
            ]
            
            quality_stats = None
            async for stat in collection.aggregate(pipeline):
                quality_stats = stat
            
            print("\n" + "="*50)
            print("📊 数据库状态汇总报告")
            print("="*50)
            print(f"📈 总记录数: {total_count}")
            print(f"✅ 完成记录: {completed_count}")
            print(f"❌ 失败记录: {failed_count}")
            print(f"📊 成功率: {(completed_count/total_count)*100:.1f}%" if total_count > 0 else "N/A")
            
            if latest_doc:
                print(f"📅 最新记录: {latest_doc.get('created_at', 'N/A')}")
            if oldest_doc:
                print(f"📅 最早记录: {oldest_doc.get('created_at', 'N/A')}")
            
            if quality_stats:
                print(f"⭐ 平均质量: {quality_stats.get('avg_quality', 0):.2f}")
                print(f"⭐ 最高质量: {quality_stats.get('max_quality', 0):.2f}")
                print(f"⭐ 最低质量: {quality_stats.get('min_quality', 0):.2f}")
            
            print("="*50)
            
            return True
            
        except Exception as e:
            print(f"❌ 生成报告失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.client:
            self.client.close()
            print("🔌 数据库连接已关闭")

async def main():
    """主测试函数"""
    print("🧪 开始数据库完整性验证")
    print("=" * 60)
    
    tester = DatabaseTester()
    
    try:
        # 连接数据库
        if not await tester.connect():
            return False
        
        # 运行各项测试
        tests = [
            ("集合存在性", tester.test_collections_exist()),
            ("解析结果数据", tester.test_parsing_results()),
            ("数据一致性", tester.test_data_consistency()),
            ("数据库索引", tester.test_indexes()),
            ("查询性能", tester.test_query_performance())
        ]
        
        results = []
        for test_name, test_coro in tests:
            print(f"\n🔍 执行测试: {test_name}")
            try:
                result = await test_coro
                results.append((test_name, result))
                status = "✅ 通过" if result else "❌ 失败"
                print(f"   {status}")
            except Exception as e:
                print(f"   ❌ 异常: {e}")
                results.append((test_name, False))
        
        # 生成汇总报告
        await tester.generate_summary_report()
        
        # 输出最终结果
        print("\n" + "=" * 60)
        print("🎯 验证结果汇总")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        print(f"总测试数: {total}")
        print(f"通过测试: {passed}")
        print(f"失败测试: {total - passed}")
        print(f"成功率: {(passed/total)*100:.1f}%")
        
        print("\n📋 详细结果:")
        for test_name, result in results:
            status = "✅" if result else "❌"
            print(f"   {status} {test_name}")
        
        if passed == total:
            print("\n🎉 数据库完整性验证完全通过！")
            print("✅ PDF 数据已正确存储到 MongoDB")
            print("✅ 数据结构完整，索引正常")
            print("✅ 查询性能良好")
            return True
        else:
            print(f"\n⚠️ 有 {total - passed} 项验证失败")
            return False
            
    except Exception as e:
        print(f"❌ 验证过程异常: {e}")
        return False
    finally:
        await tester.disconnect()

if __name__ == "__main__":
    asyncio.run(main()) 