"""Main FastAPI application for AI Coaching Management System."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from ai_coaching.config.settings import get_config
from ai_coaching.models.base import SystemDependencies, APIResponse
from ai_coaching.services.database import DatabaseService
from ai_coaching.services.embedding import EmbeddingService
from ai_coaching.services.airtable import AirtableService
from ai_coaching.services.gmail import GmailService
from ai_coaching.agents.registry import AgentRegistry, initialize_agent_registry
from ai_coaching.api.middleware.rate_limit import RateLimitMiddleware

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global dependencies container
dependencies: SystemDependencies = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    config = get_config()
    
    logger.info(
        "Starting AI Coaching Management System",
        version=config.app_version,
        environment=config.environment
    )
    
    # Initialize services
    global dependencies
    
    try:
        # Initialize database service
        db_service = DatabaseService(config.database)
        await db_service.initialize()
        
        # Initialize embedding service
        embedding_service = EmbeddingService(config.ai)
        await embedding_service.initialize()
        
        # Initialize Airtable service
        airtable_service = AirtableService(config.airtable)
        await airtable_service.initialize()
        
        # Initialize Gmail service (without credentials initially)
        gmail_service = GmailService(config.gmail)
        await gmail_service.initialize()
        
        # Create system dependencies
        dependencies = SystemDependencies(
            db_service=db_service,
            airtable_service=airtable_service,
            gmail_service=gmail_service,
            embedding_service=embedding_service,
            config=config,
            logger=logger
        )
        
        # Initialize agent registry
        initialize_agent_registry(dependencies)
        
        logger.info("All services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to initialize services", error=str(e))
        raise
    finally:
        logger.info("Shutting down AI Coaching Management System")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title=config.app_name,
        version=config.app_version,
        description="AI-powered coaching management system using PydanticAI",
        lifespan=lifespan,
        docs_url="/docs" if config.debug else None,
        redoc_url="/redoc" if config.debug else None
    )
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        default_requests_per_minute=config.security.api_rate_limit
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Frontend URLs
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for production
    if config.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
        )
    
    # Exception handlers
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            method=request.method
        )
        
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                success=False,
                error="Internal server error",
                message="An unexpected error occurred"
            ).dict()
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=APIResponse(
                success=False,
                error=exc.detail,
                message=f"HTTP {exc.status_code} error"
            ).dict()
        )
    
    # Health check endpoints
    @app.get("/health", response_model=APIResponse)
    async def health_check():
        """Basic health check endpoint."""
        return APIResponse(
            success=True,
            data={"status": "healthy", "service": "ai-coaching-backend"},
            message="Service is running"
        )
    
    @app.get("/health/detailed", response_model=APIResponse)
    async def detailed_health_check():
        """Detailed health check with service status."""
        if not dependencies:
            raise HTTPException(status_code=503, detail="Services not initialized")
        
        try:
            # Check individual service health
            health_status = {
                "database": await dependencies.db_service.health_check(),
                "embedding": await dependencies.embedding_service.health_check(),
                "airtable": await dependencies.airtable_service.health_check(),
                "gmail": await dependencies.gmail_service.health_check()
            }
            
            # Check agent registry
            agent_health = AgentRegistry.health_check()
            health_status.update({f"agent_{k.value}": v for k, v in agent_health.items()})
            
            # Overall health
            overall_health = all(health_status.values())
            
            return APIResponse(
                success=overall_health,
                data={
                    "overall_health": overall_health,
                    "services": health_status,
                    "timestamp": dependencies.config.app_version
                },
                message="Detailed health check completed"
            )
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            raise HTTPException(status_code=503, detail="Health check failed")
    
    @app.get("/info", response_model=APIResponse)
    async def app_info():
        """Get application information."""
        return APIResponse(
            success=True,
            data={
                "name": config.app_name,
                "version": config.app_version,
                "environment": config.environment,
                "debug": config.debug
            },
            message="Application information"
        )
    
    # Include API routes
    from ai_coaching.api.routes import auth, gmail, health
    
    app.include_router(
        health.router,
        prefix=config.api_prefix,
        tags=["health"]
    )
    
    app.include_router(
        auth.router,
        prefix=f"{config.api_prefix}/auth",
        tags=["authentication"]
    )
    
    app.include_router(
        gmail.router,
        prefix=f"{config.api_prefix}/gmail",
        tags=["gmail"]
    )
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    config = get_config()
    
    # Configure Python logging to work with structlog
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(message)s"
    )
    
    uvicorn.run(
        "ai_coaching.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload and config.environment == "development",
        log_level=config.log_level.lower(),
        workers=config.worker_processes if config.environment == "production" else 1
    )