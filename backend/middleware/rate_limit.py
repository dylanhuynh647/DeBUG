"""
Rate limiting middleware for API endpoints
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import time

# Rate limit storage: {endpoint: {ip: [(timestamp, count)]}}
rate_limit_store: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))

# Rate limit configurations
RATE_LIMITS = {
    "/api/auth": {"requests": 5, "window": 60},  # 5 requests per minute
    "/api/bugs": {"requests": 20, "window": 60},  # 20 requests per minute
    "/api/artifacts": {"requests": 20, "window": 60},
    "/api/user": {"requests": 10, "window": 60},
    "default": {"requests": 30, "window": 60},  # 30 requests per minute default
}

def get_rate_limit_config(path: str) -> Dict[str, int]:
    """Get rate limit configuration for a path"""
    for endpoint, config in RATE_LIMITS.items():
        if path.startswith(endpoint):
            return config
    return RATE_LIMITS["default"]

def get_client_identifier(request: Request) -> str:
    """Get client identifier for rate limiting"""
    # Use IP address for rate limiting
    # In production, consider using user ID for authenticated requests
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Skip rate limiting for health checks
    if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
        return await call_next(request)
    
    client_id = get_client_identifier(request)
    path = request.url.path
    config = get_rate_limit_config(path)
    
    now = time.time()
    window_start = now - config["window"]
    
    # Clean old entries
    if path in rate_limit_store and client_id in rate_limit_store[path]:
        rate_limit_store[path][client_id] = [
            ts for ts in rate_limit_store[path][client_id]
            if ts > window_start
        ]
    
    # Count requests in window
    request_count = len(rate_limit_store[path][client_id])
    
    if request_count >= config["requests"]:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": f"Rate limit exceeded: {config['requests']} requests per {config['window']} seconds"
            },
            headers={
                "X-RateLimit-Limit": str(config["requests"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(now + config["window"]))
            }
        )
    
    # Add current request
    rate_limit_store[path][client_id].append(now)
    
    # Add rate limit headers
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(config["requests"])
    response.headers["X-RateLimit-Remaining"] = str(config["requests"] - request_count - 1)
    response.headers["X-RateLimit-Reset"] = str(int(now + config["window"]))
    
    return response
