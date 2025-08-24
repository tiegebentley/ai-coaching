"""Base Agent architecture for AI Coaching Management System."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
import time

import structlog
from pydantic import BaseModel, Field

from ai_coaching.models.base import BaseAgentOutput, SystemDependencies, TaskStatus
# from ai_coaching.config.settings import SystemConfig  # Avoid import time validation

logger = structlog.get_logger(__name__)


class AgentTask(BaseModel):
    """Task model for agent processing."""
    task_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique task identifier")
    task_type: str = Field(..., description="Type of task to process")
    input_data: Dict[str, Any] = Field(..., description="Task input parameters")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=lowest, 10=highest)")
    timeout_seconds: Optional[int] = Field(default=60, description="Task timeout in seconds")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Task creation timestamp")


class AgentStatus(BaseModel):
    """Agent status information."""
    is_healthy: bool = Field(..., description="Agent health status")
    is_busy: bool = Field(default=False, description="Whether agent is currently processing")
    current_task_id: Optional[str] = Field(None, description="Currently processing task ID")
    total_tasks_processed: int = Field(default=0, description="Total tasks processed")
    average_processing_time: float = Field(default=0.0, description="Average task processing time in seconds")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    error_count: int = Field(default=0, description="Number of errors encountered")
    last_error: Optional[str] = Field(None, description="Last error message")


class BaseAgent(ABC):
    """Abstract base class for all AI agents in the system.
    
    Provides common functionality for task processing, error handling,
    logging, and status management that all agents can inherit.
    """
    
    def __init__(
        self,
        agent_name: str,
        dependencies: SystemDependencies,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize base agent.
        
        Args:
            agent_name: Human-readable name for the agent
            dependencies: System dependencies (database, services, etc.)
            config: Agent-specific configuration
        """
        self.agent_name = agent_name
        self.dependencies = dependencies
        self.config = config or {}
        self.logger = structlog.get_logger(f"agent.{agent_name.lower()}")
        
        # Agent state
        self._status = AgentStatus(is_healthy=True)
        self._task_history: List[Dict[str, Any]] = []
        self._initialization_time = datetime.now(UTC)
        
        # Performance tracking
        self._processing_times: List[float] = []
        self._max_history_size = 1000
        
        self.logger.info(
            "Agent initialized",
            agent_name=agent_name,
            config_keys=list(self.config.keys())
        )
    
    async def initialize(self) -> bool:
        """Initialize the agent and its dependencies.
        
        Override this method to perform agent-specific initialization.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Agent initialization started")
            
            # Check system dependencies
            if not await self._check_dependencies():
                raise RuntimeError("Dependency check failed")
            
            # Agent-specific initialization
            await self._initialize_agent()
            
            self._status.is_healthy = True
            self._status.last_activity = datetime.now(UTC)
            
            self.logger.info("Agent initialization completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(
                "Agent initialization failed",
                error=str(e),
                error_type=type(e).__name__
            )
            self._status.is_healthy = False
            self._status.last_error = str(e)
            self._status.error_count += 1
            return False
    
    @abstractmethod
    async def process_task(self, task: AgentTask) -> BaseAgentOutput:
        """Process a task assigned to this agent.
        
        Args:
            task: Task to process
            
        Returns:
            BaseAgentOutput with processing results
        """
        pass
    
    @abstractmethod
    async def _initialize_agent(self) -> None:
        """Agent-specific initialization logic.
        
        Override this method to implement custom initialization
        for each agent type.
        """
        pass
    
    async def get_status(self) -> AgentStatus:
        """Get current agent status.
        
        Returns:
            Current agent status information
        """
        # Update average processing time
        if self._processing_times:
            self._status.average_processing_time = sum(self._processing_times) / len(self._processing_times)
        
        return self._status.copy(deep=True)
    
    async def handle_error(
        self,
        error: Exception,
        task: Optional[AgentTask] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle errors during task processing.
        
        Args:
            error: Exception that occurred
            task: Task being processed when error occurred
            context: Additional error context
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now(UTC).isoformat(),
            "agent_name": self.agent_name
        }
        
        if task:
            error_info["task_id"] = task.task_id
            error_info["task_type"] = task.task_type
        
        if context:
            error_info["context"] = context
        
        # Update agent status
        self._status.error_count += 1
        self._status.last_error = str(error)
        
        # Log error with structured data
        self.logger.error(
            "Agent error occurred",
            **error_info
        )
        
        # Store error in task history
        self._add_to_history({
            "type": "error",
            "timestamp": datetime.now(UTC),
            "task_id": task.task_id if task else None,
            "error": error_info
        })
    
    async def health_check(self) -> bool:
        """Perform comprehensive health check.
        
        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            # Check basic agent state
            if not self._status.is_healthy:
                return False
            
            # Check dependencies
            if not await self._check_dependencies():
                self._status.is_healthy = False
                return False
            
            # Agent-specific health checks
            if not await self._agent_health_check():
                self._status.is_healthy = False
                return False
            
            # Update last activity
            self._status.last_activity = datetime.now(UTC)
            
            self.logger.debug("Health check passed")
            return True
            
        except Exception as e:
            self.logger.error(
                "Health check failed",
                error=str(e)
            )
            self._status.is_healthy = False
            self._status.last_error = str(e)
            self._status.error_count += 1
            return False
    
    async def _check_dependencies(self) -> bool:
        """Check that all required dependencies are available.
        
        Returns:
            True if all dependencies are available, False otherwise
        """
        try:
            # Check database service
            if self.dependencies.db_service:
                db_healthy = await self.dependencies.db_service.health_check()
                if not db_healthy:
                    self.logger.warning("Database service not healthy")
                    return False
            
            # Check other dependencies as needed
            # Subclasses can override this method for specific checks
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Dependency check failed",
                error=str(e)
            )
            return False
    
    async def _agent_health_check(self) -> bool:
        """Agent-specific health check logic.
        
        Override this method to implement custom health checks
        for each agent type.
        
        Returns:
            True if agent-specific checks pass, False otherwise
        """
        return True
    
    def _add_to_history(self, entry: Dict[str, Any]) -> None:
        """Add entry to task history.
        
        Args:
            entry: History entry to add
        """
        self._task_history.append(entry)
        
        # Maintain history size limit
        if len(self._task_history) > self._max_history_size:
            self._task_history = self._task_history[-self._max_history_size:]
    
    def _record_processing_time(self, processing_time: float) -> None:
        """Record task processing time for performance tracking.
        
        Args:
            processing_time: Processing time in seconds
        """
        self._processing_times.append(processing_time)
        
        # Maintain reasonable history size
        if len(self._processing_times) > 100:
            self._processing_times = self._processing_times[-100:]
    
    async def _execute_task(self, task: AgentTask) -> BaseAgentOutput:
        """Execute a task with proper error handling and timing.
        
        Args:
            task: Task to execute
            
        Returns:
            BaseAgentOutput with results
        """
        start_time = time.time()
        
        try:
            # Mark agent as busy
            self._status.is_busy = True
            self._status.current_task_id = task.task_id
            
            self.logger.info(
                "Task processing started",
                task_id=task.task_id,
                task_type=task.task_type
            )
            
            # Process the task
            result = await self.process_task(task)
            
            # Record successful processing
            processing_time = time.time() - start_time
            self._record_processing_time(processing_time)
            self._status.total_tasks_processed += 1
            
            # Add to history
            self._add_to_history({
                "type": "task_completed",
                "timestamp": datetime.now(UTC),
                "task_id": task.task_id,
                "task_type": task.task_type,
                "processing_time": processing_time,
                "success": result.success
            })
            
            self.logger.info(
                "Task processing completed",
                task_id=task.task_id,
                success=result.success,
                processing_time=processing_time,
                confidence_score=result.confidence_score
            )
            
            return result
            
        except Exception as e:
            # Handle error
            await self.handle_error(e, task)
            
            # Return error result
            processing_time = time.time() - start_time
            return BaseAgentOutput(
                success=False,
                confidence_score=0.0,
                result_data={"error": str(e)},
                error_message=str(e),
                processing_time=processing_time
            )
        
        finally:
            # Mark agent as not busy
            self._status.is_busy = False
            self._status.current_task_id = None
            self._status.last_activity = datetime.now(UTC)
    
    async def shutdown(self) -> None:
        """Shutdown the agent gracefully.
        
        Override this method to implement custom shutdown logic.
        """
        try:
            self.logger.info("Agent shutdown initiated")
            
            # Wait for current task to complete if busy
            while self._status.is_busy:
                await asyncio.sleep(0.1)
            
            # Agent-specific shutdown logic
            await self._shutdown_agent()
            
            self._status.is_healthy = False
            self.logger.info("Agent shutdown completed")
            
        except Exception as e:
            self.logger.error(
                "Agent shutdown failed",
                error=str(e)
            )
    
    async def _shutdown_agent(self) -> None:
        """Agent-specific shutdown logic.
        
        Override this method to implement custom shutdown
        for each agent type.
        """
        pass
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get comprehensive agent information.
        
        Returns:
            Dictionary containing agent details
        """
        return {
            "agent_name": self.agent_name,
            "agent_type": self.__class__.__name__,
            "status": self._status.dict(),
            "config": self.config,
            "initialization_time": self._initialization_time.isoformat(),
            "task_history_size": len(self._task_history),
            "avg_processing_time": (
                sum(self._processing_times) / len(self._processing_times)
                if self._processing_times else 0.0
            )
        }