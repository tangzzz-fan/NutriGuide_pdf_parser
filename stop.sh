#!/bin/bash

# 🛑 PDF Parser Service Stop Script
# PDF解析服务停止脚本

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
    echo "███████╗████████╗ ██████╗ ██████╗     ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗"
    echo "██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗    ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝"
    echo "███████╗   ██║   ██║   ██║██████╔╝    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  "
    echo "╚════██║   ██║   ██║   ██║██╔═══╝     ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  "
    echo "███████║   ██║   ╚██████╔╝██║         ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗"
    echo "╚══════╝   ╚═╝    ╚═════╝ ╚═╝         ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝"
    echo -e "${NC}"
    echo -e "${CYAN}🛑 PDF Parser Service Stop${NC}"
    echo ""
}

show_usage() {
    cat << EOF
使用方法: $0 [选项]

选项:
  --force       强制停止所有相关进程
  --clean       清理日志和临时文件
  --port PORT   指定要停止的端口服务
  --help        显示此帮助信息

示例:
  $0              # 停止所有PDF Parser服务
  $0 --force      # 强制停止所有进程
  $0 --clean      # 停止服务并清理文件
  $0 --port 7800  # 停止指定端口的服务

EOF
}

stop_by_pid() {
    local pid_file=$1
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            log_info "停止 $service_name (PID: $pid)..."
            kill $pid
            
            # 等待进程停止
            local count=0
            while ps -p $pid > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # 如果仍在运行，强制停止
            if ps -p $pid > /dev/null 2>&1; then
                if [ "$FORCE_STOP" = true ]; then
                    log_warn "强制停止 $service_name (PID: $pid)..."
                    kill -9 $pid
                else
                    log_warn "$service_name 未能正常停止，使用 --force 强制停止"
                fi
            fi
            
            if ! ps -p $pid > /dev/null 2>&1; then
                log_info "✓ $service_name 已停止"
            fi
        else
            log_warn "$service_name PID文件存在但进程未运行"
        fi
        
        rm -f "$pid_file"
    else
        log_warn "$service_name PID文件不存在"
    fi
}

stop_by_port() {
    local port=$1
    
    log_step "停止端口 $port 上的服务..."
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pids=$(lsof -t -i:$port)
        for pid in $pids; do
            log_info "停止端口 $port 上的进程 (PID: $pid)..."
            if [ "$FORCE_STOP" = true ]; then
                kill -9 $pid 2>/dev/null || true
            else
                kill $pid 2>/dev/null || true
            fi
        done
        
        sleep 2
        
        if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            log_info "✓ 端口 $port 上的服务已停止"
        else
            log_warn "端口 $port 上仍有服务运行"
        fi
    else
        log_info "端口 $port 上没有运行的服务"
    fi
}

stop_all_services() {
    log_step "停止所有 PDF Parser 服务..."
    
    # 停止API服务
    stop_by_pid "logs/api.pid" "PDF Parser API"
    
    # 停止Celery Worker
    stop_by_pid "logs/worker.pid" "Celery Worker"
    
    # 停止Celery Beat
    stop_by_pid "logs/beat.pid" "Celery Beat"
    
    # 检查常用端口
    local ports=("7800" "7801" "7802")
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            local pids=$(lsof -t -i:$port)
            for pid in $pids; do
                # 检查是否为Python/Uvicorn/Celery进程
                local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "")
                if [[ "$cmd" == "python"* ]] || [[ "$cmd" == "uvicorn"* ]] || [[ "$cmd" == "celery"* ]]; then
                    log_info "发现可能的PDF Parser进程在端口 $port (PID: $pid)，正在停止..."
                    if [ "$FORCE_STOP" = true ]; then
                        kill -9 $pid 2>/dev/null || true
                    else
                        kill $pid 2>/dev/null || true
                    fi
                fi
            done
        fi
    done
}

cleanup_files() {
    if [ "$CLEAN_FILES" = true ]; then
        log_step "清理文件..."
        
        # 清理日志文件
        if [ -d "logs" ]; then
            log_info "清理日志文件..."
            rm -f logs/*.log
            rm -f logs/*.pid
        fi
        
        # 清理临时文件
        if [ -d "temp" ]; then
            log_info "清理临时文件..."
            rm -rf temp/*
        fi
        
        # 清理上传文件 (可选)
        read -p "是否清理上传的文件？(y/N): " confirm
        if [[ $confirm =~ ^[Yy]$ ]] && [ -d "uploads" ]; then
            log_info "清理上传文件..."
            rm -rf uploads/*
        fi
        
        log_info "✓ 文件清理完成"
    fi
}

show_status() {
    log_step "检查服务状态..."
    
    local any_running=false
    
    # 检查PID文件
    local pid_files=("logs/api.pid" "logs/worker.pid" "logs/beat.pid")
    local service_names=("PDF Parser API" "Celery Worker" "Celery Beat")
    
    for i in "${!pid_files[@]}"; do
        local pid_file="${pid_files[$i]}"
        local service_name="${service_names[$i]}"
        
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ps -p $pid > /dev/null 2>&1; then
                echo -e "${RED}✗ $service_name: 仍在运行 (PID: $pid)${NC}"
                any_running=true
            else
                echo -e "${GREEN}✓ $service_name: 已停止${NC}"
            fi
        else
            echo -e "${GREEN}✓ $service_name: 已停止${NC}"
        fi
    done
    
    # 检查端口
    local ports=("7800" "7801" "7802")
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${RED}✗ 端口 $port: 仍有服务运行${NC}"
            any_running=true
        fi
    done
    
    echo ""
    if [ "$any_running" = false ]; then
        echo -e "${GREEN}✅ 所有PDF Parser服务已停止${NC}"
    else
        echo -e "${YELLOW}⚠️ 部分服务可能仍在运行，使用 --force 强制停止${NC}"
    fi
}

# ==================== 参数解析 ==================== #

FORCE_STOP=false
CLEAN_FILES=false
SPECIFIC_PORT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_STOP=true
            shift
            ;;
        --clean)
            CLEAN_FILES=true
            shift
            ;;
        --port)
            SPECIFIC_PORT="$2"
            shift 2
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

# ==================== 主执行流程 ==================== #

main() {
    print_header
    
    if [ -n "$SPECIFIC_PORT" ]; then
        # 停止指定端口的服务
        stop_by_port "$SPECIFIC_PORT"
    else
        # 停止所有服务
        stop_all_services
    fi
    
    # 等待进程完全停止
    sleep 2
    
    # 清理文件
    cleanup_files
    
    # 显示最终状态
    show_status
    
    log_info "停止操作完成"
}

# 执行主函数
main "$@" 