#!/usr/bin/env python3
"""
简单的Celery测试脚本
"""

import time
import os
from celery_app import celery_app

def test_celery_connection():
    """测试Celery连接"""
    print("🧪 测试Celery连接...")
    
    try:
        # 检查工作器状态
        i = celery_app.control.inspect()
        active = i.active()
        stats = i.stats()
        
        print(f"✅ 工作器连接成功")
        print(f"活跃任务: {active}")
        print(f"工作器统计: {list(stats.keys()) if stats else 'None'}")
        
        return True
    except Exception as e:
        print(f"❌ Celery连接失败: {e}")
        return False

def test_task_submission():
    """测试任务提交"""
    print("\n🧪 测试任务提交...")
    
    try:
        # 创建一个测试文件
        test_file = "test_simple.pdf"
        with open(test_file, "w") as f:
            f.write("test content")
        
        # 提交任务
        result = celery_app.send_task(
            'parse_pdf_task',
            args=[test_file, 'test_file_id', 'test_doc_id', 'auto'],
            task_id='simple_test_task'
        )
        
        print(f"✅ 任务提交成功: {result.id}")
        print(f"任务状态: {result.status}")
        
        # 等待一段时间
        print("⏳ 等待5秒...")
        time.sleep(5)
        
        # 检查任务状态
        print(f"任务最终状态: {result.status}")
        
        # 检查工作器
        i = celery_app.control.inspect()
        active = i.active()
        print(f"当前活跃任务: {active}")
        
        # 清理
        if os.path.exists(test_file):
            os.remove(test_file)
            
        return True
    except Exception as e:
        print(f"❌ 任务提交失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Celery简单测试")
    
    # 测试连接
    if not test_celery_connection():
        exit(1)
    
    # 测试任务提交
    if not test_task_submission():
        exit(1)
    
    print("\n🎉 Celery测试完成!") 