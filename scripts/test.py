#!/usr/bin/env python3
"""
PDF解析服务测试脚本
用于验证服务的基本功能
"""

import asyncio
import httpx
import json
import sys
import time
from pathlib import Path

# API基础URL
API_BASE = "http://localhost:7800"

async def test_health():
    """测试健康检查接口"""
    print("🏥 测试健康检查...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 健康检查通过: {data['status']}")
                print(f"📊 服务状态: {data['services']}")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

async def test_parsing_status():
    """测试解析状态查询"""
    print("\n📋 测试解析历史查询...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE}/parse/history?limit=5")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 历史记录查询成功: 共 {data['total']} 条记录")
                for item in data['items'][:3]:  # 显示前3条
                    print(f"  📄 {item.get('filename', 'unknown')} - {item.get('status', 'unknown')}")
                return True
            else:
                print(f"❌ 查询失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            return False

async def test_file_upload():
    """测试文件上传（模拟）"""
    print("\n📤 测试文件上传接口...")
    
    # 创建一个简单的测试文件（如果不存在的话）
    test_file_path = Path("test_file.txt")
    if not test_file_path.exists():
        test_file_path.write_text("这是一个测试文件，用于验证上传功能")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 注意：这里只是测试接口是否存在，实际PDF解析需要真实的PDF文件
            files = {"file": ("test.txt", test_file_path.read_bytes(), "text/plain")}
            data = {"parsing_type": "auto"}
            
            response = await client.post(f"{API_BASE}/parse/sync", files=files, data=data)
            
            if response.status_code in [200, 400, 413]:  # 200=成功, 400=格式错误, 413=文件太大
                if response.status_code == 200:
                    result = response.json()
                    print(f"✅ 文件上传成功: {result.get('message', 'Unknown')}")
                elif response.status_code == 400:
                    print("⚠️ 文件格式错误（预期行为，测试文件不是PDF）")
                elif response.status_code == 413:
                    print("⚠️ 文件太大（预期行为）")
                return True
            else:
                print(f"❌ 上传失败: {response.status_code}")
                print(f"响应: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 上传测试失败: {e}")
            return False
        finally:
            # 清理测试文件
            if test_file_path.exists():
                test_file_path.unlink()

async def test_async_endpoint():
    """测试异步解析接口"""
    print("\n⚡ 测试异步解析接口...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 创建临时测试文件
            test_file_path = Path("async_test.txt")
            test_file_path.write_text("异步解析测试文件")
            
            files = {"file": ("async_test.txt", test_file_path.read_bytes(), "text/plain")}
            data = {"parsing_type": "auto"}
            
            response = await client.post(f"{API_BASE}/parse/async", files=files, data=data)
            
            if response.status_code in [200, 202, 400]:
                if response.status_code == 202:
                    result = response.json()
                    print(f"✅ 异步任务已提交: 任务ID {result.get('task_id', 'unknown')}")
                elif response.status_code == 400:
                    print("⚠️ 文件格式错误（预期行为，测试文件不是PDF）")
                return True
            else:
                print(f"❌ 异步接口测试失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 异步接口测试失败: {e}")
            return False
        finally:
            if test_file_path.exists():
                test_file_path.unlink()

async def test_api_docs():
    """测试API文档接口"""
    print("\n📚 测试API文档...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE}/docs")
            if response.status_code == 200:
                print("✅ API文档可访问")
                return True
            else:
                print(f"❌ API文档访问失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API文档测试失败: {e}")
            return False

async def main():
    """主测试函数"""
    print("🧪 开始测试 NutriGuide PDF解析服务")
    print("=" * 50)
    
    # 等待服务启动
    print("⏳ 等待服务启动...")
    await asyncio.sleep(2)
    
    tests = [
        ("健康检查", test_health),
        ("API文档", test_api_docs),
        ("解析历史", test_parsing_status),
        ("同步上传", test_file_upload),
        ("异步上传", test_async_endpoint),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
    
    print("\n" + "=" * 50)
    print(f"🎯 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！服务运行正常")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查服务状态")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main()) 