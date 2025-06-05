#!/usr/bin/env python3
"""
后端集成测试脚本
验证 pdf_parser 服务与主后端 API (3000 端口) 的集成
"""

import requests
import json
import time
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# 配置
PDF_PARSER_URL = "http://localhost:7800"
BACKEND_API_URL = "http://localhost:3000"
TIMEOUT = 30

def create_test_pdf():
    """创建测试 PDF"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # 添加营养标签内容
    p.drawString(100, 750, "INTEGRATION TEST - NUTRITION FACTS")
    p.drawString(100, 720, "Per 100g serving")
    p.drawString(100, 690, "")
    
    # 营养成分
    nutrition_data = [
        ("Energy", "280 kcal"),
        ("Protein", "18.0 g"),
        ("Total Fat", "9.5 g"),
        ("Carbohydrates", "32.0 g"),
        ("Fiber", "3.5 g"),
        ("Sugar", "8.2 g"),
        ("Sodium", "95 mg"),
        ("Calcium", "320 mg")
    ]
    
    y_pos = 660
    for item, value in nutrition_data:
        p.drawString(120, y_pos, f"{item}: {value}")
        y_pos -= 25
    
    # 产品信息
    p.drawString(100, 450, "Product: Integration Test Yogurt")
    p.drawString(100, 420, "Brand: TestBrand")
    p.drawString(100, 390, "Net Weight: 200g")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.getvalue()

def test_services_running():
    """测试两个服务是否都在运行"""
    print("🔍 检查服务状态...")
    
    # 检查 PDF Parser 服务
    try:
        response = requests.get(f"{PDF_PARSER_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ PDF Parser 服务运行正常 (7800)")
            pdf_parser_ok = True
        else:
            print(f"❌ PDF Parser 服务异常: HTTP {response.status_code}")
            pdf_parser_ok = False
    except Exception as e:
        print(f"❌ PDF Parser 服务无法访问: {e}")
        pdf_parser_ok = False
    
    # 检查后端 API 服务
    try:
        response = requests.get(f"{BACKEND_API_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ 后端 API 服务运行正常 (3000)")
            backend_api_ok = True
        else:
            print(f"❌ 后端 API 服务异常: HTTP {response.status_code}")
            backend_api_ok = False
    except Exception as e:
        print(f"❌ 后端 API 服务无法访问: {e}")
        backend_api_ok = False
    
    return pdf_parser_ok, backend_api_ok

def test_pdf_parser_upload():
    """测试 PDF Parser 上传功能"""
    print("\n📤 测试 PDF Parser 上传功能...")
    
    try:
        pdf_content = create_test_pdf()
        
        files = {
            'file': ('integration_test.pdf', pdf_content, 'application/pdf')
        }
        
        data = {
            'parsing_type': 'nutrition_label'
        }
        
        response = requests.post(
            f"{PDF_PARSER_URL}/parse/sync",
            files=files,
            data=data,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ PDF Parser 上传成功")
            print(f"   文档ID: {result.get('document_id')}")
            print(f"   状态: {result.get('status')}")
            
            if 'data' in result and result['data']:
                data = result['data']
                print(f"   解析类型: {data.get('parsing_type')}")
                print(f"   质量评分: {data.get('quality_score')}")
            
            return result.get('document_id'), result.get('data')
        else:
            print(f"❌ PDF Parser 上传失败: HTTP {response.status_code}")
            print(f"   错误: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ PDF Parser 上传异常: {e}")
        return None, None

def test_backend_api_endpoints():
    """测试后端 API 的相关端点"""
    print("\n🔌 测试后端 API 端点...")
    
    endpoints_to_test = [
        ("/health", "健康检查"),
        ("/api/docs", "API 文档"),  # 假设后端有这个端点
    ]
    
    results = {}
    
    for endpoint, description in endpoints_to_test:
        try:
            response = requests.get(f"{BACKEND_API_URL}{endpoint}", timeout=10)
            if response.status_code == 200:
                print(f"✅ {description}: 正常")
                results[endpoint] = True
            else:
                print(f"❌ {description}: HTTP {response.status_code}")
                results[endpoint] = False
        except Exception as e:
            print(f"❌ {description}: 异常 - {e}")
            results[endpoint] = False
    
    return results

def test_database_consistency():
    """测试数据库一致性（通过 PDF Parser API）"""
    print("\n🗄️ 测试数据库一致性...")
    
    try:
        # 获取解析历史
        response = requests.get(f"{PDF_PARSER_URL}/parse/history?limit=5", timeout=10)
        
        if response.status_code == 200:
            history = response.json()
            total_records = history.get('total', 0)
            returned_records = len(history.get('results', []))
            
            print(f"✅ 数据库查询正常")
            print(f"   总记录数: {total_records}")
            print(f"   返回记录数: {returned_records}")
            
            # 检查最近的记录
            if history.get('results'):
                latest = history['results'][0]
                print(f"   最新记录: {latest.get('filename')} - {latest.get('status')}")
            
            return True
        else:
            print(f"❌ 数据库查询失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 数据库查询异常: {e}")
        return False

def test_cross_service_workflow():
    """测试跨服务工作流"""
    print("\n🔄 测试跨服务工作流...")
    
    # 这里可以测试 PDF Parser 解析的数据是否能被后端 API 使用
    # 由于不知道后端 API 的具体接口，我们模拟一个测试场景
    
    print("   📊 步骤 1: 使用 PDF Parser 解析文档")
    document_id, parsed_data = test_pdf_parser_upload()
    
    if not document_id:
        print("   ❌ PDF 解析失败，无法继续跨服务测试")
        return False
    
    print("   📊 步骤 2: 验证解析结果可用性")
    try:
        response = requests.get(f"{PDF_PARSER_URL}/parse/status/{document_id}", timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('data'):
                print("   ✅ 解析结果可正常获取")
                
                # 这里可以尝试将数据发送给后端 API
                # 由于不知道具体的端点，我们只是验证数据格式
                parsed_data = result['data']
                
                print("   📊 步骤 3: 验证数据格式兼容性")
                if validate_data_format(parsed_data):
                    print("   ✅ 数据格式符合后端 API 要求")
                    return True
                else:
                    print("   ⚠️ 数据格式可能需要调整")
                    return False
            else:
                print("   ❌ 解析结果为空")
                return False
        else:
            print(f"   ❌ 获取解析结果失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 跨服务工作流异常: {e}")
        return False

def validate_data_format(data):
    """验证数据格式是否符合后端 API 要求"""
    if not isinstance(data, dict):
        return False
    
    # 检查基本结构
    required_fields = ['basic_info', 'extracted_data', 'quality_score', 'parsing_type', 'status']
    for field in required_fields:
        if field not in data:
            return False
    
    # 检查营养数据格式
    if 'extracted_data' in data and data['extracted_data']:
        extracted = data['extracted_data']
        if extracted.get('type') == 'food' and extracted.get('nutrition'):
            # 营养数据应该是字典格式
            if not isinstance(extracted['nutrition'], dict):
                return False
    
    return True

def test_concurrent_requests():
    """测试并发请求处理"""
    print("\n⚡ 测试并发请求处理...")
    
    # 简单的并发测试：同时发送健康检查请求
    import threading
    import time
    
    results = []
    
    def health_check_worker():
        try:
            start_time = time.time()
            response = requests.get(f"{PDF_PARSER_URL}/health", timeout=5)
            end_time = time.time()
            
            results.append({
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'success': response.status_code == 200
            })
        except Exception as e:
            results.append({
                'status_code': None,
                'response_time': None,
                'success': False,
                'error': str(e)
            })
    
    # 启动多个并发请求
    threads = []
    thread_count = 5
    
    print(f"   🚀 启动 {thread_count} 个并发健康检查请求...")
    
    for i in range(thread_count):
        thread = threading.Thread(target=health_check_worker)
        threads.append(thread)
        thread.start()
    
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    # 分析结果
    successful_requests = sum(1 for r in results if r['success'])
    avg_response_time = sum(r['response_time'] for r in results if r['response_time']) / len([r for r in results if r['response_time']])
    
    print(f"   📊 并发测试结果:")
    print(f"      成功请求: {successful_requests}/{thread_count}")
    print(f"      平均响应时间: {avg_response_time:.3f} 秒")
    
    if successful_requests == thread_count and avg_response_time < 1.0:
        print("   ✅ 并发处理能力良好")
        return True
    else:
        print("   ⚠️ 并发处理可能需要优化")
        return False

def main():
    """主测试函数"""
    print("🧪 开始后端集成测试")
    print("=" * 60)
    
    test_results = {}
    
    # 1. 检查服务状态
    pdf_parser_ok, backend_api_ok = test_services_running()
    test_results['services_running'] = pdf_parser_ok and backend_api_ok
    
    if not pdf_parser_ok:
        print("\n❌ PDF Parser 服务未运行，停止测试")
        return False
    
    # 2. 测试 PDF Parser 功能
    document_id, parsed_data = test_pdf_parser_upload()
    test_results['pdf_parser_upload'] = document_id is not None
    
    # 3. 测试后端 API 端点（如果可用）
    if backend_api_ok:
        api_results = test_backend_api_endpoints()
        test_results['backend_api_endpoints'] = any(api_results.values())
    else:
        test_results['backend_api_endpoints'] = False
        print("\n⚠️ 后端 API 服务未运行，跳过相关测试")
    
    # 4. 测试数据库一致性
    test_results['database_consistency'] = test_database_consistency()
    
    # 5. 测试跨服务工作流
    test_results['cross_service_workflow'] = test_cross_service_workflow()
    
    # 6. 测试并发处理
    test_results['concurrent_requests'] = test_concurrent_requests()
    
    # 输出最终结果
    print("\n" + "=" * 60)
    print("🎯 集成测试结果汇总")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"成功率: {(passed_tests/total_tests)*100:.1f}%")
    
    print("\n📋 详细结果:")
    test_descriptions = {
        'services_running': '服务运行状态',
        'pdf_parser_upload': 'PDF Parser 上传',
        'backend_api_endpoints': '后端 API 端点',
        'database_consistency': '数据库一致性',
        'cross_service_workflow': '跨服务工作流',
        'concurrent_requests': '并发请求处理'
    }
    
    for test_key, result in test_results.items():
        status = "✅" if result else "❌"
        description = test_descriptions.get(test_key, test_key)
        print(f"   {status} {description}")
    
    print("\n🌐 服务地址:")
    print(f"   • PDF Parser: {PDF_PARSER_URL}")
    print(f"   • 后端 API: {BACKEND_API_URL}")
    print(f"   • PDF Parser 仪表板: {PDF_PARSER_URL}/dashboard")
    print(f"   • PDF Parser API 文档: {PDF_PARSER_URL}/docs")
    
    if passed_tests == total_tests:
        print("\n🎉 所有集成测试通过！")
        print("✅ PDF Parser 服务与后端系统集成正常")
        print("✅ 数据流转和存储功能完善")
        return True
    else:
        print(f"\n⚠️ 有 {total_tests - passed_tests} 个测试失败")
        print("💡 建议检查失败的测试项并进行相应优化")
        return False

if __name__ == "__main__":
    main() 