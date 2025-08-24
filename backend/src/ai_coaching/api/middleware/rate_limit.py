"""Rate limiting middleware for API endpoints."""

import time
from typing import Dict, Optional
from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware.
    
    In production, this should use Redis or another distributed cache.
    """
    
    def __init__(self, app, default_requests_per_minute: int = 100):
        """Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            default_requests_per_minute: Default rate limit
        """
        super().__init__(app)
        self.default_rpm = default_requests_per_minute
        self.request_counts: Dict[str, Dict[str, any]] = {}
        
        # Path-specific rate limits (requests per minute)
        self.path_limits = {
            "/api/v1/gmail/webhook": 600,  # Gmail webhooks can be frequent
            "/api/v1/gmail/process-email": 60,  # Manual email processing
            "/api/v1/auth/google": 20,  # OAuth endpoints
            "/api/v1/health": 1000,  # Health checks
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response or rate limit error
        """
        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)
        
        # Get path-specific rate limit
        path = request.url.path
        rate_limit = self._get_rate_limit_for_path(path)
        
        # Check rate limit
        if not self._check_rate_limit(client_ip, path, rate_limit):
            logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=path,
                rate_limit=rate_limit
            )
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": rate_limit,
                    "window": "1 minute",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Process request
        response = await call_next(request)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def _get_rate_limit_for_path(self, path: str) -> int:
        """Get rate limit for specific path.
        
        Args:
            path: Request path
            
        Returns:
            Rate limit (requests per minute)
        """
        # Check exact path matches
        if path in self.path_limits:
            return self.path_limits[path]
        
        # Check path patterns
        for pattern, limit in self.path_limits.items():
            if path.startswith(pattern):
                return limit
        
        return self.default_rpm
    
    def _check_rate_limit(self, client_ip: str, path: str, limit: int) -> bool:
        """Check if client is within rate limit.
        
        Args:
            client_ip: Client IP address
            path: Request path
            limit: Rate limit (requests per minute)
            
        Returns:
            True if within limit, False otherwise
        """
        current_time = time.time()
        minute_window = int(current_time // 60)
        
        # Create client key
        client_key = f"{client_ip}:{path}"
        
        # Initialize tracking if needed
        if client_key not in self.request_counts:
            self.request_counts[client_key] = {
                "count": 0,
                "window": minute_window
            }
        
        client_data = self.request_counts[client_key]
        
        # Reset counter if new minute window
        if client_data["window"] != minute_window:
            client_data["count"] = 0
            client_data["window"] = minute_window
        
        # Check if within limit
        if client_data["count"] >= limit:
            return False
        
        # Increment counter
        client_data["count"] += 1
        
        # Clean up old entries (simple cleanup every 100 requests)
        if len(self.request_counts) > 1000:
            self._cleanup_old_entries(current_time)
        
        return True
    
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old rate limiting entries.
        
        Args:
            current_time: Current timestamp
        """
        current_minute = int(current_time // 60)
        
        # Remove entries older than 2 minutes
        expired_keys = [
            key for key, data in self.request_counts.items()
            if current_minute - data["window"] > 2
        ]
        
        for key in expired_keys:
            del self.request_counts[key]
        
        logger.debug("Cleaned up rate limit entries", removed_count=len(expired_keys))