"""Orchestrator Agent for task delegation and multi-agent workflows."""

import asyncio
import time
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
import structlog

from pydantic import BaseModel, Field

from ai_coaching.agents.base import BaseAgent, AgentTask
from ai_coaching.models.base import BaseAgentOutput, SystemDependencies, TaskStatus, AgentType
from ai_coaching.agents.registry import AgentRegistry


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TaskPriority(str, Enum):
    """Task priority levels for orchestration."""
    URGENT = "urgent"      # <5 minutes response time
    HIGH = "high"          # <30 minutes response time
    NORMAL = "normal"      # <2 hours response time
    LOW = "low"           # <24 hours response time
    BACKGROUND = "background"  # Process when idle


class OrchestratedTask(BaseModel):
    """Enhanced task model for orchestration."""
    task_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique task identifier")
    parent_workflow_id: Optional[str] = Field(None, description="Parent workflow ID")
    task_type: str = Field(..., description="Type of task to process")
    agent_type: AgentType = Field(..., description="Target agent for execution")
    input_data: Dict[str, Any] = Field(..., description="Task input parameters")
    context: Dict[str, Any] = Field(default_factory=dict, description="Shared workflow context")
    
    # Priority and timing
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority level")
    deadline: Optional[datetime] = Field(None, description="Task deadline")
    estimated_duration: Optional[float] = Field(None, description="Estimated processing time in seconds")
    
    # Dependencies and relationships
    dependencies: List[str] = Field(default_factory=list, description="Task IDs this task depends on")
    dependents: List[str] = Field(default_factory=list, description="Task IDs that depend on this task")
    
    # Status tracking
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    assigned_to: Optional[str] = Field(None, description="Assigned agent instance ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Task creation time")
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    
    # Error handling
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    last_error: Optional[str] = Field(None, description="Last error message")
    
    # Results
    result: Optional[BaseAgentOutput] = Field(None, description="Task execution result")


class Workflow(BaseModel):
    """Multi-task workflow definition."""
    workflow_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    
    # Workflow structure
    tasks: List[OrchestratedTask] = Field(default_factory=list, description="Tasks in workflow")
    execution_strategy: str = Field(default="sequential", description="Execution strategy: sequential, parallel, conditional")
    
    # Status and timing
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="Workflow status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Workflow creation time")
    started_at: Optional[datetime] = Field(None, description="Workflow start time")
    completed_at: Optional[datetime] = Field(None, description="Workflow completion time")
    
    # Context and results
    shared_context: Dict[str, Any] = Field(default_factory=dict, description="Shared workflow context")
    results: Dict[str, BaseAgentOutput] = Field(default_factory=dict, description="Task results by task_id")
    
    # Error handling
    failed_tasks: List[str] = Field(default_factory=list, description="Failed task IDs")
    error_strategy: str = Field(default="fail_fast", description="Error handling strategy")
    

class AgentMetrics(BaseModel):
    """Performance metrics for agent monitoring."""
    agent_type: AgentType
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    avg_processing_time: float = 0.0
    current_load: int = 0  # Number of concurrent tasks
    max_concurrent: int = 5  # Maximum concurrent tasks
    last_activity: Optional[datetime] = None
    health_score: float = 1.0  # 0-1 health score


