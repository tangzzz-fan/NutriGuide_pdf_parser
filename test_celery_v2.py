#!/usr/bin/env python3
"""
测试Celery V2任务（无状态更新版本）
"""

import time
import os
import json
from celery_app import celery_app
from celery.result import AsyncResult

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

def test_v2_task_submission():
    """测试V2任务提交"""
    print("\n🧪 测试V2任务提交...")
    
    try:
        # 创建一个测试文件
        test_file = "test_v2.pdf"
        with open(test_file, "w") as f:
            f.write("test content for celery v2")
        
        # 提交V2任务
        task_id = 'v2_test_task'
        result = celery_app.send_task(
            'parse_pdf_task_v2',
            args=[test_file, 'test_file_id_v2', 'test_doc_id_v2', 'auto'],
            task_id=task_id
        )
        
        print(f"✅ V2任务提交成功: {result.id}")
        print(f"初始任务状态: {result.status}")
        
        # 监控任务状态变化
        timeout = 30  # 最长等待30秒
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            current_status = result.status
            print(f"⏳ 任务状态: {current_status}")
            
            if current_status in ['SUCCESS', 'FAILURE']:
                break
                
            time.sleep(2)
        
        # 获取最终结果
        final_status = result.status
        print(f"🏁 最终状态: {final_status}")
        
        if final_status == 'SUCCESS':
            try:
                task_result = result.get(timeout=5)
                print(f"✅ 任务结果: {json.dumps(task_result, indent=2, ensure_ascii=False)}")
            except Exception as e:
                print(f"⚠️  获取结果时出错: {e}")
        elif final_status == 'FAILURE':
            try:
                error_info = result.info
                print(f"❌ 任务失败信息: {json.dumps(error_info, indent=2, ensure_ascii=False)}")
            except Exception as e:
                print(f"⚠️  获取错误信息时出错: {e}")
        else:
            print(f"⚠️  任务状态: {final_status}")
        
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            
        return True
        
    except Exception as e:
        print(f"❌ V2任务测试失败: {e}")
        return False

def test_direct_task_call():
    """测试直接调用任务函数"""
    print("\n🧪 测试直接调用任务函数...")
    
    try:
        from celery_app import parse_pdf_task
        
        # 创建一个测试文件
        test_file = "test_direct.pdf"
        with open(test_file, "w") as f:
            f.write("test content for direct call")
        
        # 直接调用任务函数（同步）
        print("📞 直接调用任务函数...")
        
        # 模拟self对象
        class MockSelf:
            def update_state(self, **kwargs):
                pass
        
        mock_self = MockSelf()
        
        # 调用任务
        result = parse_pdf_task(
            mock_self,
            test_file, 
            'test_file_id_direct', 
            'test_doc_id_direct', 
            'auto'
        )
        
        print(f"✅ 直接调用结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            
        return True
        
    except Exception as e:
        print(f"❌ 直接调用测试失败: {e}")
        return False

def test_worker_status():
    """测试工作器状态"""
    print("\n🧪 测试工作器状态...")
    
    try:
        i = celery_app.control.inspect()
        
        # 获取各种状态信息
        active = i.active()
        reserved = i.reserved()
        stats = i.stats()
        registered = i.registered()
        
        print(f"活跃任务: {active}")
        print(f"保留任务: {reserved}")
        print(f"已注册任务: {list(registered.values())[0] if registered else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 工作器状态检查失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Celery V2 测试")
    print("=" * 50)
    
    # 测试连接
    if not test_celery_connection():
        exit(1)
    
    # 测试工作器状态
    test_worker_status()
    
    # 测试V2任务提交
    test_v2_task_submission()
    
    # 测试直接调用
    test_direct_task_call()
    
    print("\n🎉 Celery V2 测试完成!") 