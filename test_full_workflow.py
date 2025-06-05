#!/usr/bin/env python3
"""
完整工作流测试脚本
验证 PDF 上传、解析、数据库存储的完整流程
"""

import requests
import json
import os
import time
import asyncio
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import traceback
from datetime import datetime

# 测试配置
API_BASE = "http://localhost:7800"
TIMEOUT = 30

def create_nutrition_label_pdf():
    """创建一个包含营养标签信息的测试 PDF"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # 添加营养标签内容
    p.drawString(100, 750, "NUTRITION FACTS - TEST PRODUCT")
    p.drawString(100, 720, "Per 100g serving")
    p.drawString(100, 690, "")
    
    # 营养成分表
    nutrition_data = [
        ("Energy", "250 kcal", "1046 kJ"),
        ("Protein", "15.0 g", ""),
        ("Total Fat", "8.5 g", ""),
        ("- Saturated Fat", "3.2 g", ""),
        ("Carbohydrates", "35.2 g", ""),
        ("- Sugars", "12.1 g", ""),
        ("Dietary Fiber", "2.8 g", ""),
        ("Sodium", "120 mg", ""),
        ("Calcium", "280 mg", ""),
        ("Iron", "2.1 mg", ""),
        ("Vitamin C", "15 mg", ""),
        ("Vitamin A", "180 μg", "")
    ]
    
    y_pos = 660
    for item, value, extra in nutrition_data:
        p.drawString(120, y_pos, f"{item}: {value}")
        if extra:
            p.drawString(300, y_pos, extra)
        y_pos -= 25
    
    # 添加产品信息
    p.drawString(100, 350, "Product Information:")
    p.drawString(120, 320, "Name: Premium Organic Milk")
    p.drawString(120, 290, "Brand: TestBrand")
    p.drawString(120, 260, "Net Weight: 1L")
    p.drawString(120, 230, "Category: Dairy Products")
    
    # 添加配料表
    p.drawString(100, 180, "Ingredients:")
    p.drawString(120, 150, "Organic whole milk, Vitamin D3")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.getvalue()

def create_recipe_pdf():
    """创建一个包含食谱的测试 PDF"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # 食谱标题
    p.drawString(100, 750, "RECIPE: Chocolate Chip Cookies")
    p.drawString(100, 720, "Serves: 24 cookies")
    p.drawString(100, 690, "Prep Time: 15 minutes")
    p.drawString(100, 660, "Cook Time: 12 minutes")
    
    # 配料列表
    p.drawString(100, 620, "INGREDIENTS:")
    ingredients = [
        "2 1/4 cups all-purpose flour",
        "1 tsp baking soda",
        "1 tsp salt",
        "1 cup butter, softened",
        "3/4 cup granulated sugar",
        "3/4 cup packed brown sugar",
        "2 large eggs",
        "2 tsp vanilla extract",
        "2 cups chocolate chips"
    ]
    
    y_pos = 590
    for ingredient in ingredients:
        p.drawString(120, y_pos, f"• {ingredient}")
        y_pos -= 20
    
    # 制作步骤
    p.drawString(100, 390, "INSTRUCTIONS:")
    instructions = [
        "1. Preheat oven to 375°F (190°C)",
        "2. Mix flour, baking soda and salt in bowl",
        "3. Beat butter and sugars until creamy",
        "4. Add eggs and vanilla, mix well",
        "5. Gradually add flour mixture",
        "6. Stir in chocolate chips",
        "7. Drop rounded tablespoons onto ungreased cookie sheets",
        "8. Bake 9-11 minutes until golden brown"
    ]
    
    y_pos = 360
    for instruction in instructions:
        p.drawString(120, y_pos, instruction)
        y_pos -= 25
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.getvalue()

