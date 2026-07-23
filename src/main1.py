from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import logging
from contextlib import asynccontextmanager

from src.api.routes import router
from src.api.middleware import LoggingMiddleware, MetricsMiddleware
from src.utils.metrics import MetricsManager
from src.utils.cache import CacheManager
from src.audit.logger import AuditLogger
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting AI Control Plane...")
    await CacheManager.initialize()
    await MetricsManager.initialize()
    await AuditLogger.initialize()
    yield
    # Shutdown
    logger.info("Shutting down AI Control Plane...")
    await CacheManager.close()
    await MetricsManager.close()
    await AuditLogger.close()

# Create FastAPI app
app = FastAPI(
    title="AI Control Plane",
    description="Enterprise AI Gateway with SA-specific PII detection",
    version="1.0.0",
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

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

# Include routes
app.include_router(router)

@app.get("/health")
async def health_check():
    """Health check endpoint for Envoy"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "redis": await CacheManager.health_check(),
            "opa": await OpaClient.health_check(),
            "database": await Database.health_check()
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

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        workers=settings.WORKERS
    )
