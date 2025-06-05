# 📦 NutriGuide PDF Parser 部署指南

## 🎯 概述

这是一个完整的 PDF 解析微服务，专门用于解析营养标签、食谱和膳食指南等文档。本指南将帮助您部署和运行服务。

## 🏗️ 架构概览

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │    MongoDB      │    │     Redis       │
│  (PDF Parser)   │◄──►│   (Database)    │    │  (Queue/Cache)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Celery Workers  │
│ (Async Tasks)   │
└─────────────────┘
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo>
cd pdf_parser

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制环境配置模板：
```bash
cp .env.example .env
```

编辑 `.env` 文件：
```bash
# 基础配置
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 数据库配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=nutriguide_pdf

# Redis 配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 安全配置
SECRET_KEY=your-secret-key-change-this
```

### 3. 启动依赖服务

```bash
# 启动 MongoDB
mongod --dbpath /path/to/data

# 启动 Redis
redis-server

# 或使用 Docker
docker run -d -p 27017:27017 mongo
docker run -d -p 6379:6379 redis
```

### 4. 运行服务

```bash
# 启动主应用
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动 Celery Worker (新终端)
celery -A celery_app worker --loglevel=info

# 启动 Celery Beat (定时任务, 可选)
celery -A celery_app beat --loglevel=info
```

## 🐳 Docker 部署

### 1. 构建镜像

```bash
docker build -t nutriguide-pdf-parser .
```

### 2. 使用 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://mongo:27017
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - mongo
      - redis

  worker:
    build: .
    command: celery -A celery_app worker --loglevel=info
    environment:
      - MONGODB_URL=mongodb://mongo:27017
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - mongo
      - redis

  mongo:
    image: mongo:latest
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:latest
    ports:
      - "6379:6379"

volumes:
  mongo_data:
```

启动：
```bash
docker-compose up -d
```

## 🔧 配置说明

### 核心配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `ENVIRONMENT` | development | 运行环境 |
| `MAX_FILE_SIZE` | 52428800 | 最大文件大小 (50MB) |
| `MAX_FILE_SIZE_SYNC` | 5242880 | 同步处理文件大小限制 (5MB) |
| `OCR_ENABLED` | true | 是否启用 OCR |
| `RATE_LIMIT_ENABLED` | true | 是否启用限流 |
| `RATE_LIMIT_PER_MINUTE` | 100 | 每分钟请求限制 |

### PDF 解析配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `DEFAULT_PARSING_TYPE` | auto | 默认解析类型 |
| `TESSERACT_CMD` | /usr/bin/tesseract | Tesseract 命令路径 |
| `TESSERACT_LANGUAGES` | eng+chi_sim | OCR 识别语言 |

### 性能调优

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `CELERY_TASK_TIME_LIMIT` | 1800 | 任务超时时间 (秒) |
| `CELERY_WORKER_PREFETCH_MULTIPLIER` | 1 | Worker 预取任务数 |
| `MONGODB_MAX_POOL_SIZE` | 10 | MongoDB 最大连接池大小 |

## 📊 监控和管理

### 1. 健康检查

```bash
# 基础健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/admin/health/detailed
```

### 2. 性能监控

```bash
# 获取应用指标
curl http://localhost:8000/metrics

# 获取系统指标
curl http://localhost:8000/admin/metrics

# 获取解析统计
curl http://localhost:8000/admin/stats?days=7
```

### 3. 日志查看

```bash
# 查看应用日志
curl http://localhost:8000/admin/logs?level=INFO&lines=100

# 查看文件日志
tail -f logs/app.log
```

## 🔒 安全配置

### 1. 生产环境安全

```bash
# 设置强密钥
SECRET_KEY=your-very-long-random-secret-key

# 限制 CORS 来源
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# 启用 HTTPS (通过反向代理)
```

### 2. 文件安全

```bash
# 限制文件类型
ALLOWED_EXTENSIONS=pdf

# 启用文件验证
# (默认启用，包括签名验证、恶意内容扫描等)
```

### 3. API 安全

```bash
# 启用限流
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=1000

# 安全中间件自动启用
# (包括 XSS 防护、内容类型嗅探防护等)
```

## 🚀 生产部署

### 1. 性能优化

```bash
# 使用 Gunicorn 运行
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 启动多个 Celery Worker
celery -A celery_app worker --concurrency=4 --loglevel=info
```

### 2. 反向代理 (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. 进程管理 (Supervisor)

```ini
# /etc/supervisor/conf.d/pdf_parser.conf
[program:pdf_parser_api]
command=/path/to/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
directory=/path/to/pdf_parser
user=www-data
autostart=true
autorestart=true

[program:pdf_parser_worker]
command=/path/to/venv/bin/celery -A celery_app worker --loglevel=info
directory=/path/to/pdf_parser
user=www-data
autostart=true
autorestart=true
```

## 📈 扩展和维护

### 1. 水平扩展

```bash
# 增加 API 实例
# 使用负载均衡器分发请求

# 增加 Worker 实例
# 启动更多 Celery Worker 进程

# 数据库集群
# 配置 MongoDB 副本集
```

### 2. 数据备份

```bash
# MongoDB 备份
mongodump --uri="mongodb://localhost:27017/nutriguide_pdf" --out backup/

# 恢复
mongorestore --uri="mongodb://localhost:27017/nutriguide_pdf" backup/nutriguide_pdf/
```

### 3. 定期维护

```bash
# 清理旧数据
curl -X POST "http://localhost:8000/admin/cleanup?days=30"

# 导出解析结果
curl "http://localhost:8000/admin/export/results?format=csv" -o results.csv
```

## 🐛 故障排除

### 常见问题

1. **PDF 解析失败**
   - 检查 Tesseract 安装: `tesseract --version`
   - 检查 PDF 文件有效性
   - 查看详细错误日志

2. **Celery 任务不执行**
   - 检查 Redis 连接: `redis-cli ping`
   - 检查 Worker 是否运行: `celery -A celery_app inspect active`
   - 查看 Worker 日志

3. **数据库连接失败**
   - 检查 MongoDB 服务: `mongosh`
   - 验证连接字符串格式
   - 检查网络访问权限

4. **内存使用过高**
   - 调整 Celery Worker 数量
   - 限制并发任务数
   - 增加系统内存

### 日志调试

```bash
# 增加日志级别
LOG_LEVEL=DEBUG

# 查看特定模块日志
grep "pdf_parser" logs/app.log

# 实时监控
tail -f logs/app.log | grep ERROR
```

## 📞 支持

如遇问题，请：
1. 查看日志文件
2. 检查配置文件
3. 参考 API 文档: `http://localhost:8000/docs`
4. 提交 Issue

---

**版本**: 1.0.0  
**更新日期**: 2025-06-05 