def test_health_check():
    """测试健康检查"""
    print("🔍 测试健康检查接口...")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过: {data['status']}")
            print(f"   数据库状态: {data['services']['database']}")
            print(f"   Redis状态: {data['services']['redis']}")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def test_sync_upload(file_content, filename, parsing_type="auto"):
    """测试同步文件上传"""
    print(f"\n📤 测试同步上传: {filename} (类型: {parsing_type})")
    
    try:
        files = {
            'file': (filename, file_content, 'application/pdf')
        }
        
        data = {
            'parsing_type': parsing_type
        }
        
        response = requests.post(
            f"{API_BASE}/parse/sync",
            files=files,
            data=data,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 上传成功!")
            print(f"   文档ID: {result.get('document_id')}")
            print(f"   状态: {result.get('status')}")
            
            # 验证解析结果
            if 'data' in result and result['data']:
                data = result['data']
                print(f"   解析类型: {data.get('parsing_type', 'unknown')}")
                print(f"   质量评分: {data.get('quality_score', 'N/A')}")
                
                # 检查基础信息
                if 'basic_info' in data:
                    basic = data['basic_info']
                    print(f"   文件大小: {basic.get('file_size', 'N/A')} bytes")
                    print(f"   页数: {basic.get('page_count', 'N/A')}")
                
                # 检查提取的数据
                if 'extracted_data' in data:
                    extracted = data['extracted_data']
                    print(f"   数据类型: {extracted.get('type', 'unknown')}")
                    
                    # 如果是营养标签，检查营养数据
                    if extracted.get('nutrition'):
                        nutrition = extracted['nutrition']
                        print(f"   营养信息: 已提取 {len(nutrition)} 项营养成分")
                    
                    # 如果是食谱，检查食谱信息
                    if extracted.get('recipe_info'):
                        recipe = extracted['recipe_info']
                        print(f"   食谱名称: {recipe.get('name', 'N/A')}")
                        print(f"   配料数量: {len(recipe.get('ingredients', []))}")
            
            return result.get('document_id')
        else:
            print(f"❌ 上传失败: HTTP {response.status_code}")
            print(f"   错误信息: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 上传异常: {e}")
        traceback.print_exc()
        return None

def test_get_status(document_id):
    """测试获取解析状态"""
    if not document_id:
        return False
        
    print(f"\n📊 测试获取解析状态 (ID: {document_id})...")
    
    try:
        response = requests.get(f"{API_BASE}/parse/status/{document_id}", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取状态成功!")
            print(f"   API状态: {result.get('status')}")
            print(f"   消息: {result.get('message')}")
            print(f"   进度: {result.get('progress', 0)}%")
            print(f"   创建时间: {result.get('created_at')}")
            print(f"   更新时间: {result.get('updated_at')}")
            
            if result.get('data'):
                print("   解析结果: 已保存到数据库")
                return True
            else:
                print("   解析结果: 未找到数据")
                return False
        else:
            print(f"❌ 获取状态失败: HTTP {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 获取状态异常: {e}")
        return False

def test_parsing_history():
    """测试解析历史查询"""
    print(f"\n📚 测试解析历史查询...")
    
    try:
        response = requests.get(f"{API_BASE}/parse/history?limit=10", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取历史成功!")
            print(f"   总记录数: {result.get('total', 0)}")
            print(f"   返回记录数: {len(result.get('results', []))}")
            
            # 显示最近的记录
            for i, record in enumerate(result.get('results', [])[:5]):
                print(f"   记录 {i+1}: {record.get('filename')} - {record.get('status')} (质量: {record.get('quality_score', 'N/A')})")
            
            return True
        else:
            print(f"❌ 获取历史失败: HTTP {response.status_code}")
            print(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 获取历史异常: {e}")
        return False

def test_database_persistence(document_id):
    """测试数据库持久化"""
    if not document_id:
        return False
    
    print(f"\n🗄️ 测试数据库持久化...")
    
    # 等待一段时间确保数据已经写入
    time.sleep(1)
    
    # 重新获取数据检查持久化
    try:
        response = requests.get(f"{API_BASE}/parse/status/{document_id}", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('data'):
                print("✅ 数据库持久化验证成功")
                print(f"   数据完整性: OK")
                return True
            else:
                print("❌ 数据库中未找到解析结果")
                return False
        else:
            print(f"❌ 验证失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 持久化验证异常: {e}")
        return False

def test_api_docs():
    """测试 API 文档访问"""
    print(f"\n📖 测试 API 文档访问...")
    
    try:
        response = requests.get(f"{API_BASE}/docs", timeout=10)
        if response.status_code == 200:
            print("✅ API 文档访问正常")
            return True
        else:
            print(f"❌ API 文档访问失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API 文档访问异常: {e}")
        return False

def test_dashboard():
    """测试仪表板访问"""
    print(f"\n📊 测试仪表板访问...")
    
    try:
        response = requests.get(f"{API_BASE}/dashboard", timeout=10)
        if response.status_code == 200 and "PDF解析工具" in response.text:
            print("✅ 仪表板访问正常")
            return True
        else:
            print(f"❌ 仪表板访问失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 仪表板访问异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🧪 开始完整工作流测试")
    print("=" * 60)
    
    # 测试计数器
    total_tests = 0
    passed_tests = 0
    
    # 存储测试结果
    test_results = {}
    document_ids = []
    
    try:
        # 1. 健康检查
        total_tests += 1
        if test_health_check():
            passed_tests += 1
            test_results['health_check'] = True
        else:
            test_results['health_check'] = False
            print("\n❌ 服务未正常运行，停止测试")
            return
        
        # 2. API 文档测试
        total_tests += 1
        if test_api_docs():
            passed_tests += 1
            test_results['api_docs'] = True
        else:
            test_results['api_docs'] = False
        
        # 3. 仪表板测试
        total_tests += 1
        if test_dashboard():
            passed_tests += 1
            test_results['dashboard'] = True
        else:
            test_results['dashboard'] = False
        
        # 4. 营养标签PDF上传测试
        print("\n" + "="*40)
        print("🍎 营养标签解析测试")
        print("="*40)
        
        nutrition_pdf = create_nutrition_label_pdf()
        total_tests += 1
        nutrition_doc_id = test_sync_upload(nutrition_pdf, "nutrition_label_test.pdf", "nutrition_label")
        if nutrition_doc_id:
            passed_tests += 1
            test_results['nutrition_upload'] = True
            document_ids.append(nutrition_doc_id)
        else:
            test_results['nutrition_upload'] = False
        
        # 5. 食谱PDF上传测试
        print("\n" + "="*40)
        print("🍪 食谱解析测试")
        print("="*40)
        
        recipe_pdf = create_recipe_pdf()
        total_tests += 1
        recipe_doc_id = test_sync_upload(recipe_pdf, "recipe_test.pdf", "recipe")
        if recipe_doc_id:
            passed_tests += 1
            test_results['recipe_upload'] = True
            document_ids.append(recipe_doc_id)
        else:
            test_results['recipe_upload'] = False
        
        # 6. 自动检测PDF上传测试
        print("\n" + "="*40)
        print("🔍 自动检测解析测试")
        print("="*40)
        
        auto_pdf = create_nutrition_label_pdf()  # 使用营养标签PDF测试自动检测
        total_tests += 1
        auto_doc_id = test_sync_upload(auto_pdf, "auto_detect_test.pdf", "auto")
        if auto_doc_id:
            passed_tests += 1
            test_results['auto_upload'] = True
            document_ids.append(auto_doc_id)
        else:
            test_results['auto_upload'] = False
        
        # 7. 状态查询测试
        print("\n" + "="*40)
        print("📊 状态查询测试")
        print("="*40)
        
        status_tests_passed = 0
        for doc_id in document_ids:
            total_tests += 1
            if test_get_status(doc_id):
                status_tests_passed += 1
                passed_tests += 1
        
        test_results['status_query'] = status_tests_passed == len(document_ids)
        
        # 8. 数据库持久化测试
        print("\n" + "="*40)
        print("🗄️ 数据库持久化测试")
        print("="*40)
        
        persistence_tests_passed = 0
        for doc_id in document_ids:
            total_tests += 1
            if test_database_persistence(doc_id):
                persistence_tests_passed += 1
                passed_tests += 1
        
        test_results['persistence'] = persistence_tests_passed == len(document_ids)
        
        # 9. 历史查询测试
        total_tests += 1
        if test_parsing_history():
            passed_tests += 1
            test_results['history_query'] = True
        else:
            test_results['history_query'] = False
        
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {e}")
        traceback.print_exc()
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("🎯 测试结果汇总")
    print("=" * 60)
    
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"成功率: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%")
    
    print("\n📋 详细结果:")
    result_items = [
        ("健康检查", test_results.get('health_check', False)),
        ("API文档", test_results.get('api_docs', False)),
        ("仪表板", test_results.get('dashboard', False)),
        ("营养标签上传", test_results.get('nutrition_upload', False)),
        ("食谱上传", test_results.get('recipe_upload', False)),
        ("自动检测上传", test_results.get('auto_upload', False)),
        ("状态查询", test_results.get('status_query', False)),
        ("数据库持久化", test_results.get('persistence', False)),
        ("历史查询", test_results.get('history_query', False))
    ]
    
    for name, result in result_items:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    print("\n🌐 服务访问地址:")
    print(f"   • API服务: {API_BASE}")
    print(f"   • API文档: {API_BASE}/docs")
    print(f"   • 仪表板: {API_BASE}/dashboard")
    print(f"   • 健康检查: {API_BASE}/health")
    
    if document_ids:
        print(f"\n📄 测试生成的文档ID:")
        for i, doc_id in enumerate(document_ids, 1):
            print(f"   {i}. {doc_id}")
    
    # 最终判断
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！PDF 上传、解析和数据库存储功能完全正常!")
        return True
    else:
        print(f"\n⚠️ 有 {total_tests - passed_tests} 个测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    main() 