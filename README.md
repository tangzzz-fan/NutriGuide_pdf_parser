# 📄 NutriGuide PDF Parser Service

## 📖 项目简介

NutriGuide PDF 解析微服务，基于 Python + FastAPI 构建，专门处理营养标签、食品成分表等 PDF 文档的智能解析和数据提取。

## 🏗️ 技术栈

- **框架**: FastAPI + Python 3.11+
- **队列**: Celery + Redis
- **PDF解析**: PyPDF2, pdfplumber, pytesseract
- **AI/OCR**: Tesseract OCR, OpenCV
- **异步**: asyncio, aioredis
- **容器**: Docker
- **测试**: pytest, pytest-asyncio

## 🚀 快速开始

### 本地开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动Celery Worker (新终端)
celery -A main.celery worker --loglevel=info
```

### Docker 开发

```bash
# 构建镜像
docker build -t nutriguide-pdf-parser .

# 运行容器
docker run -p 8000:8000 nutriguide-pdf-parser
```

## 📚 API 文档

启动服务后访问：
- 开发环境: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

## 🔧 环境配置

### 环境变量

创建对应的环境配置文件：

```bash
# .env.development
ENVIRONMENT=development
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379
LOG_LEVEL=DEBUG
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=pdf,PDF

# .env.production
ENVIRONMENT=production
REDIS_URL=redis://your-prod-host:6379
CELERY_BROKER_URL=redis://your-prod-host:6379
CELERY_RESULT_BACKEND=redis://your-prod-host:6379
LOG_LEVEL=INFO
MAX_FILE_SIZE=10485760
ALLOWED_EXTENSIONS=pdf,PDF
```

## 📊 主要功能模块

### PDF 上传与验证 (`/api/upload`)
- 支持 PDF 文件上传
- 文件格式验证
- 文件大小限制
- 异步处理队列

### 同步解析 (`/api/parse`)
- 实时 PDF 内容提取
- 文本识别与清理
- 营养数据结构化

### 异步解析 (`/api/parse-async`)  
- 大文件异步队列处理
- 任务状态跟踪
- 结果查询接口

### 任务管理 (`/api/tasks`)
- 解析任务状态查询
- 任务结果获取
- 错误信息反馈

## 🏛️ 项目结构

```
.                           
├── main.py                 # FastAPI 应用入口
├── config/
│   └── settings.py         # 配置管理
├── services/
│   ├── pdf_parser.py       # PDF解析核心逻辑
│   ├── text_processor.py   # 文本处理与清理
│   └── data_extractor.py   # 营养数据提取
├── models/
│   ├── request.py          # 请求模型
│   └── response.py         # 响应模型
├── utils/
│   ├── validators.py       # 文件验证工具
│   └── helpers.py          # 通用工具函数
├── tasks/
│   └── celery_tasks.py     # Celery异步任务
├── tests/                  # 测试文件
├── requirements.txt        # Python依赖
└── Dockerfile             # 容器配置
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_pdf_parser.py

# 生成覆盖率报告
pytest --cov=. --cov-report=html

# 异步测试
pytest -v tests/test_async_tasks.py
```

## 📈 性能监控

### 健康检查
```bash
GET /health
GET /health/detailed
```

### 队列监控
```bash
# Celery监控
celery -A main.celery inspect active
celery -A main.celery inspect stats

# Redis监控  
redis-cli monitor
```

### 指标监控
- 处理延迟
- 队列长度
- 成功/失败率
- 内存使用量

## 🔧 核心解析算法

### PDF 文本提取
```python
# 支持多种PDF类型
- 可选择文本PDF (直接提取)
- 扫描图片PDF (OCR识别)
- 混合类型PDF (智能判断)
```

### 营养数据识别
```python
# 营养标签解析
- 热量、蛋白质、脂肪、碳水化合物
- 维生素、矿物质含量
- 过敏原信息
- 营养成分表格化
```

### 数据清理与验证
```python
# 数据后处理
- 单位标准化 (g, mg, μg, IU等)
- 数值范围验证
- 缺失数据补全
- 结构化输出
```

## 🚀 部署

### Docker 部署
```bash
# 构建生产镜像
docker build -t nutriguide-pdf-parser:latest .

# 运行生产容器
docker run -d \
  --name nutriguide-pdf-parser \
  -p 8000:8000 \
  --env-file .env.production \
  nutriguide-pdf-parser:latest

# 运行 Celery Worker
docker run -d \
  --name nutriguide-celery-worker \
  --env-file .env.production \
  nutriguide-pdf-parser:latest \
  celery -A main.celery worker --loglevel=info
```

### 环境要求
- Python 3.11+
- Redis 7.0+
- Tesseract OCR
- Docker (可选)

## 🤝 开发指南

### 代码规范
- Black 代码格式化
- Flake8 代码检查
- Type hints 类型注解
- Docstring 文档字符串

### 提交规范
```bash
# 功能开发
git commit -m "feat: add nutrition label extraction"

# 问题修复
git commit -m "fix: resolve OCR encoding issue"

# 性能优化
git commit -m "perf: improve PDF parsing speed"
```

### API 设计原则
- RESTful 设计
- 异步优先
- 错误处理完善
- 响应格式统一

## 🔍 使用示例

### 同步解析 PDF
```python
import requests

# 上传并解析PDF
with open('nutrition_label.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/api/parse',
        files=files
    )
    
result = response.json()
print(result['nutrition_data'])
```

### 异步解析 PDF
```python
import requests
import time

# 提交异步任务
with open('large_document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post(
        'http://localhost:8000/api/parse-async', 
        files=files
    )

task_id = response.json()['task_id']

# 轮询任务状态
while True:
    status_response = requests.get(
        f'http://localhost:8000/api/tasks/{task_id}'
    )
    status = status_response.json()
    
    if status['state'] == 'SUCCESS':
        print(status['result'])
        break
    elif status['state'] == 'FAILURE':
        print(f"Error: {status['error']}")
        break
        
    time.sleep(2)
```

## 🛠️ 故障排除

### 常见问题

#### 1. OCR 识别效果差
```bash
# 检查 Tesseract 安装
tesseract --version

# 优化图片预处理
- 调整 DPI 设置
- 图像去噪处理  
- 二值化处理
```

#### 2. 队列处理缓慢
```bash
# 增加 Worker 数量
celery -A main.celery worker --concurrency=4

# 检查 Redis 连接
redis-cli ping
```

#### 3. 内存使用过高
```bash
# 限制并发处理
MAX_CONCURRENT_TASKS=2

# 优化PDF加载
- 分页处理
- 流式读取
```

## 📞 支持

- **问题反馈**: 通过 GitHub Issues
- **技术支持**: pdf-team@nutriguide.com
- **文档更新**: 欢迎提交 PR

## 🔬 高级功能

### AI 增强解析
- 使用机器学习模型识别营养标签格式
- 智能字段映射和数据校正
- 多语言营养标签支持

### 批量处理
- 支持多文件并行处理
- 批量任务进度跟踪
- 结果批量导出

### 缓存优化
- Redis 结果缓存
- 相似文档去重
- 智能缓存策略

---

**NutriGuide PDF Parser Team** © 2024 