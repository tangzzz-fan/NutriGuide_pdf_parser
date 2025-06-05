#!/bin/bash

# PDF Parser Service 启动脚本
# 用于快速启动开发环境

set -e

echo "🚀 启动 NutriGuide PDF解析服务..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建目录结构..."
mkdir -p uploads logs

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cat > .env << EOF
# Environment Configuration
ENVIRONMENT=development

# Database Configuration
MONGODB_URL=mongodb://mongo:27017
DATABASE_NAME=nutriguide_pdf_parser

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# External APIs
BACKEND_API_URL=http://localhost:3000

# File Storage
UPLOAD_DIR=./uploads
LOG_DIR=./logs

# PDF Processing
TESSERACT_CMD=/usr/bin/tesseract
EOF
    echo "✅ 环境变量文件已创建"
fi

# 启动服务
echo "🔧 启动服务容器..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
if curl -f http://localhost:7800/health > /dev/null 2>&1; then
    echo "✅ PDF解析服务启动成功!"
    echo "🌐 API文档: http://localhost:7800/docs"
    echo "📊 任务监控: http://localhost:5555"
    echo "🗄️ 数据库管理: http://localhost:8081 (可选)"
else
    echo "❌ 服务启动失败，请检查日志"
    docker-compose logs --tail=50
fi

echo ""
echo "📋 常用命令:"
echo "  查看日志: docker-compose logs -f"
echo "  停止服务: docker-compose down"
echo "  重启服务: docker-compose restart"
echo "  查看状态: docker-compose ps" 