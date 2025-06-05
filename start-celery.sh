#!/bin/bash

# NutriGuide PDF解析工具 - Celery工作器启动脚本

echo "🔄 启动 Celery 工作器..."

# 检查是否在正确的目录
if [ ! -f "celery_app.py" ]; then
    echo "❌ 错误: 请在 pdf_parser 目录下运行此脚本"
    exit 1
fi

# 检查Python虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 错误: 未找到Python虚拟环境，请先运行 install-deps.sh"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate
export PYTHONPATH=$PWD:$PYTHONPATH

# 设置 MongoDB 配置环境变量
export MONGODB_URL="mongodb://admin:admin123@localhost:27017/nutriguide_dev?authSource=admin"
export MONGODB_DATABASE="nutriguide_dev"
export ENVIRONMENT=development

# 设置 Redis 配置环境变量
export REDIS_URL="redis://localhost:6379/0"

# 检查 Redis 是否运行 (Docker容器)
if ! docker exec nutriguide-redis-dev redis-cli ping > /dev/null 2>&1; then
    echo "❌ 错误: Redis 未运行，请先启动 Redis Docker 容器"
    echo "提示: 运行 docker-compose -f ../docker-compose.dev.yml up -d redis-dev"
    exit 1
fi

# 检查 MongoDB 是否运行 (Docker容器)
if ! docker exec nutriguide-mongodb-dev mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; then
    echo "❌ 错误: MongoDB 未运行，请先启动 MongoDB Docker 容器"
    echo "提示: 运行 docker-compose -f ../docker-compose.dev.yml up -d mongodb-dev"
    exit 1
fi

echo "✅ 依赖服务检查通过"

# 创建日志目录
mkdir -p logs

# 检查是否已有工作器在运行
if pgrep -f "celery.*worker" > /dev/null; then
    echo "⚠️  警告: Celery 工作器可能已在运行"
    echo "运行以下命令查看: ps aux | grep celery"
fi

echo "🚀 启动 Celery 工作器..."

# 启动 Celery 工作器
celery -A celery_app worker \
    --loglevel=info \
    --logfile=logs/celery_worker.log \
    --pidfile=logs/celery_worker.pid \
    --detach \
    --pool=prefork \
    --concurrency=2 \
    --max-tasks-per-child=1000

if [ $? -eq 0 ]; then
    echo "✅ Celery 工作器已启动"
    echo "📝 日志文件: logs/celery_worker.log"
    echo "🔍 PID文件: logs/celery_worker.pid"
    
    # 等待工作器启动
    sleep 3
    
    # 检查工作器状态
    echo "🔍 检查工作器状态..."
    celery -A celery_app inspect active
    
    if [ $? -eq 0 ]; then
        echo "✅ Celery 工作器运行正常"
    else
        echo "⚠️  工作器可能还在启动中，请稍后再检查"
    fi
else
    echo "❌ Celery 工作器启动失败"
    exit 1
fi

echo ""
echo "🎉 Celery 工作器启动完成!"
echo ""
echo "📊 监控命令:"
echo "   查看工作器: celery -A celery_app inspect active"
echo "   查看队列: celery -A celery_app inspect reserved"
echo "   查看统计: celery -A celery_app inspect stats"
echo ""
echo "🛑 停止工作器:"
echo "   运行: ./stop-celery.sh"
echo "   或者: celery -A celery_app control shutdown"
echo ""
echo "💡 提示: 工作器现在可以处理PDF解析任务了" 