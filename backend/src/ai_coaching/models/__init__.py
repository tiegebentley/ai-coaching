"""AI Coaching Management System - Data Models Package.

This package contains all Pydantic models used throughout the system,
including database schema models, API request/response models, and
business logic models.
"""

# Base models and common types
from .base import (
    SystemDependencies,
    BaseAgentOutput,
    AgentType,
    TaskStatus,
    UserRole,
    BaseTask,
    SystemHealthStatus,
    APIResponse
)

# Knowledge base models
from .knowledge import (
    ContentCategory,
    ContentSource,
    ContentFormat,
    KnowledgeItem,
    KnowledgeItemMetadata,
    KnowledgeSearchQuery,
    KnowledgeSearchResult,
    KnowledgeSearchResponse,
    KnowledgeBatchOperation,
    KnowledgeStats
)

__all__ = [
    # Base models
    "SystemDependencies",
    "BaseAgentOutput", 
    "AgentType",
    "TaskStatus",
    "UserRole",
    "BaseTask",
    "SystemHealthStatus",
    "APIResponse",
    
    # Knowledge models
    "ContentCategory",
    "ContentSource",
    "ContentFormat",
    "KnowledgeItem",
    "KnowledgeItemMetadata",
    "KnowledgeSearchQuery",
    "KnowledgeSearchResult",
    "KnowledgeSearchResponse",
    "KnowledgeBatchOperation",
    "KnowledgeStats",
]