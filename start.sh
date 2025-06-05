#!/bin/bash

# 🚀 PDF Parser Service Startup Script
# 独立的PDF解析服务启动脚本

set -e

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}"
    echo "██████╗ ██████╗ ███████╗    ██████╗  █████╗ ██████╗ ███████╗███████╗██████╗ "
    echo "██╔══██╗██╔══██╗██╔════╝    ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗"
    echo "██████╔╝██║  ██║█████╗      ██████╔╝███████║██████╔╝███████╗█████╗  ██████╔╝"
    echo "██╔═══╝ ██║  ██║██╔══╝      ██╔═══╝ ██╔══██║██╔══██╗╚════██║██╔══╝  ██╔══██╗"
    echo "██║     ██████╔╝██║         ██║     ██║  ██║██║  ██║███████║███████╗██║  ██║"
    echo "╚═╝     ╚═════╝ ╚═╝         ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝"
    echo -e "${NC}"
    echo -e "${CYAN}📄 PDF Parser Microservice${NC}"
    echo ""
}

show_usage() {
    cat << EOF
使用方法: $0 [选项]

选项:
  --env ENV     指定环境 (dev/qa/prod，默认: dev)
  --port PORT   指定端口 (默认: 7800)
  --setup       初始化环境和依赖
  --daemon      后台运行 (默认)
  --foreground  前台运行
  --logs        显示日志
  --help        显示此帮助信息

示例:
  $0                      # 启动开发环境
  $0 --env prod           # 启动生产环境
  $0 --setup              # 初始化环境
  $0 --port 7801          # 指定端口启动
  $0 --logs               # 启动并显示日志

EOF
}

check_dependencies() {
    log_step "检查依赖..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        log_error "pip 未安装"
        exit 1
    fi
    
    log_info "✓ 依赖检查通过"
}

setup_environment() {
    log_step "设置环境..."
    
    # 创建虚拟环境
    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    log_info "安装依赖包..."
    pip install -r requirements.txt
    
    deactivate
    
    # 创建必要目录
    mkdir -p logs uploads temp static templates
    
    # 创建环境配置
    if [ ! -f ".env" ]; then
        log_info "创建环境配置文件..."
        cat > .env << EOF
# PDF Parser 环境配置
ENVIRONMENT=$ENVIRONMENT
DEBUG=$([ "$ENVIRONMENT" = "dev" ] && echo "true" || echo "false")
HOST=0.0.0.0
PORT=$PORT

# 数据库配置
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=nutriguide_pdf

# Redis 配置
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# 文件处理配置
MAX_FILE_SIZE=52428800
MAX_FILE_SIZE_SYNC=5242880
ALLOWED_EXTENSIONS=pdf

# 安全配置
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "fallback-secret-key-$(date +%s)")
CORS_ORIGINS=*

# 功能开关
OCR_ENABLED=true
RATE_LIMIT_ENABLED=true
METRICS_ENABLED=true
CLEANUP_ENABLED=true
EOF
    fi
    
    log_info "✓ 环境设置完成"
}

check_services() {
    log_step "检查外部服务..."
    
    # 检查MongoDB
    if ! nc -z localhost 27017 2>/dev/null; then
        log_warn "MongoDB 服务未运行 (localhost:27017)"
        log_warn "请先启动 MongoDB 服务"
    else
        log_info "✓ MongoDB 服务运行中"
    fi
    
    # 检查Redis
    if ! nc -z localhost 6379 2>/dev/null; then
        log_warn "Redis 服务未运行 (localhost:6379)"
        log_warn "请先启动 Redis 服务"
    else
        log_info "✓ Redis 服务运行中"
    fi
}

start_services() {
    log_step "启动 PDF Parser 服务..."
    
    # 检查端口占用
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warn "端口 $PORT 已被占用，停止现有进程..."
        kill -9 $(lsof -t -i:$PORT) 2>/dev/null || true
        sleep 2
    fi
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 启动API服务
    log_info "启动 PDF Parser API (端口: $PORT)..."
    if [ "$DAEMON" = true ]; then
        nohup uvicorn main:app --host 0.0.0.0 --port $PORT --reload > logs/api.log 2>&1 &
        API_PID=$!
        echo $API_PID > logs/api.pid
        log_info "✓ API 服务已启动 (PID: $API_PID)"
    else
        uvicorn main:app --host 0.0.0.0 --port $PORT --reload &
        API_PID=$!
        echo $API_PID > logs/api.pid
    fi
    
    # 启动 Celery Worker
    log_info "启动 Celery Worker..."
    if [ "$DAEMON" = true ]; then
        nohup celery -A celery_app worker --loglevel=info > logs/worker.log 2>&1 &
        WORKER_PID=$!
        echo $WORKER_PID > logs/worker.pid
        log_info "✓ Celery Worker 已启动 (PID: $WORKER_PID)"
    else
        celery -A celery_app worker --loglevel=info &
        WORKER_PID=$!
        echo $WORKER_PID > logs/worker.pid
    fi
    
    # 生产环境启动定时任务
    if [ "$ENVIRONMENT" = "prod" ]; then
        log_info "启动 Celery Beat..."
        if [ "$DAEMON" = true ]; then
            nohup celery -A celery_app beat --loglevel=info > logs/beat.log 2>&1 &
            BEAT_PID=$!
            echo $BEAT_PID > logs/beat.pid
            log_info "✓ Celery Beat 已启动 (PID: $BEAT_PID)"
        else
            celery -A celery_app beat --loglevel=info &
            BEAT_PID=$!
            echo $BEAT_PID > logs/beat.pid
        fi
    fi
    
    deactivate
    
    # 等待服务启动
    sleep 3
    
    # 健康检查
    if curl -s "http://localhost:$PORT/health" > /dev/null; then
        log_info "✓ 服务健康检查通过"
    else
        log_warn "服务可能未正常启动，请检查日志"
    fi
}

