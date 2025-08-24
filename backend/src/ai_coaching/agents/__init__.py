"""AI Coaching Agents Package.

This package contains all AI agents used in the system, including
base agent architecture and specialized agent implementations.
"""

from .base import BaseAgent, AgentTask, AgentStatus
from .knowledge import KnowledgeAgent
from .registry import AgentRegistry, initialize_agent_registry

__all__ = [
    "BaseAgent",
    "AgentTask", 
    "AgentStatus",
    "KnowledgeAgent",
    "AgentRegistry",
    "initialize_agent_registry",
]