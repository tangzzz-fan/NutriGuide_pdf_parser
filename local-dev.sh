#!/bin/bash

# 本地虚拟环境开发启动脚本
echo "🏠 启动本地虚拟环境开发模式..."

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "📦 创建新的虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "⬆️ 升级pip..."
pip install --upgrade pip

# 检查是否需要安装依赖
if [ ! -f "venv/.deps_installed" ]; then
    echo "📥 首次运行，安装核心依赖..."
    
    # 安装基础依赖，避免问题包
    pip install \
        fastapi==0.104.1 \
        uvicorn[standard]==0.24.0 \
        pydantic==2.5.0 \
        pydantic-settings==2.1.0 \
        pymongo==4.6.0 \
        motor==3.3.2 \
        jinja2==3.1.2 \
        pdfplumber==0.10.3 \
        PyPDF2==3.0.1 \
        pdfminer.six==20231228 \
        python-multipart==0.0.6 \
        aiofiles==23.2.1 \
        pillow==10.1.0 \
        pandas \
        numpy \
        python-dotenv==1.0.0 \
        requests==2.31.0 \
        httpx==0.25.2 \
        loguru==0.7.2 \
        psutil==5.9.6
    
    if [ $? -eq 0 ]; then
        touch venv/.deps_installed
        echo "✅ 核心依赖安装完成"
    else
        echo "❌ 依赖安装失败，请检查错误信息"
        exit 1
    fi
else
    echo "✅ 依赖已安装，跳过安装步骤"
fi

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

# 设置环境变量
export ENVIRONMENT=development
export DATABASE_NAME=nutriguide_pdf_parser
export BACKEND_API_URL=http://localhost:3000
export TESSERACT_CMD=/usr/bin/tesseract

# 创建日志目录
mkdir -p logs

echo ""
echo "🚀 启动 FastAPI 应用（本地开发模式）..."
echo "   MongoDB: $MONGODB_URL"
echo "   Redis: $REDIS_URL"
echo "   Mode: 纯本地开发（无Docker依赖）"
echo ""

# 启动应用（不启动Celery避免依赖问题）
uvicorn main:app --host 0.0.0.0 --port 7800 --reload &

# 记录PID
echo $! > app.pid

echo ""
echo "✅ 本地开发环境已启动！"
echo ""
echo "📊 服务访问地址："
echo "   • Web API: http://localhost:7800"
echo "   • API 文档: http://localhost:7800/docs"
echo "   • 健康检查: http://localhost:7800/health"
echo ""
echo "💡 开发模式说明："
echo "   • 如果MongoDB/Redis未运行，服务将使用Mock模式"
echo "   • PDF解析功能完全可用（同步模式）"
echo "   • 支持热重载和实时调试"
echo "   • Celery异步任务暂时禁用"
echo ""
echo "🔍 查看应用日志："
echo "   tail -f logs/app.log"
echo ""
echo "⏹️  停止服务："
echo "   ./local-stop.sh"
echo ""

# 等待主应用启动
sleep 3

# 检查主应用是否成功启动
if ps -p $(cat app.pid) > /dev/null; then
    echo "✅ FastAPI 应用启动成功"
    
    # 测试API连接
    echo "🔍 测试API连接..."
    sleep 2
    if curl -s http://localhost:7800/health > /dev/null; then
        echo "✅ API 连接成功"
    else
        echo "⚠️ API 连接测试失败，但服务可能正在启动"
    fi
else
    echo "❌ FastAPI 应用启动失败，请检查错误日志"
    exit 1
fi

# 可选：自动打开浏览器
if command -v open &> /dev/null; then
    echo "🌐 打开浏览器..."
    sleep 2  # 等待服务完全启动
    open http://localhost:7800/docs
fi

echo ""
echo "💡 提示：保持此终端窗口打开以查看日志"
echo "💡 如需重新安装依赖，删除 venv/.deps_installed 文件" 