#!/usr/bin/env python3
"""
前端UI集成测试脚本
测试文件上传和解析功能的完整流程
"""

import asyncio
import aiohttp
import aiofiles
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:7800"

async def test_ui_upload_flow():
    """测试前端UI上传流程"""
    print("🧪 测试前端UI文件上传解析流程...\n")
    
    # 创建测试PDF文件
    test_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (Test Nutrition Guide) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer<</Size 5/Root 1 0 R>>
startxref
299
%%EOF"""
    
    # 保存测试文件
    test_file = Path("test_ui_nutrition.pdf")
    async with aiofiles.open(test_file, 'wb') as f:
        await f.write(test_content)
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. 测试健康状态
            print("1️⃣ 测试服务状态...")
            async with session.get(f"{BASE_URL}/health") as resp:
                health = await resp.json()
                print(f"✅ 服务状态: {health['status']}")
                if health['status'] != 'healthy':
                    print("❌ 服务不健康，停止测试")
                    return
            
            # 2. 测试前端页面可访问性
            print("\n2️⃣ 测试前端页面...")
            async with session.get(f"{BASE_URL}/dashboard") as resp:
                if resp.status == 200:
                    print("✅ 前端页面可访问")
                else:
                    print(f"❌ 前端页面访问失败: {resp.status}")
                    return
            
            # 3. 测试文件上传（异步解析）
            print("\n3️⃣ 测试文件上传功能...")
            
            # 准备表单数据
            data = aiohttp.FormData()
            data.add_field('file', 
                          open(test_file, 'rb'),
                          filename='test_ui_nutrition.pdf',
                          content_type='application/pdf')
            
            # 上传文件
            async with session.post(f"{BASE_URL}/parse/async?parsing_type=auto", data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    task_id = result['task_id']
                    document_id = result['document_id']
                    print(f"✅ 文件上传成功")
                    print(f"   任务ID: {task_id}")
                    print(f"   文档ID: {document_id}")
                    
                    # 4. 监控解析状态
                    print("\n4️⃣ 监控解析状态...")
                    max_attempts = 20
                    for attempt in range(max_attempts):
                        try:
                            async with session.get(f"{BASE_URL}/parse/status/{document_id}") as status_resp:
                                if status_resp.status == 200:
                                    status_data = await status_resp.json()
                                    progress = status_data.get('progress', 0)
                                    message = status_data.get('message', 'Processing...')
                                    
                                    print(f"   进度: {progress}% - {message}")
                                    
                                    # 检查是否完成
                                    if progress >= 100:
                                        print("✅ 解析完成!")
                                        break
                                    
                                    await asyncio.sleep(2)
                                else:
                                    print(f"⚠️ 状态查询失败: {status_resp.status}")
                                    break
                        except Exception as e:
                            print(f"⚠️ 状态查询异常: {e}")
                            break
                    else:
                        print("⚠️ 解析超时，但可能仍在处理中")
                    
                    # 5. 获取解析结果
                    print("\n5️⃣ 获取解析结果...")
                    try:
                        async with session.get(f"{BASE_URL}/parse/result/{document_id}") as result_resp:
                            if result_resp.status == 200:
                                result_data = await result_resp.json()
                                print(f"✅ 解析结果获取成功")
                                print(f"   文件名: {result_data.get('filename')}")
                                print(f"   状态: {result_data.get('status')}")
                                
                                # 显示解析结果概要
                                result_content = result_data.get('result')
                                if result_content:
                                    print(f"   解析类型: {result_content.get('type', 'unknown')}")
                                    if 'nutrition_facts' in result_content:
                                        nutrition = result_content['nutrition_facts']
                                        print(f"   营养信息: {len(nutrition.get('nutrients', []))} 项营养素")
                                    if 'recipe' in result_content:
                                        recipe = result_content['recipe']
                                        print(f"   食谱信息: {recipe.get('title', 'N/A')}")
                                    if 'text_content' in result_content:
                                        text = result_content['text_content']
                                        print(f"   文本内容: {len(text)} 字符")
                                else:
                                    print("   等待解析结果...")
                                    
                            else:
                                print(f"❌ 解析结果获取失败: {result_resp.status}")
                    except Exception as e:
                        print(f"❌ 获取解析结果时出错: {e}")
                    
                    # 6. 测试历史记录
                    print("\n6️⃣ 测试历史记录...")
                    try:
                        async with session.get(f"{BASE_URL}/parse/history?limit=5") as history_resp:
                            if history_resp.status == 200:
                                history_data = await history_resp.json()
                                results = history_data.get('results', [])
                                print(f"✅ 历史记录: 找到 {len(results)} 条记录")
                                
                                # 验证刚上传的文件是否在历史中
                                found_current = any(r.get('document_id') == document_id for r in results)
                                if found_current:
                                    print("✅ 当前上传的文件已出现在历史记录中")
                                else:
                                    print("⚠️ 当前文件未在历史记录中找到（可能需要刷新）")
                            else:
                                print(f"❌ 历史记录获取失败: {history_resp.status}")
                    except Exception as e:
                        print(f"❌ 获取历史记录时出错: {e}")
                        
                else:
                    error = await resp.json()
                    print(f"❌ 文件上传失败: {error}")
                    return
                    
        except Exception as e:
            print(f"❌ 测试过程中出错: {e}")
        finally:
            # 清理测试文件
            if test_file.exists():
                test_file.unlink()
    
    print("\n🎉 前端UI测试完成!")
    print("\n📋 用户操作指南:")
    print("1. 访问 http://localhost:7800/dashboard")
    print("2. 在'文件上传'标签页拖拽或选择PDF文件")
    print("3. 选择解析类型（auto、food、recipe）")
    print("4. 点击'开始解析'按钮")
    print("5. 等待上传完成（状态会显示为'已上传'）")
    print("6. 切换到'解析历史'标签页查看结果")
    print("7. 点击'查看内容'按钮查看详细的解析结果")
    print("\n注意：文件解析可能需要10-30秒，请耐心等待")

if __name__ == "__main__":
    asyncio.run(test_ui_upload_flow()) 