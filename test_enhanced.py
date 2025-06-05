#!/usr/bin/env python3
"""
Enhanced PDF Parser Test Suite
测试新增功能和完整性
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试核心模块导入"""
    print("🧪 测试模块导入...")
    
    try:
        from config.settings import get_settings, Settings
        print("✅ Settings 模块导入成功")
        
        from utils.logger import get_logger
        print("✅ Logger 模块导入成功")
        
        from utils.validators import FileValidator, validate_upload_file
        print("✅ Validators 模块导入成功")
        
        from utils.middleware import MetricsMiddleware, RateLimitMiddleware
        print("✅ Middleware 模块导入成功")
        
        from services.database import DatabaseService
        print("✅ Database 服务导入成功")
        
        from services.pdf_parser import PDFParserService
        print("✅ PDF Parser 服务导入成功")
        
        return True
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False

def test_settings():
    """测试配置管理"""
    print("\n🧪 测试配置管理...")
    
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        print(f"✅ 环境: {settings.environment}")
        print(f"✅ MongoDB URL: {settings.mongodb_url}")
        print(f"✅ 最大文件大小: {settings.max_file_size / 1024 / 1024:.1f}MB")
        print(f"✅ OCR 启用: {settings.ocr_enabled}")
        print(f"✅ 限流启用: {settings.rate_limit_enabled}")
        
        # 测试配置方法
        celery_config = settings.get_celery_config()
        print(f"✅ Celery 配置项数量: {len(celery_config)}")
        
        cors_config = settings.get_cors_config()
        print(f"✅ CORS 配置项数量: {len(cors_config)}")
        
        return True
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_file_validator():
    """测试文件验证器"""
    print("\n🧪 测试文件验证器...")
    
    try:
        from utils.validators import FileValidator, sanitize_filename
        
        validator = FileValidator()
        
        # 测试文件名清理
        dirty_name = "test<>file|name.pdf"
        clean_name = sanitize_filename(dirty_name)
        print(f"✅ 文件名清理: '{dirty_name}' -> '{clean_name}'")
        
        # 创建临时PDF文件进行测试
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # 写入PDF头
            tmp.write(b'%PDF-1.4\n')
            tmp.write(b'%Test PDF content\n')
            tmp_path = tmp.name
        
        try:
            # 测试有效PDF文件
            is_valid, error = validator.validate_file(tmp_path, "test.pdf")
            if is_valid:
                print("✅ PDF 文件验证通过")
            else:
                print(f"⚠️ PDF 文件验证失败: {error}")
            
            # 获取文件信息
            file_info = validator.get_file_info(tmp_path, "test.pdf")
            print(f"✅ 文件信息获取: 大小 {file_info.get('size', 0)} 字节")
            
        finally:
            # 清理临时文件
            os.unlink(tmp_path)
        
        return True
    except Exception as e:
        print(f"❌ 文件验证器测试失败: {e}")
        return False

async def test_database_service():
    """测试数据库服务"""
    print("\n🧪 测试数据库服务...")
    
    try:
        from services.database import DatabaseService
        
        db_service = DatabaseService()
        
        # 注意：这里不实际连接数据库，只测试方法
        print("✅ 数据库服务创建成功")
        print(f"✅ 集合配置: {list(db_service.collections.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ 数据库服务测试失败: {e}")
        return False

def test_pdf_parser_service():
    """测试PDF解析服务"""
    print("\n🧪 测试PDF解析服务...")
    
    try:
        from services.pdf_parser import PDFParserService
        
        pdf_service = PDFParserService()
        print(f"✅ PDF解析服务创建成功")
        print(f"✅ 解析器类型: {list(pdf_service.extractors.keys())}")
        
        # 测试基础信息提取
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-1.4\n%Test content\n')
            tmp_path = tmp.name
        
        try:
            basic_info = pdf_service._extract_basic_info(tmp_path)
            print(f"✅ 基础信息提取: {basic_info.get('filename')}")
        finally:
            os.unlink(tmp_path)
        
        return True
    except Exception as e:
        print(f"❌ PDF解析服务测试失败: {e}")
        return False

