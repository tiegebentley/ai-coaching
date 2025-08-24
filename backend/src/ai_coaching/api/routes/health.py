"""Health check endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
import structlog
from datetime import datetime

from ai_coaching.services.database import DatabaseService
from ai_coaching.services.embedding import EmbeddingService
from ai_coaching.config.settings import get_config

logger = structlog.get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, bool]
    details: Dict[str, Any] = {}


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Comprehensive health check endpoint."""
    config = get_config()
    timestamp = datetime.utcnow()
    
    # Check service health
    services = {}
    details = {}
    
    # Database health
    try:
        db_service = DatabaseService(config.database)
        await db_service.initialize()
        db_healthy = await db_service.health_check()
        services["database"] = db_healthy
        if db_healthy:
            details["database"] = "Connected to Supabase"
        else:
            details["database"] = "Database connection failed"
        await db_service.close()
    except Exception as e:
        services["database"] = False
        details["database"] = f"Database error: {str(e)}"
    
    # Embedding service health
    try:
        embedding_service = EmbeddingService(config.ai)
        await embedding_service.initialize()
        embed_healthy = await embedding_service.health_check()
        services["embedding"] = embed_healthy
        if embed_healthy:
            details["embedding"] = "OpenAI API accessible"
        else:
            details["embedding"] = "OpenAI API not accessible"
    except Exception as e:
        services["embedding"] = False
        details["embedding"] = f"Embedding service error: {str(e)}"
    
    # Overall status
    overall_status = "healthy" if all(services.values()) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=timestamp,
        version=config.app_version,
        services=services,
        details=details
    )


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """Simple liveness check for container orchestration."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check for load balancer."""
    config = get_config()
    
    # Quick service checks
    ready = True
    checks = {}
    
    try:
        # Just check if we can create service instances
        db_service = DatabaseService(config.database)
        checks["database"] = "ready"
    except Exception as e:
        checks["database"] = f"not ready: {str(e)}"
        ready = False
    
    try:
        embedding_service = EmbeddingService(config.ai)
        checks["embedding"] = "ready"
    except Exception as e:
        checks["embedding"] = f"not ready: {str(e)}"
        ready = False
    
    return {
        "status": "ready" if ready else "not ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }