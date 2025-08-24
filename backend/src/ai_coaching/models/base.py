"""Base models and core system dependencies for AI Coaching Management System."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
import structlog

# Import service types (will be implemented later)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_coaching.services.database import DatabaseService
    from ai_coaching.services.airtable import AirtableService
    from ai_coaching.services.gmail import GmailService
    from ai_coaching.services.embedding import EmbeddingService
    from ai_coaching.config.settings import SystemConfig


@dataclass
class SystemDependencies:
    """Core system dependencies for all agents."""
    db_service: "DatabaseService"
    airtable_service: "AirtableService"
    gmail_service: "GmailService"
    embedding_service: "EmbeddingService"
    config: "SystemConfig"
    logger: structlog.stdlib.BoundLogger


class BaseAgentOutput(BaseModel):
    """Standard output structure for all agents."""
    success: bool = Field(description="Task completion status")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in result")
    result_data: Dict[str, Any] = Field(description="Structured result payload")
    error_message: Optional[str] = Field(default=None, description="Error details if applicable")
    processing_time: float = Field(description="Task processing duration in seconds")


class AgentType(str, Enum):
    """Enumeration of available agent types."""
    EMAIL = "email"
    SCHEDULE = "schedule"
    KNOWLEDGE = "knowledge"
    ORCHESTRATOR = "orchestrator"
    CONTENT = "content"


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    """User role definitions."""
    ADMIN = "admin"
    COACH = "coach"
    PARENT = "parent"
    READONLY = "readonly"


class BaseTask(BaseModel):
    """Base task model for agent processing."""
    task_id: str = Field(description="Unique task identifier")
    task_type: str = Field(description="Type of task")
    input_data: Dict[str, Any] = Field(description="Task input parameters")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=lowest, 10=highest)")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class SystemHealthStatus(BaseModel):
    """System health status model."""
    overall_health: bool = Field(description="Overall system health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    service_status: Dict[str, bool] = Field(description="Individual service health status")
    performance_metrics: Dict[str, float] = Field(description="Current performance metrics")
    active_tasks: int = Field(description="Number of active tasks")
    error_count: int = Field(default=0, description="Number of recent errors")


class APIResponse(BaseModel):
    """Standard API response format."""
    success: bool = Field(description="Request success status")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    message: Optional[str] = Field(default=None, description="Response message")
    error: Optional[str] = Field(default=None, description="Error message if applicable")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")