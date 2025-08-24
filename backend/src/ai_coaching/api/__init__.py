"""API package for AI Coaching Management System.

This package contains all API routes and endpoints for the FastAPI application.
Organized by functionality: auth, gmail, webhooks, dashboard, etc.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai_coaching.config.settings import get_config
import structlog

logger = structlog.get_logger(__name__)

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title=config.app_name,
        version=config.app_version,
        debug=config.debug,
        openapi_url=f"{config.api_prefix}/openapi.json" if config.debug else None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Import and include routers
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
    
    logger.info("FastAPI application created", app_name=config.app_name, version=config.app_version)
    
    return app