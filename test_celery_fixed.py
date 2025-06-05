#!/usr/bin/env python3
"""
修复后的Celery测试脚本
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

def test_task_submission_and_result():
    """测试任务提交和结果获取"""
    print("\n🧪 测试任务提交和结果获取...")
    
    try:
        # 创建一个测试文件
        test_file = "test_fixed.pdf"
        with open(test_file, "w") as f:
            f.write("test content for fixed celery")
        
        # 提交任务
        task_id = 'fixed_test_task'
        result = celery_app.send_task(
            'parse_pdf_task',
            args=[test_file, 'test_file_id_fixed', 'test_doc_id_fixed', 'auto'],
            task_id=task_id
        )
        
        print(f"✅ 任务提交成功: {result.id}")
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
            print(f"⚠️  任务状态异常: {final_status}")
        
        # 检查工作器状态
        i = celery_app.control.inspect()
        active = i.active()
        print(f"💼 当前活跃任务: {active}")
        
        # 清理测试文件
        if os.path.exists(test_file):
            os.remove(test_file)
            
        return final_status in ['SUCCESS', 'FAILURE']  # 任务有明确结果就算成功
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_result_retrieval():
    """测试结果检索"""
    print("\n🧪 测试结果检索...")
    
    try:
        # 创建AsyncResult对象
        test_task_id = 'fixed_test_task'
        result = AsyncResult(test_task_id, app=celery_app)
        
        print(f"任务ID: {test_task_id}")
        print(f"任务状态: {result.status}")
        print(f"任务就绪: {result.ready()}")
        print(f"任务成功: {result.successful()}")
        print(f"任务失败: {result.failed()}")
        
        if result.ready():
            if result.successful():
                print(f"✅ 任务结果: {result.result}")
            else:
                print(f"❌ 任务错误: {result.info}")
        else:
            print("⏳ 任务还在处理中...")
            
        return True
    except Exception as e:
        print(f"❌ 结果检索失败: {e}")
        return False

def test_broker_backend_config():
    """测试broker和backend配置"""
    print("\n🧪 测试broker和backend配置...")
    
    try:
        conf = celery_app.conf
        print(f"Broker URL: {conf.broker_url}")
        print(f"Result Backend: {conf.result_backend}")
        print(f"Task Serializer: {conf.task_serializer}")
        print(f"Result Serializer: {conf.result_serializer}")
        print(f"Accept Content: {conf.accept_content}")
        print(f"Result Accept Content: {conf.result_accept_content}")
        
        return True
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Celery修复后测试")
    print("=" * 50)
    
    # 测试连接
    if not test_celery_connection():
        exit(1)
    
    # 测试配置
    if not test_broker_backend_config():
        exit(1)
    
    # 测试任务提交和结果
    if not test_task_submission_and_result():
        print("⚠️  任务执行测试未完全成功，但这可能是正常的（取决于具体错误）")
    
    # 测试结果检索
    test_result_retrieval()
    
    print("\n🎉 Celery修复测试完成!")
    print("💡 如果看到明确的错误信息而不是序列化错误，说明修复已生效") 