class OrchestratorAgent(BaseAgent):
    """Agent responsible for task delegation and multi-agent workflow coordination.
    
    This agent:
    - Manages a task queue with prioritization
    - Delegates tasks to specialized agents
    - Coordinates complex multi-step workflows  
    - Handles agent communication and context sharing
    - Monitors performance and implements dynamic scaling
    - Provides error handling and recovery mechanisms
    """
    
    def __init__(
        self,
        dependencies: SystemDependencies,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the Orchestrator Agent.
        
        Args:
            dependencies: System dependencies
            config: Agent-specific configuration
        """
        super().__init__(
            agent_name="OrchestratorAgent",
            dependencies=dependencies,
            config=config or {}
        )
        
        # Task management
        self._task_queue: List[OrchestratedTask] = []
        self._active_tasks: Dict[str, OrchestratedTask] = {}
        self._workflows: Dict[str, Workflow] = {}
        
        # Agent monitoring
        self._agent_metrics: Dict[AgentType, AgentMetrics] = {}
        self._agent_registry = AgentRegistry()
        
        # Configuration
        self._max_concurrent_tasks = config.get('max_concurrent_tasks', 10)
        self._health_check_interval = config.get('health_check_interval', 60)  # seconds
        self._task_timeout = config.get('task_timeout', 300)  # 5 minutes default
        
        # Performance tracking
        self._total_workflows = 0
        self._completed_workflows = 0
        self._failed_workflows = 0
        
    async def _initialize_agent(self) -> None:
        """Initialize the orchestrator agent."""
        self.logger.info("Initializing Orchestrator Agent")
        
        # Initialize agent metrics for known agent types
        for agent_type in AgentType:
            if agent_type != AgentType.ORCHESTRATOR:  # Don't monitor self
                self._agent_metrics[agent_type] = AgentMetrics(agent_type=agent_type)
        
        # Start background monitoring task
        asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("Orchestrator Agent initialized successfully")
    
    async def process_task(self, task: AgentTask) -> BaseAgentOutput:
        """Process orchestration requests.
        
        Args:
            task: Orchestration task (delegate_task, execute_workflow, etc.)
            
        Returns:
            BaseAgentOutput with orchestration results
        """
        start_time = time.time()
        task_type = task.task_type
        
        try:
            self.logger.info(
                "Processing orchestration task",
                task_id=task.task_id,
                orchestration_type=task_type
            )
            
            if task_type == "delegate_task":
                result = await self._delegate_task(task.input_data)
            elif task_type == "execute_workflow":
                result = await self._execute_workflow(task.input_data)
            elif task_type == "monitor_agents":
                result = await self._monitor_agents()
            elif task_type == "get_queue_status":
                result = await self._get_queue_status()
            elif task_type == "cancel_task":
                result = await self._cancel_task(task.input_data)
            else:
                raise ValueError(f"Unknown orchestration task type: {task_type}")
            
            processing_time = time.time() - start_time
            
            return BaseAgentOutput(
                success=True,
                confidence_score=result.get('confidence_score', 0.9),
                result_data=result,
                processing_time=processing_time,
                metadata={
                    "orchestration_type": task_type,
                    "active_tasks": len(self._active_tasks),
                    "queued_tasks": len(self._task_queue),
                    "active_workflows": len([w for w in self._workflows.values() if w.status == WorkflowStatus.RUNNING])
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Orchestration task failed",
                task_id=task.task_id,
                error=str(e)
            )
            processing_time = time.time() - start_time
            
            return BaseAgentOutput(
                success=False,
                confidence_score=0.0,
                result_data={"error": str(e)},
                error_message=str(e),
                processing_time=processing_time
            )
    
    async def _delegate_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate a task to the appropriate agent.
        
        Args:
            task_data: Task delegation request
            
        Returns:
            Delegation result
        """
        # Extract task information
        agent_type = AgentType(task_data['agent_type'])
        task_input = task_data['task_input']
        priority = TaskPriority(task_data.get('priority', TaskPriority.NORMAL))
        
        # Create orchestrated task
        orchestrated_task = OrchestratedTask(
            task_type=task_input.get('task_type', 'generic'),
            agent_type=agent_type,
            input_data=task_input,
            priority=priority,
            context=task_data.get('context', {}),
            dependencies=task_data.get('dependencies', []),
            max_retries=task_data.get('max_retries', 3)
        )
        
        # Add to queue
        await self._enqueue_task(orchestrated_task)
        
        # Process queue
        await self._process_queue()
        
        return {
            "task_id": orchestrated_task.task_id,
            "status": orchestrated_task.status.value,
            "message": f"Task delegated to {agent_type.value} agent",
            "queue_position": len(self._task_queue)
        }
    
    async def _execute_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a multi-task workflow.
        
        Args:
            workflow_data: Workflow definition
            
        Returns:
            Workflow execution result
        """
        workflow_name = workflow_data['name']
        workflow_tasks = workflow_data['tasks']
        strategy = workflow_data.get('execution_strategy', 'sequential')
        
        # Create workflow
        workflow = Workflow(
            name=workflow_name,
            description=workflow_data.get('description'),
            execution_strategy=strategy,
            shared_context=workflow_data.get('context', {}),
            error_strategy=workflow_data.get('error_strategy', 'fail_fast')
        )
        
        # Create orchestrated tasks
        for task_def in workflow_tasks:
            task = OrchestratedTask(
                parent_workflow_id=workflow.workflow_id,
                task_type=task_def['task_type'],
                agent_type=AgentType(task_def['agent_type']),
                input_data=task_def['input_data'],
                priority=TaskPriority(task_def.get('priority', TaskPriority.NORMAL)),
                dependencies=task_def.get('dependencies', []),
                context=workflow.shared_context
            )
            workflow.tasks.append(task)
        
        # Store workflow
        self._workflows[workflow.workflow_id] = workflow
        self._total_workflows += 1
        
        # Execute workflow
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(UTC)
        
        try:
            if strategy == "sequential":
                await self._execute_sequential_workflow(workflow)
            elif strategy == "parallel":
                await self._execute_parallel_workflow(workflow)
            else:
                raise ValueError(f"Unknown execution strategy: {strategy}")
            
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now(UTC)
            self._completed_workflows += 1
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            self._failed_workflows += 1
            raise e
        
        return {
            "workflow_id": workflow.workflow_id,
            "status": workflow.status.value,
            "completed_tasks": len(workflow.results),
            "total_tasks": len(workflow.tasks),
            "execution_time": (workflow.completed_at - workflow.started_at).total_seconds() if workflow.completed_at else None
        }
    
    async def _execute_sequential_workflow(self, workflow: Workflow) -> None:
        """Execute workflow tasks sequentially."""
        for task in workflow.tasks:
            # Check dependencies
            if not await self._check_task_dependencies(task, workflow):
                continue
            
            # Execute task
            result = await self._execute_single_task(task)
            workflow.results[task.task_id] = result
            
            # Update shared context
            if result.success and 'context_updates' in result.result_data:
                workflow.shared_context.update(result.result_data['context_updates'])
            
            # Handle failures based on error strategy
            if not result.success and workflow.error_strategy == "fail_fast":
                raise Exception(f"Task {task.task_id} failed: {result.error_message}")
    
    async def _execute_parallel_workflow(self, workflow: Workflow) -> None:
        """Execute workflow tasks in parallel where possible."""
        # Group tasks by dependency levels
        dependency_levels = self._calculate_dependency_levels(workflow.tasks)
        
        # Execute each level in sequence, but tasks within level in parallel
        for level in sorted(dependency_levels.keys()):
            level_tasks = dependency_levels[level]
            
            # Execute level tasks in parallel
            tasks_coroutines = [
                self._execute_single_task(task) for task in level_tasks
            ]
            
            results = await asyncio.gather(*tasks_coroutines, return_exceptions=True)
            
            # Process results
            for task, result in zip(level_tasks, results):
                if isinstance(result, Exception):
                    # Handle exception
                    error_result = BaseAgentOutput(
                        success=False,
                        confidence_score=0.0,
                        result_data={"error": str(result)},
                        error_message=str(result),
                        processing_time=0.0
                    )
                    workflow.results[task.task_id] = error_result
                    
                    if workflow.error_strategy == "fail_fast":
                        raise result
                else:
                    workflow.results[task.task_id] = result
                    
                    # Update shared context
                    if result.success and 'context_updates' in result.result_data:
                        workflow.shared_context.update(result.result_data['context_updates'])
    
    async def _execute_single_task(self, task: OrchestratedTask) -> BaseAgentOutput:
        """Execute a single task using the appropriate agent.
        
        Args:
            task: Task to execute
            
        Returns:
            Task execution result
        """
        # Get agent from registry
        agent = self._agent_registry.get_agent(task.agent_type)
        if not agent:
            return BaseAgentOutput(
                success=False,
                confidence_score=0.0,
                result_data={"error": f"Agent {task.agent_type.value} not found"},
                error_message=f"Agent {task.agent_type.value} not found",
                processing_time=0.0
            )
        
        # Map priority to integer
        priority_map = {
            TaskPriority.URGENT: 10,
            TaskPriority.HIGH: 8, 
            TaskPriority.NORMAL: 5,
            TaskPriority.LOW: 3,
            TaskPriority.BACKGROUND: 1
        }
        
        # Create agent task
        agent_task = AgentTask(
            task_id=task.task_id,
            task_type=task.task_type,
            input_data=task.input_data,
            context=task.context,
            priority=priority_map.get(task.priority, 5),
            timeout_seconds=self._task_timeout
        )
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(UTC)
        self._active_tasks[task.task_id] = task
        
        try:
            # Execute task through agent
            result = await agent.process_task(agent_task)
            
            # Update task
            task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            task.completed_at = datetime.now(UTC)
            task.result = result
            
            # Update metrics
            self._update_agent_metrics(task.agent_type, result)
            
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(UTC)
            task.last_error = str(e)
            
            error_result = BaseAgentOutput(
                success=False,
                confidence_score=0.0,
                result_data={"error": str(e)},
                error_message=str(e),
                processing_time=0.0
            )
            task.result = error_result
            
            self._update_agent_metrics(task.agent_type, error_result)
            
            return error_result
        
        finally:
            # Remove from active tasks
            self._active_tasks.pop(task.task_id, None)
    
    async def _enqueue_task(self, task: OrchestratedTask) -> None:
        """Add task to priority queue."""
        # Insert task based on priority
        priority_order = {
            TaskPriority.URGENT: 1,
            TaskPriority.HIGH: 2,
            TaskPriority.NORMAL: 3,
            TaskPriority.LOW: 4,
            TaskPriority.BACKGROUND: 5
        }
        
        task_priority = priority_order.get(task.priority, 3)
        
        # Find insertion point
        insert_index = 0
        for i, queued_task in enumerate(self._task_queue):
            queued_priority = priority_order.get(queued_task.priority, 3)
            if task_priority < queued_priority:
                insert_index = i
                break
            insert_index = i + 1
        
        self._task_queue.insert(insert_index, task)
        
        self.logger.info(
            "Task enqueued",
            task_id=task.task_id,
            priority=task.priority.value,
            queue_size=len(self._task_queue)
        )
    
    async def _process_queue(self) -> None:
        """Process queued tasks based on capacity."""
        while (len(self._active_tasks) < self._max_concurrent_tasks and 
               self._task_queue):
            
            # Get next task
            next_task = None
            for i, task in enumerate(self._task_queue):
                # Check if dependencies are met
                if await self._check_task_dependencies(task, None):
                    next_task = self._task_queue.pop(i)
                    break
            
            if next_task is None:
                break  # No tasks with satisfied dependencies
            
            # Start task execution in background
            asyncio.create_task(self._execute_single_task(next_task))
    
    async def _check_task_dependencies(self, task: OrchestratedTask, workflow: Optional[Workflow]) -> bool:
        """Check if task dependencies are satisfied."""
        if not task.dependencies:
            return True
        
        # If part of workflow, check within workflow context
        if workflow:
            for dep_id in task.dependencies:
                if dep_id not in workflow.results:
                    return False
                if not workflow.results[dep_id].success:
                    return False
        else:
            # Check in active/completed tasks
            for dep_id in task.dependencies:
                if dep_id in self._active_tasks:
                    return False  # Dependency still running
                # Would need to check completed tasks database here
        
        return True
    
    def _calculate_dependency_levels(self, tasks: List[OrchestratedTask]) -> Dict[int, List[OrchestratedTask]]:
        """Calculate dependency levels for parallel execution."""
        levels = {}
        task_levels = {}
        
        # Calculate level for each task
        for task in tasks:
            level = self._calculate_task_level(task, tasks, task_levels)
            if level not in levels:
                levels[level] = []
            levels[level].append(task)
        
        return levels
    
    def _calculate_task_level(self, task: OrchestratedTask, all_tasks: List[OrchestratedTask], memo: Dict[str, int]) -> int:
        """Calculate the execution level for a task based on dependencies."""
        if task.task_id in memo:
            return memo[task.task_id]
        
        if not task.dependencies:
            memo[task.task_id] = 0
            return 0
        
        # Find maximum level of dependencies
        max_dep_level = -1
        task_map = {t.task_id: t for t in all_tasks}
        
        for dep_id in task.dependencies:
            if dep_id in task_map:
                dep_level = self._calculate_task_level(task_map[dep_id], all_tasks, memo)
                max_dep_level = max(max_dep_level, dep_level)
        
        level = max_dep_level + 1
        memo[task.task_id] = level
        return level
    
    def _update_agent_metrics(self, agent_type: AgentType, result: BaseAgentOutput) -> None:
        """Update performance metrics for an agent."""
        if agent_type not in self._agent_metrics:
            return
        
        metrics = self._agent_metrics[agent_type]
        metrics.total_tasks += 1
        metrics.last_activity = datetime.now(UTC)
        
        if result.success:
            metrics.successful_tasks += 1
        else:
            metrics.failed_tasks += 1
        
        # Update average processing time
        if metrics.total_tasks == 1:
            metrics.avg_processing_time = result.processing_time
        else:
            metrics.avg_processing_time = (
                (metrics.avg_processing_time * (metrics.total_tasks - 1) + result.processing_time) / 
                metrics.total_tasks
            )
        
        # Update health score
        success_rate = metrics.successful_tasks / metrics.total_tasks
        metrics.health_score = min(1.0, success_rate * 1.2)  # Slightly boost for good performance
    
    async def _monitor_agents(self) -> Dict[str, Any]:
        """Get monitoring information for all agents."""
        agent_status = {}
        
        for agent_type, metrics in self._agent_metrics.items():
            agent_status[agent_type.value] = {
                "total_tasks": metrics.total_tasks,
                "success_rate": metrics.successful_tasks / max(1, metrics.total_tasks),
                "avg_processing_time": metrics.avg_processing_time,
                "current_load": metrics.current_load,
                "health_score": metrics.health_score,
                "last_activity": metrics.last_activity.isoformat() if metrics.last_activity else None
            }
        
        return {
            "agent_metrics": agent_status,
            "orchestrator_stats": {
                "total_workflows": self._total_workflows,
                "completed_workflows": self._completed_workflows,
                "failed_workflows": self._failed_workflows,
                "success_rate": self._completed_workflows / max(1, self._total_workflows),
                "active_tasks": len(self._active_tasks),
                "queued_tasks": len(self._task_queue),
                "active_workflows": len([w for w in self._workflows.values() if w.status == WorkflowStatus.RUNNING])
            }
        }
    
    async def _get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "active_tasks": len(self._active_tasks),
            "queued_tasks": len(self._task_queue),
            "queue_details": [
                {
                    "task_id": task.task_id,
                    "priority": task.priority.value,
                    "agent_type": task.agent_type.value,
                    "created_at": task.created_at.isoformat()
                }
                for task in self._task_queue
            ],
            "active_details": [
                {
                    "task_id": task.task_id,
                    "agent_type": task.agent_type.value,
                    "started_at": task.started_at.isoformat() if task.started_at else None
                }
                for task in self._active_tasks.values()
            ]
        }
    
    async def _cancel_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cancel a queued or active task."""
        task_id = task_data['task_id']
        
        # Check queued tasks
        for i, task in enumerate(self._task_queue):
            if task.task_id == task_id:
                cancelled_task = self._task_queue.pop(i)
                cancelled_task.status = TaskStatus.CANCELLED
                return {
                    "task_id": task_id,
                    "status": "cancelled",
                    "message": "Task removed from queue"
                }
        
        # Check active tasks (can't cancel, but can mark for cancellation)
        if task_id in self._active_tasks:
            return {
                "task_id": task_id,
                "status": "cancellation_requested",
                "message": "Cancellation requested for active task"
            }
        
        return {
            "task_id": task_id,
            "status": "not_found",
            "message": "Task not found in queue or active tasks"
        }
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring and maintenance loop."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                # Update agent metrics
                for agent_type in self._agent_metrics:
                    # Update current load based on active tasks
                    load = sum(1 for task in self._active_tasks.values() 
                             if task.agent_type == agent_type)
                    self._agent_metrics[agent_type].current_load = load
                
                # Process queue
                await self._process_queue()
                
                # Clean up completed workflows (keep for 1 hour)
                cutoff_time = datetime.now(UTC).timestamp() - 3600  # 1 hour ago
                to_remove = [
                    wf_id for wf_id, workflow in self._workflows.items()
                    if workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED] and
                    workflow.completed_at and workflow.completed_at.timestamp() < cutoff_time
                ]
                
                for wf_id in to_remove:
                    del self._workflows[wf_id]
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {str(e)}")
    
    async def _agent_health_check(self) -> bool:
        """Orchestrator-specific health check."""
        # Check if monitoring loop is running
        # Check agent registry health
        health_status = await self._agent_registry.health_check()
        
        # Consider orchestrator healthy if at least one agent is available
        return len(health_status) > 0 and any(health_status.values())
    
    def get_orchestrator_stats(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator statistics."""
        return {
            "workflows": {
                "total": self._total_workflows,
                "completed": self._completed_workflows,
                "failed": self._failed_workflows,
                "active": len([w for w in self._workflows.values() if w.status == WorkflowStatus.RUNNING])
            },
            "tasks": {
                "active": len(self._active_tasks),
                "queued": len(self._task_queue),
                "max_concurrent": self._max_concurrent_tasks
            },
            "agents": {
                "monitored": len(self._agent_metrics),
                "healthy": sum(1 for m in self._agent_metrics.values() if m.health_score > 0.7)
            },
            "configuration": {
                "max_concurrent_tasks": self._max_concurrent_tasks,
                "health_check_interval": self._health_check_interval,
                "task_timeout": self._task_timeout
            }
        }