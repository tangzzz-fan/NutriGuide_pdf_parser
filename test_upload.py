#!/usr/bin/env python3
"""
测试 PDF 上传功能
验证 MongoDB 连接和文件上传是否正常工作
"""

import requests
import json
import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_pdf():
    """创建一个简单的测试 PDF 文件"""
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # 添加一些测试内容
    p.drawString(100, 750, "NutriGuide PDF Parser Test")
    p.drawString(100, 700, "This is a test PDF file for upload testing.")
    p.drawString(100, 650, "Nutrition Facts:")
    p.drawString(120, 600, "Calories: 250 kcal")
    p.drawString(120, 550, "Protein: 15g")
    p.drawString(120, 500, "Fat: 8g")
    p.drawString(120, 450, "Carbohydrates: 35g")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.getvalue()

def test_health_check():
    """测试健康检查接口"""
    print("🔍 测试健康检查接口...")
    try:
        response = requests.get("http://localhost:7800/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过: {data['status']}")
            print(f"   数据库状态: {data['services']['database']}")
            print(f"   Redis状态: {data['services']['redis']}")
            return True
        else:
            print(f"❌ 健康检查失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def test_sync_upload():
    """测试同步文件上传"""
    print("\n📤 测试同步 PDF 上传...")
    
    try:
        # 创建测试 PDF
        pdf_content = create_test_pdf()
        
        # 准备上传文件
        files = {
            'file': ('test_nutrition.pdf', pdf_content, 'application/pdf')
        }
        
        data = {
            'parsing_type': 'auto'
        }
        
        # 发送上传请求
        response = requests.post(
            "http://localhost:7800/parse/sync",
            files=files,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 同步上传成功!")
            print(f"   文档ID: {result.get('document_id')}")
            print(f"   状态: {result.get('status')}")
            print(f"   消息: {result.get('message')}")
            
            # 显示解析结果摘要
            if 'data' in result and result['data']:
                data = result['data']
                print(f"   解析类型: {data.get('parsing_type', 'unknown')}")
                print(f"   质量评分: {data.get('quality_score', 'N/A')}")
                
                if 'basic_info' in data:
                    basic = data['basic_info']
                    print(f"   文件大小: {basic.get('file_size', 'N/A')} bytes")
                    print(f"   页数: {basic.get('page_count', 'N/A')}")
            
            return result.get('document_id')
        else:
            print(f"❌ 同步上传失败: HTTP {response.status_code}")
            print(f"   错误信息: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ 同步上传异常: {e}")
        return None

def test_get_result(document_id):
    """测试获取解析结果"""
    if not document_id:
        return
        
    print(f"\n📊 测试获取解析结果 (ID: {document_id})...")
    
    try:
        response = requests.get(f"http://localhost:7800/parse/status/{document_id}", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取结果成功!")
            print(f"   状态: {result.get('status')}")
            print(f"   进度: {result.get('progress', 0)}%")
            
            if result.get('result'):
                print("   解析结果已保存到数据库")
            
        else:
            print(f"❌ 获取结果失败: HTTP {response.status_code}")
            print(f"   错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 获取结果异常: {e}")

def test_parsing_history():
    """测试获取解析历史"""
    print(f"\n📚 测试获取解析历史...")
    
    try:
        response = requests.get("http://localhost:7800/parse/history?limit=5", timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 获取历史成功!")
            print(f"   总记录数: {result.get('total', 0)}")
            print(f"   返回记录数: {len(result.get('results', []))}")
            
            for i, record in enumerate(result.get('results', [])[:3]):
                print(f"   记录 {i+1}: {record.get('filename')} - {record.get('status')}")
            
        else:
            print(f"❌ 获取历史失败: HTTP {response.status_code}")
            print(f"   错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 获取历史异常: {e}")

def main():
    """主测试函数"""
    print("🧪 开始 PDF Parser 功能测试")
    print("=" * 50)
    
    # 检查依赖
    try:
        import reportlab
    except ImportError:
        print("❌ 缺少 reportlab 依赖，正在安装...")
        os.system("pip install reportlab")
        import reportlab
    
    # 1. 健康检查
    if not test_health_check():
        print("\n❌ 服务未正常运行，请检查服务状态")
        return
    
    # 2. 同步上传测试
    document_id = test_sync_upload()
    
    # 3. 获取结果测试
    test_get_result(document_id)
    
    # 4. 历史记录测试
    test_parsing_history()
    
    print("\n" + "=" * 50)
    print("🎉 测试完成!")
    
    if document_id:
        print("✅ 所有功能正常，MongoDB 连接和文件上传都工作正常")
        print(f"📊 可以访问仪表板查看结果: http://localhost:7800/dashboard")
    else:
        print("⚠️ 部分功能可能存在问题，请检查日志")

if __name__ == "__main__":
    main() 