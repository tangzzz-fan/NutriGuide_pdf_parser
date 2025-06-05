#!/bin/bash

# 开发环境启动脚本
echo "🚀 启动 PDF Parser 开发环境..."

# 检查是否有旧的容器在运行
echo "📋 检查现有容器..."
EXISTING_CONTAINERS=$(docker-compose ps -q)

if [ ! -z "$EXISTING_CONTAINERS" ]; then
    echo "⏹️  停止现有容器..."
    docker-compose down
fi

# 构建镜像（使用虚拟环境）
echo "🔨 构建 Docker 镜像（使用虚拟环境）..."
docker-compose build

# 启动服务
echo "🎯 启动所有服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 显示访问信息
echo ""
echo "✅ PDF Parser 开发环境已启动！"
echo ""
echo "📊 服务访问地址："
echo "   • Web API: http://localhost:7800"
echo "   • API 文档: http://localhost:7800/docs"
echo "   • Flower (任务监控): http://localhost:5555"
echo "   • MongoDB Express: http://localhost:8081"
echo ""
echo "🔍 查看日志："
echo "   docker-compose logs -f web"
echo ""
echo "⏹️  停止服务："
echo "   docker-compose down"
echo ""

# 可选：自动打开浏览器
if command -v open &> /dev/null; then
    echo "🌐 打开浏览器..."
    open http://localhost:7800/docs
fi 