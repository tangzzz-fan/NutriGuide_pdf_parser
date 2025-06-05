#!/bin/bash

# Start PDF Parser Service with MongoDB configuration
# This script sets up the correct environment variables to connect to MongoDB running in Docker

echo "🚀 启动 PDF Parser 服务..."
echo "📦 MongoDB 配置: Docker 容器 (nutriguide-mongodb-dev)"
echo "🔐 使用认证: admin:admin123"
echo "📊 数据库: nutriguide_dev"
echo ""

# 检查 MongoDB 容器是否运行
if ! docker ps | grep -q nutriguide-mongodb-dev; then
    echo "⚠️  MongoDB 容器未运行，请先启动 Docker 服务："
    echo "cd .. && docker-compose -f docker-compose.dev.yml up -d mongodb-dev"
    exit 1
fi

# 检查端口是否被占用
if lsof -i:7800 >/dev/null 2>&1; then
    echo "⚠️  端口 7800 已被占用，正在停止..."
    lsof -ti:7800 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# 设置环境变量
export ENVIRONMENT=development
export DEBUG=true
export HOST=0.0.0.0
export PORT=7800

# MongoDB 配置 - 连接到 Docker 容器
export MONGODB_URL="mongodb://admin:admin123@localhost:27017/nutriguide_dev?authSource=admin"
export MONGODB_DATABASE="nutriguide_dev"
export MONGODB_MAX_POOL_SIZE=10
export MONGODB_MIN_POOL_SIZE=5

# Redis 配置
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="redis://localhost:6379/1"
export CELERY_RESULT_BACKEND="redis://localhost:6379/2"

# 安全配置
export SECRET_KEY="pdf-parser-dev-secret-key-2024"
export CORS_ORIGINS='["http://localhost:3000", "http://localhost:3001", "http://localhost:7800"]'

# 日志配置
export LOG_LEVEL=INFO

echo "✅ 环境变量已设置"
echo "🌐 服务将在 http://localhost:7800 启动"
echo "📊 仪表板: http://localhost:7800/dashboard"
echo "📚 API 文档: http://localhost:7800/docs"
echo ""

# 启动服务
echo "🚀 启动中..."
python -m uvicorn main:app --reload --host 0.0.0.0 --port 7800 