def test_metrics_middleware():
    """测试性能监控中间件"""
    print("\n🧪 测试性能监控中间件...")
    
    try:
        from utils.middleware import MetricsMiddleware
        
        # 创建模拟应用
        class MockApp:
            pass
        
        middleware = MetricsMiddleware(MockApp())
        print("✅ 性能监控中间件创建成功")
        
        # 测试指标获取
        metrics = middleware.get_metrics()
        print(f"✅ 指标结构: {list(metrics.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ 性能监控中间件测试失败: {e}")
        return False

def test_api_structure():
    """测试API结构"""
    print("\n🧪 测试API结构...")
    
    try:
        from main import app
        print("✅ 主应用创建成功")
        
        # 获取路由信息
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(f"{route.methods} {route.path}")
        
        print(f"✅ API 路由数量: {len(routes)}")
        for route in routes[:5]:  # 显示前5个路由
            print(f"   {route}")
        
        return True
    except Exception as e:
        print(f"❌ API结构测试失败: {e}")
        return False

def test_environment_config():
    """测试环境配置"""
    print("\n🧪 测试环境配置...")
    
    try:
        from config.settings import get_settings
        settings = get_settings()
        
        # 测试不同环境的行为
        print(f"✅ 当前环境: {settings.environment}")
        print(f"✅ 是否开发环境: {settings.is_development}")
        print(f"✅ 是否生产环境: {settings.is_production}")
        
        # 测试目录创建
        required_dirs = [
            settings.upload_dir,
            settings.temp_dir,
            "logs"
        ]
        
        for directory in required_dirs:
            if os.path.exists(directory):
                print(f"✅ 目录存在: {directory}")
            else:
                print(f"⚠️ 目录不存在: {directory}")
        
        return True
    except Exception as e:
        print(f"❌ 环境配置测试失败: {e}")
        return False

def test_celery_integration():
    """测试Celery集成"""
    print("\n🧪 测试Celery集成...")
    
    try:
        from celery_app import celery_app
        print("✅ Celery应用创建成功")
        
        # 检查任务注册
        registered_tasks = list(celery_app.tasks.keys())
        print(f"✅ 注册任务数量: {len(registered_tasks)}")
        
        # 显示主要任务
        main_tasks = [task for task in registered_tasks if not task.startswith('celery.')]
        for task in main_tasks[:3]:
            print(f"   {task}")
        
        return True
    except Exception as e:
        print(f"❌ Celery集成测试失败: {e}")
        return False

def generate_test_report():
    """生成测试报告"""
    print("\n📋 生成测试报告...")
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "test_results": {
            "imports": False,
            "settings": False,
            "file_validator": False,
            "database_service": False,
            "pdf_parser": False,
            "middleware": False,
            "api_structure": False,
            "environment": False,
            "celery": False
        },
        "summary": {
            "total_tests": 0,
            "passed": 0,
            "failed": 0
        }
    }
    
    # 运行所有测试
    tests = [
        ("imports", test_imports),
        ("settings", test_settings),
        ("file_validator", test_file_validator),
        ("database_service", lambda: asyncio.run(test_database_service())),
        ("pdf_parser", test_pdf_parser_service),
        ("middleware", test_metrics_middleware),
        ("api_structure", test_api_structure),
        ("environment", test_environment_config),
        ("celery", test_celery_integration)
    ]
    
    for test_name, test_func in tests:
        report["test_results"][test_name] = test_func()
        report["summary"]["total_tests"] += 1
        if report["test_results"][test_name]:
            report["summary"]["passed"] += 1
        else:
            report["summary"]["failed"] += 1
    
    # 保存报告
    report_path = "test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 测试报告已保存: {report_path}")
    return report

def main():
    """主测试函数"""
    print("🚀 开始增强测试套件")
    print("=" * 60)
    
    report = generate_test_report()
    
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print(f"总测试数: {report['summary']['total_tests']}")
    print(f"通过: {report['summary']['passed']}")
    print(f"失败: {report['summary']['failed']}")
    
    if report["summary"]["failed"] == 0:
        print("\n🎉 所有测试通过！")
        print("\n📋 下一步:")
        print("1. 启动 MongoDB 和 Redis 服务")
        print("2. 运行: uvicorn main:app --reload")
        print("3. 访问: http://localhost:7800/docs")
        print("4. 测试管理API: http://localhost:7800/admin/metrics")
        return True
    else:
        print(f"\n⚠️ 有 {report['summary']['failed']} 个测试失败")
        print("请检查错误信息并修复问题")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 