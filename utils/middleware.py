"""
API 中间件
提供限流、监控、安全检查等功能
"""

import time
import asyncio
from typing import Callable, Dict, Any
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as redis
from collections import defaultdict, deque
import json

from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """API 限流中间件"""
    
    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client
        self.local_cache = defaultdict(lambda: {"requests": deque(), "blocked_until": 0})
        self.per_minute_limit = settings.rate_limit_per_minute
        self.per_hour_limit = settings.rate_limit_per_hour
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        client_ip = self.get_client_ip(request)
        current_time = time.time()
        
        # 检查是否被封禁
        if self.is_blocked(client_ip, current_time):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": "API rate limit exceeded. Please try again later.",
                    "retry_after": 60
                }
            )
        
        # 检查限流
        if await self.is_rate_limited(client_ip, current_time):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate Limited",
                    "message": f"Request limit exceeded: {self.per_minute_limit}/minute",
                    "retry_after": 60
                }
            )
        
        # 记录请求
        await self.record_request(client_ip, current_time)
        
        # 执行请求
        response = await call_next(request)
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def is_blocked(self, client_ip: str, current_time: float) -> bool:
        """检查IP是否被封禁"""
        cache_data = self.local_cache[client_ip]
        return current_time < cache_data["blocked_until"]
    
    async def is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """检查是否触发限流"""
        if self.redis_client:
            return await self.redis_rate_limit_check(client_ip, current_time)
        else:
            return self.local_rate_limit_check(client_ip, current_time)
    
    def local_rate_limit_check(self, client_ip: str, current_time: float) -> bool:
        """本地限流检查"""
        cache_data = self.local_cache[client_ip]
        requests = cache_data["requests"]
        
        # 清理过期请求
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        while requests and requests[0] < hour_ago:
            requests.popleft()
        
        # 检查每分钟限制
        minute_requests = sum(1 for req_time in requests if req_time > minute_ago)
        if minute_requests >= self.per_minute_limit:
            return True
        
        # 检查每小时限制
        if len(requests) >= self.per_hour_limit:
            return True
        
        return False
    
    async def redis_rate_limit_check(self, client_ip: str, current_time: float) -> bool:
        """Redis限流检查"""
        try:
            minute_key = f"rate_limit:{client_ip}:minute"
            hour_key = f"rate_limit:{client_ip}:hour"
            
            # 检查每分钟限制
            minute_count = await self.redis_client.get(minute_key)
            if minute_count and int(minute_count) >= self.per_minute_limit:
                return True
            
            # 检查每小时限制
            hour_count = await self.redis_client.get(hour_key)
            if hour_count and int(hour_count) >= self.per_hour_limit:
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Redis限流检查失败: {e}")
            return self.local_rate_limit_check(client_ip, current_time)
    
    async def record_request(self, client_ip: str, current_time: float):
        """记录请求"""
        if self.redis_client:
            await self.redis_record_request(client_ip)
        else:
            self.local_record_request(client_ip, current_time)
    
    def local_record_request(self, client_ip: str, current_time: float):
        """本地记录请求"""
        cache_data = self.local_cache[client_ip]
        cache_data["requests"].append(current_time)
    
    async def redis_record_request(self, client_ip: str):
        """Redis记录请求"""
        try:
            minute_key = f"rate_limit:{client_ip}:minute"
            hour_key = f"rate_limit:{client_ip}:hour"
            
            # 增加计数
            pipe = self.redis_client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)
            await pipe.execute()
            
        except Exception as e:
            logger.warning(f"Redis记录请求失败: {e}")


class MetricsMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics = {
            "request_count": 0,
            "total_duration": 0,
            "error_count": 0,
            "endpoint_stats": defaultdict(lambda: {
                "count": 0,
                "total_duration": 0,
                "error_count": 0
            })
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.metrics_enabled:
            return await call_next(request)
        
        start_time = time.time()
        
