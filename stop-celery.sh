#!/bin/bash

# NutriGuide PDF解析工具 - 停止 Celery 工作器脚本

echo "🛑 停止 Celery 工作器..."

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
    export PYTHONPATH=$PWD:$PYTHONPATH
fi

# 方法1: 使用 Celery 命令优雅停止
echo "🔄 尝试优雅停止工作器..."
celery -A celery_app control shutdown 2>/dev/null

sleep 2

# 方法2: 通过 PID 文件停止
if [ -f "logs/celery_worker.pid" ]; then
    PID=$(cat logs/celery_worker.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "🔄 通过 PID 停止工作器 ($PID)..."
        kill $PID
        sleep 2
        
        # 检查是否还在运行
        if kill -0 $PID 2>/dev/null; then
            echo "⚠️  强制停止工作器..."
            kill -9 $PID
        fi
    fi
    rm -f logs/celery_worker.pid
fi

# 方法3: 查找并停止所有 celery worker 进程
CELERY_PIDS=$(pgrep -f "celery.*worker")
if [ ! -z "$CELERY_PIDS" ]; then
    echo "🔄 停止剩余的 Celery 进程..."
    for pid in $CELERY_PIDS; do
        echo "   停止进程 $pid"
        kill $pid 2>/dev/null
    done
    
    sleep 2
    
    # 强制停止仍在运行的进程
    REMAINING_PIDS=$(pgrep -f "celery.*worker")
    if [ ! -z "$REMAINING_PIDS" ]; then
        echo "⚠️  强制停止剩余进程..."
        for pid in $REMAINING_PIDS; do
            kill -9 $pid 2>/dev/null
        done
    fi
fi

# 检查是否还有 celery 进程
if pgrep -f "celery.*worker" > /dev/null; then
    echo "❌ 仍有 Celery 进程在运行，请手动检查:"
    ps aux | grep celery | grep -v grep
else
    echo "✅ Celery 工作器已停止"
fi

# 清理日志文件（可选）
if [ "$1" = "--clean" ]; then
    echo "🧹 清理日志文件..."
    rm -f logs/celery_worker.log
    echo "✅ 日志文件已清理"
fi

echo "🎉 Celery 工作器停止完成" 