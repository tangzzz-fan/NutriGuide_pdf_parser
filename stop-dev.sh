#!/bin/bash

# NutriGuide PDF解析工具 - 开发环境停止脚本

echo "🛑 停止 NutriGuide PDF解析工具开发环境..."

# 检查是否在正确的目录
if [ ! -f "main.py" ]; then
    echo "❌ 错误: 请在 pdf_parser 目录下运行此脚本"
    exit 1
fi

# 创建logs目录（如果不存在）
mkdir -p logs

# 从PID文件读取进程ID并停止
if [ -f "logs/backend.pid" ]; then
    BACKEND_PID=$(cat logs/backend.pid)
    if ps -p $BACKEND_PID > /dev/null; then
        echo "🔧 停止后端服务 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        echo "✅ 后端服务已停止"
    else
        echo "⚠️  后端服务进程不存在"
    fi
    rm -f logs/backend.pid
else
    echo "⚠️  未找到后端PID文件，尝试通过端口停止..."
    # 通过端口查找并停止进程
    BACKEND_PID=$(lsof -ti:7800)
    if [ ! -z "$BACKEND_PID" ]; then
        echo "🔧 停止端口7800上的进程 (PID: $BACKEND_PID)..."
        kill $BACKEND_PID
        echo "✅ 后端服务已停止"
    else
        echo "ℹ️  端口7800上没有运行的进程"
    fi
fi

if [ -f "logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if ps -p $FRONTEND_PID > /dev/null; then
        echo "🎨 停止前端服务 (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo "✅ 前端服务已停止"
    else
        echo "⚠️  前端服务进程不存在"
    fi
    rm -f logs/frontend.pid
else
    echo "⚠️  未找到前端PID文件，尝试通过端口停止..."
    # 通过端口查找并停止进程
    FRONTEND_PID=$(lsof -ti:4000)
    if [ ! -z "$FRONTEND_PID" ]; then
        echo "🎨 停止端口4000上的进程 (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo "✅ 前端服务已停止"
    else
        echo "ℹ️  端口4000上没有运行的进程"
    fi
fi

# 停止可能的Node.js进程（Vite开发服务器）
echo "🧹 清理残留的Node.js进程..."
pkill -f "vite" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true

# 停止可能的Python进程
echo "🧹 清理残留的Python进程..."
pkill -f "main.py" 2>/dev/null || true

echo ""
echo "🎉 开发环境已完全停止!"
echo ""
echo "📝 日志文件保留在 logs/ 目录中"
echo "🚀 重新启动请运行: ./start-dev.sh"
echo ""
