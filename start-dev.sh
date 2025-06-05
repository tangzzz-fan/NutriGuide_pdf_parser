#!/bin/bash

# NutriGuide PDF解析工具 - 开发环境启动脚本

echo "🚀 启动 NutriGuide PDF解析工具开发环境..."

# 检查是否在正确的目录
if [ ! -f "main.py" ]; then
    echo "❌ 错误: 请在 pdf_parser 目录下运行此脚本"
    exit 1
fi

# 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 错误: 未找到Python虚拟环境，请先运行 install-deps.sh"
    exit 1
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ 错误: 未找到前端依赖，请先在 frontend 目录下运行 npm install"
    exit 1
fi

echo "📦 检查服务状态..."

# 检查端口占用
if lsof -Pi :7800 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  警告: 端口 7800 已被占用，后端服务可能已在运行"
fi

if lsof -Pi :4000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  警告: 端口 4000 已被占用，前端服务可能已在运行"
fi

echo "🔧 启动后端服务 (端口 7800)..."
# 激活虚拟环境并启动后端
source venv/bin/activate
export PYTHONPATH=$PWD:$PYTHONPATH

# 设置 MongoDB 配置环境变量 - 连接到 Docker 容器
export MONGODB_URL="mongodb://admin:admin123@localhost:27017/nutriguide_dev?authSource=admin"
export MONGODB_DATABASE="nutriguide_dev"
export ENVIRONMENT=development

nohup python main.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 3

echo "🔧 启动 Celery Worker..."
# 检查 Celery Worker 是否已在运行
if pgrep -f "celery.*worker" > /dev/null; then
    echo "⚠️  Celery Worker 已在运行，跳过启动"
else
    # 启动 Celery Worker
    nohup celery -A celery_app worker --loglevel=info --logfile=logs/celery_worker.log --pidfile=logs/celery_worker.pid --detach > /dev/null 2>&1
    sleep 2

    # 检查 Celery Worker 是否成功启动
    if pgrep -f "celery.*worker" > /dev/null; then
        echo "✅ Celery Worker 已启动"
    else
        echo "❌ Celery Worker 启动失败，请检查日志: logs/celery_worker.log"
    fi
fi

echo "🎨 启动前端服务 (端口 4000)..."
# 启动前端
cd frontend
nohup npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"

# 保存PID到文件
echo $BACKEND_PID > logs/backend.pid
echo $FRONTEND_PID > logs/frontend.pid

echo ""
echo "🎉 开发环境启动完成!"
echo ""
echo "📊 服务地址:"
echo "   后端API: http://localhost:7800"
echo "   前端界面: http://localhost:4000"
echo "   API文档: http://localhost:7800/docs"
echo ""
echo "📝 日志文件:"
echo "   后端日志: logs/backend.log"
echo "   前端日志: logs/frontend.log"
echo ""
echo "🛑 停止服务:"
echo "   运行: ./stop-dev.sh"
echo ""
echo "💡 提示: 前端会自动代理API请求到后端服务"
echo ""

# 等待几秒让服务完全启动
sleep 2

# 检查服务是否正常启动
echo "🔍 检查服务状态..."

# 检查后端服务
if curl -s http://localhost:7800/health > /dev/null; then
    echo "✅ 后端服务运行正常"
else
    echo "❌ 后端服务启动失败，请检查日志: logs/backend.log"
fi

# 检查 Celery Worker
if pgrep -f "celery.*worker" > /dev/null; then
    echo "✅ Celery Worker 运行正常"

    # 进一步检查 Celery 是否能处理任务
    if command -v celery > /dev/null; then
        CELERY_STATUS=$(celery -A celery_app inspect active 2>/dev/null | grep -c "celery@" || echo "0")
        if [ "$CELERY_STATUS" -gt 0 ]; then
            echo "✅ Celery Worker 可以接收任务"
        else
            echo "⚠️  Celery Worker 运行中但可能无法接收任务"
        fi
    fi
else
    echo "❌ Celery Worker 未运行，PDF解析功能可能不可用"
fi

# 检查前端服务
if curl -s http://localhost:4000 > /dev/null; then
    echo "✅ 前端服务运行正常"
else
    echo "❌ 前端服务启动失败，请检查日志: logs/frontend.log"
fi

echo ""
echo "🌐 正在打开浏览器..."
sleep 1

# 尝试打开浏览器
if command -v open > /dev/null; then
    open http://localhost:4000
elif command -v xdg-open > /dev/null; then
    xdg-open http://localhost:4000
else
    echo "请手动打开浏览器访问: http://localhost:4000"
fi

echo "✨ 开发环境已就绪，开始开发吧！"
