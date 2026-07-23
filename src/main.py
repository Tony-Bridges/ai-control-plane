from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import uvicorn
import logging
from contextlib import asynccontextmanager

from src.api.routes import router
from src.api.middleware import (
    LoggingMiddleware, 
    MetricsMiddleware,
    TenantMiddleware,
    RateLimitMiddleware
)
from src.utils.metrics import MetricsManager
from src.utils.cache import CacheManager
from src.audit.logger import AuditLogger
from src.policy.version_manager import PolicyVersionManager
from src.tenant.manager import TenantManager
from src.secrets.manager import SecretsManagerFactory
from src.config import settings

logger = logging.getLogger(__name__)
load_dotenv()
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting AI Control Plane...")
    
    # Initialize components
    await CacheManager.initialize()
    await MetricsManager.initialize()
    audit_logger = AuditLogger()
    await audit_logger.initialize()
    #await PolicyVersionManager().initialize()
    logger.warning("Running without database - some features disabled")
    logger.info("Application startup complete")
    yield
    await TenantManager().initialize()
    
    # Initialize secrets manager
    if settings.SECRETS_PROVIDER:
        secrets_manager = await SecretsManagerFactory.create(
            settings.SECRETS_PROVIDER,
            settings.SECRETS_CONFIG
        )
        app.state.secrets_manager = secrets_manager
    
    logger.info("✅ All components initialized")
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")
    await CacheManager.close()
    await MetricsManager.close()
    await AuditLogger.close()

# Create FastAPI app
app = FastAPI(
    title="AI Control Plane",
    description="Enterprise AI Gateway with Multi-Tenant Support",
    version="3.1.7",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenantMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

# Include routes
app.include_router(router)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.1.7",
        "services": {
            "redis": await CacheManager.health_check(),
            "opa": await OpaClient.health_check(),
            "database": await DatabasePool.health_check(),
            "vault": await app.state.secrets_manager.health_check() 
                if hasattr(app.state, 'secrets_manager') else "not_configured"
        }
    }

@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    return {"status": "ready"}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return MetricsManager.get_metrics()

@app.get("/api/v1/tenants")
async def list_tenants():
    """List all tenants"""
    tenant_manager = TenantManager()
    return await tenant_manager.list_tenants()

@app.get("/api/v1/policies/versions")
async def get_policy_versions():
    """Get policy version history"""
    version_manager = PolicyVersionManager()
    return await version_manager.get_policy_history()

@app.post("/api/v1/policies/rollback/{version}")
async def rollback_policy(version: str):
    """Rollback to specific policy version"""
    from src.policy.engine import PolicyEngine
    policy_engine = PolicyEngine()
    success = await policy_engine.rollback_policy(version)
    
    if success:
        return {"status": "success", "version": version}
    else:
        raise HTTPException(status_code=400, detail="Rollback failed")

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=settings.WORKERS
    )