        # 执行请求
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"请求处理出错: {e}")
            status_code = 500
            response = JSONResponse(
                status_code=500,
                content={"error": "Internal Server Error"}
            )
        
        # 计算耗时
        duration = time.time() - start_time
        
        # 更新指标
        self.update_metrics(request, duration, status_code)
        
        # 添加响应头
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response
    
    def update_metrics(self, request: Request, duration: float, status_code: int):
        """更新性能指标"""
        endpoint = f"{request.method} {request.url.path}"
        
        # 全局指标
        self.metrics["request_count"] += 1
        self.metrics["total_duration"] += duration
        
        if status_code >= 400:
            self.metrics["error_count"] += 1
        
        # 端点指标
        endpoint_stats = self.metrics["endpoint_stats"][endpoint]
        endpoint_stats["count"] += 1
        endpoint_stats["total_duration"] += duration
        
        if status_code >= 400:
            endpoint_stats["error_count"] += 1
        
        # 记录慢请求
        if duration > getattr(settings, "slow_request_threshold", 5.0):
            logger.warning(f"慢请求检测: {endpoint} - {duration:.3f}s")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        result = {
            "total_requests": self.metrics["request_count"],
            "total_errors": self.metrics["error_count"],
            "average_response_time": (
                self.metrics["total_duration"] / self.metrics["request_count"]
                if self.metrics["request_count"] > 0 else 0
            ),
            "error_rate": (
                self.metrics["error_count"] / self.metrics["request_count"] * 100
                if self.metrics["request_count"] > 0 else 0
            ),
            "endpoints": {}
        }
        
        for endpoint, stats in self.metrics["endpoint_stats"].items():
            result["endpoints"][endpoint] = {
                "requests": stats["count"],
                "errors": stats["error_count"],
                "average_response_time": (
                    stats["total_duration"] / stats["count"]
                    if stats["count"] > 0 else 0
                ),
                "error_rate": (
                    stats["error_count"] / stats["count"] * 100
                    if stats["count"] > 0 else 0
                )
            }
        
        return result


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.blocked_ips = set()
        self.suspicious_patterns = [
            "sql injection", "union select", "script>", "<iframe",
            "../../../", "etc/passwd", "cmd.exe", "powershell"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self.get_client_ip(request)
        
        # 检查被封禁的IP
        if client_ip in self.blocked_ips:
            logger.warning(f"被封禁的IP尝试访问: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"error": "Access Denied"}
            )
        
        # 安全检查
        if self.security_check(request):
            logger.warning(f"可疑请求检测: {client_ip} - {request.url}")
            self.blocked_ips.add(client_ip)
            return JSONResponse(
                status_code=403,
                content={"error": "Security violation detected"}
            )
        
        response = await call_next(request)
        
        # 添加安全头
        self.add_security_headers(response)
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def security_check(self, request: Request) -> bool:
        """安全检查"""
        # 检查URL
        url_str = str(request.url).lower()
        for pattern in self.suspicious_patterns:
            if pattern in url_str:
                return True
        
        # 检查User-Agent
        user_agent = request.headers.get("User-Agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "burp"]
        if any(agent in user_agent for agent in suspicious_agents):
            return True
        
        # 检查请求头
        for header_name, header_value in request.headers.items():
            header_value_lower = header_value.lower()
            for pattern in self.suspicious_patterns:
                if pattern in header_value_lower:
                    return True
        
        return False
    
    def add_security_headers(self, response: Response):
        """添加安全头"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        
        # 记录请求开始
        logger.info(f"请求开始: {request.method} {request.url.path} - {client_ip}")
        
        # 执行请求
        response = await call_next(request)
        
        # 计算耗时
        duration = time.time() - start_time
        
        # 记录请求完成
        logger.info(
            f"请求完成: {request.method} {request.url.path} - "
            f"{response.status_code} - {duration:.3f}s - {client_ip}"
        )
        
        return response


# 全局指标收集器
metrics_collector = None

def get_metrics_collector():
    """获取指标收集器"""
    global metrics_collector
    return metrics_collector

def set_metrics_collector(collector):
    """设置指标收集器"""
    global metrics_collector
    metrics_collector = collector 