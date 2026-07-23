from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import uuid
import time
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware to handle tenant identification"""
    
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID") or request.query_params.get("tenant_id") or "default"
        request.state.tenant_id = tenant_id
        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to each request"""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} - Processed in {process_time:.3f}s")
        
        response.headers["X-Process-Time"] = str(process_time)
        return response

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect and expose metrics about requests"""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = defaultdict(int)
        self.error_count = defaultdict(int)
        self.response_times = []
        self.start_time = datetime.now()
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path
        
        # Increment request count
        self.request_count[f"{method}:{path}"] += 1
        
        try:
            response = await call_next(request)
            
            # Track errors
            if response.status_code >= 400:
                self.error_count[f"{method}:{path}"] += 1
            
            # Track response time
            elapsed = time.time() - start_time
            self.response_times.append(elapsed)
            
            # Keep only last 1000 response times
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            # Add metrics to response headers
            response.headers["X-Request-Count"] = str(self.request_count[f"{method}:{path}"])
            response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
            
            return response
            
        except Exception as e:
            self.error_count[f"{method}:{path}"] += 1
            raise e
    
    def get_metrics(self):
        """Get current metrics"""
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        return {
            "total_requests": sum(self.request_count.values()),
            "total_errors": sum(self.error_count.values()),
            "avg_response_time": avg_response_time,
            "request_count_by_endpoint": dict(self.request_count),
            "error_count_by_endpoint": dict(self.error_count),
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds()
        }

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to implement rate limiting per tenant"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        # Store request counts per tenant with timestamps
        self.tenant_requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        # Get tenant ID from request state (set by TenantMiddleware)
        tenant_id = getattr(request.state, 'tenant_id', 'default')
        
        # Get current time
        current_time = datetime.now()
        
        # Clean up old requests (older than 1 minute)
        minute_ago = current_time - timedelta(minutes=1)
        self.tenant_requests[tenant_id] = [
            timestamp for timestamp in self.tenant_requests[tenant_id]
            if timestamp > minute_ago
        ]
        
        # Check if rate limit is exceeded
        if len(self.tenant_requests[tenant_id]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for tenant: {tenant_id}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute."
            )
        
        # Add current request timestamp
        self.tenant_requests[tenant_id].append(current_time)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.tenant_requests[tenant_id])
        )
        
        return response
    
    def get_rate_limit_status(self, tenant_id: str = None):
        """Get rate limit status for a tenant"""
        if tenant_id is None:
            return {tenant: len(requests) for tenant, requests in self.tenant_requests.items()}
        return len(self.tenant_requests.get(tenant_id, []))