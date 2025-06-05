#!/usr/bin/env python3
"""
调试数据库问题
"""

import asyncio
import os
from services.database import DatabaseService
from bson import ObjectId

# 设置环境变量
os.environ['MONGODB_URL'] = "mongodb://admin:admin123@localhost:27017/nutriguide_dev?authSource=admin"
os.environ['MONGODB_DATABASE'] = "nutriguide_dev"

async def debug_database_issue():
    """调试数据库问题"""
    print("🔍 调试数据库问题...")
    
    # 初始化数据库服务
    db_service = DatabaseService()
    await db_service.connect()
    
    try:
        # 直接查询数据库
        collection = db_service.db[db_service.collections['parsing_results']]
        
        print("\n📊 数据库统计:")
        total_docs = await collection.count_documents({})
        print(f"   总文档数: {total_docs}")
        
        # 检查文档结构
        print("\n📋 检查文档结构:")
        cursor = collection.find({}).limit(5)
        
        async for doc in cursor:
            print(f"\n📄 文档 ID: {doc['_id']}")
            print(f"   字段: {list(doc.keys())}")
            
            # 检查必需字段
            required_fields = ['filename', 'parsing_type', 'status', 'created_at']
            missing_fields = []
            
            for field in required_fields:
                if field not in doc:
                    missing_fields.append(field)
                else:
                    value = doc[field]
                    if value is None:
                        missing_fields.append(f"{field} (None)")
                    else:
                        print(f"   {field}: {value} ({type(value).__name__})")
            
            if missing_fields:
                print(f"   ❌ 缺少字段: {missing_fields}")
            else:
                print(f"   ✅ 所有必需字段存在")
        
        # 测试 get_parsing_history 方法
        print("\n🧪 测试 get_parsing_history 方法:")
        try:
            history = await db_service.get_parsing_history(limit=3)
            print(f"✅ 方法调用成功")
            print(f"   返回类型: {type(history)}")
            print(f"   返回字段: {list(history.keys()) if isinstance(history, dict) else 'Not a dict'}")
            
            if isinstance(history, dict) and 'results' in history:
                results = history['results']
                print(f"   结果数量: {len(results)}")
                
                for i, result in enumerate(results[:2]):
                    print(f"   结果 {i+1}: {result}")
            
        except Exception as e:
            print(f"❌ 方法调用失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 检查是否有损坏的文档
        print("\n🔍 检查损坏的文档:")
        cursor = collection.find({})
        corrupted_count = 0
        
        async for doc in cursor:
            try:
                # 尝试访问所有字段
                doc_id = str(doc["_id"])
                filename = doc.get("filename")
                parsing_type = doc.get("parsing_type")
                status = doc.get("status")
                created_at = doc.get("created_at")
                
                if not filename or not parsing_type or not status:
                    print(f"   ⚠️  文档 {doc_id} 有空字段:")
                    print(f"      filename: {filename}")
                    print(f"      parsing_type: {parsing_type}")
                    print(f"      status: {status}")
                    corrupted_count += 1
                    
            except Exception as e:
                print(f"   ❌ 文档 {doc.get('_id', 'unknown')} 损坏: {e}")
                corrupted_count += 1
        
        print(f"\n📊 损坏文档统计: {corrupted_count} / {total_docs}")
        
        # 如果有损坏的文档，提供修复建议
        if corrupted_count > 0:
            print("\n💡 修复建议:")
            print("   1. 删除损坏的文档")
            print("   2. 或者修复缺失的字段")
            
            # 询问是否要修复
            print("\n🔧 是否要自动修复损坏的文档？")
            print("   这将删除缺少必需字段的文档")
            
            # 自动修复（在测试环境中）
            if os.getenv('ENVIRONMENT') == 'development':
                print("   开发环境，自动修复...")
                await fix_corrupted_documents(collection)
        
    finally:
        await db_service.disconnect()


async def fix_corrupted_documents(collection):
    """修复损坏的文档"""
    print("🔧 开始修复损坏的文档...")
    
    # 删除缺少必需字段的文档
    delete_result = await collection.delete_many({
        "$or": [
            {"filename": {"$exists": False}},
            {"filename": None},
            {"parsing_type": {"$exists": False}},
            {"parsing_type": None},
            {"status": {"$exists": False}},
            {"status": None},
            {"created_at": {"$exists": False}},
            {"created_at": None}
        ]
    })
    
    print(f"✅ 删除了 {delete_result.deleted_count} 个损坏的文档")
    
    # 为缺少可选字段的文档添加默认值
    from datetime import datetime
    
    update_result = await collection.update_many(
        {"quality_score": {"$exists": False}},
        {"$set": {"quality_score": None}}
    )
    print(f"✅ 为 {update_result.modified_count} 个文档添加了默认 quality_score")
    
    update_result = await collection.update_many(
        {"processing_time": {"$exists": False}},
        {"$set": {"processing_time": None}}
    )
    print(f"✅ 为 {update_result.modified_count} 个文档添加了默认 processing_time")
    
    update_result = await collection.update_many(
        {"updated_at": {"$exists": False}},
        {"$set": {"updated_at": datetime.utcnow()}}
    )
    print(f"✅ 为 {update_result.modified_count} 个文档添加了默认 updated_at")


async def test_fixed_method():
    """测试修复后的方法"""
    print("\n🧪 测试修复后的方法...")
    
    db_service = DatabaseService()
    await db_service.connect()
    
    try:
        history = await db_service.get_parsing_history(limit=5)
        print(f"✅ get_parsing_history 调用成功")
        print(f"   总记录数: {history.get('total', 0)}")
        print(f"   返回记录数: {len(history.get('results', []))}")
        
        for i, result in enumerate(history.get('results', [])[:3]):
            print(f"   记录 {i+1}: {result.get('filename')} - {result.get('status')}")
        
    except Exception as e:
        print(f"❌ 方法调用仍然失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db_service.disconnect()


if __name__ == "__main__":
    print("🚀 开始调试数据库问题...")
    
    asyncio.run(debug_database_issue())
    asyncio.run(test_fixed_method())