show_status() {
    echo -e "${CYAN}======================================${NC}"
    echo -e "${CYAN}  PDF Parser 服务状态${NC}"
    echo -e "${CYAN}======================================${NC}"
    
    # API 状态
    if curl -s "http://localhost:$PORT/health" > /dev/null; then
        echo -e "${GREEN}✓ API 服务: 运行中${NC}"
    else
        echo -e "${RED}✗ API 服务: 未运行${NC}"
    fi
    
    # Worker 状态
    if [ -f "logs/worker.pid" ]; then
        WORKER_PID=$(cat logs/worker.pid)
        if ps -p $WORKER_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Celery Worker: 运行中 (PID: $WORKER_PID)${NC}"
        else
            echo -e "${RED}✗ Celery Worker: 未运行${NC}"
        fi
    else
        echo -e "${RED}✗ Celery Worker: 未启动${NC}"
    fi
    
    # Beat 状态 (生产环境)
    if [ "$ENVIRONMENT" = "prod" ] && [ -f "logs/beat.pid" ]; then
        BEAT_PID=$(cat logs/beat.pid)
        if ps -p $BEAT_PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Celery Beat: 运行中 (PID: $BEAT_PID)${NC}"
        else
            echo -e "${RED}✗ Celery Beat: 未运行${NC}"
        fi
    fi
    
    echo ""
    echo -e "${CYAN}======================================${NC}"
    echo -e "${CYAN}  访问地址${NC}"
    echo -e "${CYAN}======================================${NC}"
    echo -e "${GREEN}📄 API 服务:${NC}          http://localhost:$PORT"
    echo -e "${GREEN}📚 API 文档:${NC}          http://localhost:$PORT/docs"
    echo -e "${GREEN}⚡ 管理界面:${NC}          http://localhost:$PORT/admin/metrics"
    echo -e "${GREEN}❤️ 健康检查:${NC}          http://localhost:$PORT/health"
    echo ""
}

show_logs() {
    log_step "显示服务日志..."
    
    if [ "$DAEMON" = true ]; then
        echo -e "${CYAN}API 日志:${NC}"
        tail -f logs/api.log &
        
        echo -e "${CYAN}Worker 日志:${NC}"
        tail -f logs/worker.log &
        
        if [ "$ENVIRONMENT" = "prod" ] && [ -f "logs/beat.log" ]; then
            echo -e "${CYAN}Beat 日志:${NC}"
            tail -f logs/beat.log &
        fi
        
        wait
    else
        log_info "服务在前台运行，日志直接输出"
    fi
}

# ==================== 参数解析 ==================== #

ENVIRONMENT="dev"
PORT=7800
SETUP_ENV=false
DAEMON=true
SHOW_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --setup)
            SETUP_ENV=true
            shift
            ;;
        --daemon)
            DAEMON=true
            shift
            ;;
        --foreground)
            DAEMON=false
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --help)
            print_header
            show_usage
            exit 0
            ;;
        *)
            log_error "未知参数: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 根据环境调整端口
case $ENVIRONMENT in
    "dev")
        PORT=${PORT:-7800}
        ;;
    "qa")
        PORT=${PORT:-7801}
        ;;
    "prod")
        PORT=${PORT:-7802}
        ;;
esac

# ==================== 主执行流程 ==================== #

main() {
    print_header
    
    log_info "环境: $ENVIRONMENT"
    log_info "端口: $PORT"
    
    # 检查依赖
    check_dependencies
    
    # 设置环境
    if [ "$SETUP_ENV" = true ] || [ ! -d "venv" ]; then
        setup_environment
    fi
    
    # 检查外部服务
    check_services
    
    # 启动服务
    start_services
    
    # 显示状态
    show_status
    
    # 显示日志
    if [ "$SHOW_LOGS" = true ]; then
        show_logs
    elif [ "$DAEMON" = false ]; then
        log_info "按 Ctrl+C 停止服务"
        wait
    fi
}

# 执行主函数
main "$@" 