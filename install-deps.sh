#!/bin/bash

# 智能依赖安装脚本
echo "📦 智能安装 PDF Parser 依赖..."

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ 虚拟环境已激活"
else
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv venv"
    exit 1
fi

# 升级pip
echo "⬆️ 升级pip..."
pip install --upgrade pip

# 安装基础依赖（除了有问题的包）
echo "📥 安装基础依赖..."
pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    pymongo==4.6.0 \
    motor==3.3.2 \
    jinja2==3.1.2 \
    pdfplumber==0.10.3 \
    pytesseract==0.3.10 \
    PyPDF2==3.0.1 \
    pdfminer.six==20231228 \
    celery==5.3.4 \
    redis==5.0.1 \
    python-multipart==0.0.6 \
    aiofiles==23.2.1 \
    pillow==10.1.0 \
    pandas==2.1.4 \
    numpy==1.26.2 \
    openpyxl==3.1.2 \
    python-dotenv==1.0.0 \
    requests==2.31.0 \
    httpx==0.25.2 \
    loguru==0.7.2 \
    jieba==0.42.1 \
    regex==2023.10.3 \
    psutil==5.9.6 \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1

# 尝试安装 PyMuPDF（可能失败）
echo "🔧 尝试安装 PyMuPDF..."
if pip install PyMuPDF==1.23.8; then
    echo "✅ PyMuPDF 安装成功"
else
    echo "⚠️ PyMuPDF 安装失败，将使用备用PDF解析库"
    echo "📝 备用方案: pdfplumber + PyPDF2 + pdfminer.six"
fi

# 尝试安装 OpenCV（可能失败）
echo "🔧 尝试安装 OpenCV..."
if pip install opencv-python==4.8.1.78; then
    echo "✅ OpenCV 安装成功"
else
    echo "⚠️ OpenCV 安装失败，图像处理功能可能受限"
    # 尝试安装简化版本
    pip install opencv-python-headless || echo "❌ OpenCV 完全安装失败"
fi

# 尝试安装 python-magic
echo "🔧 尝试安装 python-magic..."
if pip install python-magic==0.4.27; then
    echo "✅ python-magic 安装成功"
else
    echo "⚠️ python-magic 安装失败，文件类型检测功能可能受限"
fi

echo ""
echo "✅ 依赖安装完成！"
echo ""
echo "📋 安装总结："
pip list | grep -E "(fastapi|uvicorn|pdfplumber|PyMuPDF|opencv|celery|redis|pymongo)"
echo ""
echo "🚀 现在可以运行: ./local-dev.sh" 