#!/bin/bash

# 本地开发环境停止脚本
echo "⏹️ 停止本地开发环境..."

# 停止主应用
if [ -f "app.pid" ]; then
    echo "🛑 停止 FastAPI 应用..."
    kill $(cat app.pid) 2>/dev/null
    rm app.pid
fi

# 停止 Celery Worker
if [ -f "worker.pid" ]; then
    echo "🛑 停止 Celery Worker..."
    kill $(cat worker.pid) 2>/dev/null
    rm worker.pid
fi

# 停止 Flower
if [ -f "flower.pid" ]; then
    echo "🛑 停止 Flower 监控..."
    kill $(cat flower.pid) 2>/dev/null
    rm flower.pid
fi

# 停止所有相关进程
echo "🧹 清理所有相关进程..."
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "celery.*worker" 2>/dev/null
pkill -f "celery.*flower" 2>/dev/null

echo "✅ 本地开发环境已停止！"
echo ""
echo "💡 说明：本地MongoDB/Redis服务（如果有）保持运行"
echo "�� 如需停止本地数据库服务，请手动操作" 