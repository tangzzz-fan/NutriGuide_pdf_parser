#!/bin/bash

echo "🚀 启动简化版本的 PDF Parser 开发环境..."

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 检查Redis服务（仅检查本地，不启动Docker）
echo "🔍 检查Redis服务..."
if nc -z localhost 6379; then
    echo "✅ 使用本地 Redis (端口 6379)"
    export REDIS_URL=redis://localhost:6379/0
else
    echo "⚠️ 本地Redis未运行，使用Mock模式"
    export REDIS_URL=redis://localhost:6379/0  # 即使连接失败也设置，代码中会处理
fi

# 检查MongoDB服务（仅检查本地，不启动Docker）
echo "🔍 检查MongoDB服务..."
if nc -z localhost 27017; then
    echo "✅ 使用本地 MongoDB (端口 27017)"
    export MONGODB_URL=mongodb://localhost:27017
else
    echo "⚠️ 本地MongoDB未运行，使用Mock模式"
    export MONGODB_URL=mongodb://localhost:27017  # 即使连接失败也设置，代码中会处理
fi

# 设置基础环境变量
export ENVIRONMENT=development
export DATABASE_NAME=nutriguide_pdf_parser
export BACKEND_API_URL=http://localhost:3000

# 创建日志目录
mkdir -p logs

echo ""
echo "🚀 启动 FastAPI 应用（纯本地模式）..."
echo "   MongoDB: $MONGODB_URL"
echo "   Redis: $REDIS_URL"
echo "   Mode: 本地开发（无Docker依赖）"
echo ""

# 启动主应用，不启动Celery避免依赖问题
uvicorn main:app --host 0.0.0.0 --port 7800 --reload &
echo $! > app.pid

# 等待启动
sleep 3

if ps -p $(cat app.pid) > /dev/null; then
    echo ""
    echo "✅ 纯本地版本启动成功！"
    echo ""
    echo "📊 访问地址："
    echo "   • API: http://localhost:7800"
    echo "   • 文档: http://localhost:7800/docs"
    echo "   • 健康检查: http://localhost:7800/health"
    echo ""
    echo "💡 开发模式说明："
    echo "   • 如果MongoDB/Redis未运行，服务将使用Mock模式"
    echo "   • PDF解析功能仍然可用（同步模式）"
    echo "   • 异步任务功能暂时禁用"
    echo ""
    echo "⏹️ 停止服务: kill $(cat app.pid) && rm app.pid"
    
    # 测试API
    echo "🔍 测试API连接..."
    sleep 2
    if curl -s http://localhost:7800/health > /dev/null; then
        echo "✅ API 连接成功"
    else
        echo "⚠️ API 连接测试失败，但服务可能正在启动"
    fi
else
    echo "❌ 应用启动失败"
    exit 1
fi 