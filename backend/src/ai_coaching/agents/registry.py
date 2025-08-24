"""Agent Registry System for managing and discovering AI agents."""

from typing import Dict, Optional, Type, TYPE_CHECKING
import structlog

from ai_coaching.models.base import AgentType, SystemDependencies

if TYPE_CHECKING:
    from ai_coaching.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class AgentRegistry:
    """Central registry for agent management and discovery."""
    
    _agents: Dict[AgentType, "BaseAgent"] = {}
    _agent_configs: Dict[AgentType, Dict] = {}
    _initialized: bool = False
    
    @classmethod
    def register_agent(
        cls, 
        agent_type: AgentType, 
        agent: "BaseAgent",
        config: Optional[Dict] = None
    ) -> None:
        """Register a new agent in the system.
        
        Args:
            agent_type: Type of agent to register
            agent: BaseAgent instance
            config: Optional configuration for the agent
        """
        cls._agents[agent_type] = agent
        cls._agent_configs[agent_type] = config or {}
        
        logger.info(
            "Agent registered",
            agent_type=agent_type.value,
            agent_id=id(agent),
            config_keys=list(config.keys()) if config else []
        )
    
    @classmethod
    def get_agent(cls, agent_type: AgentType) -> Optional["BaseAgent"]:
        """Retrieve agent by type.
        
        Args:
            agent_type: Type of agent to retrieve
            
        Returns:
            Agent instance if found, None otherwise
        """
        agent = cls._agents.get(agent_type)
        if agent is None:
            logger.warning(
                "Agent not found",
                agent_type=agent_type.value,
                available_agents=list(cls._agents.keys())
            )
        return agent
    
    @classmethod
    def get_agent_config(cls, agent_type: AgentType) -> Dict:
        """Get configuration for a specific agent type.
        
        Args:
            agent_type: Type of agent
            
        Returns:
            Agent configuration dictionary
        """
        return cls._agent_configs.get(agent_type, {})
    
    @classmethod
    def list_agents(cls) -> Dict[AgentType, Dict]:
        """List all registered agents with their configurations.
        
        Returns:
            Dictionary mapping agent types to their info
        """
        return {
            agent_type: {
                "agent": agent,
                "config": cls._agent_configs.get(agent_type, {}),
                "registered_at": getattr(agent, "_registered_at", None)
            }
            for agent_type, agent in cls._agents.items()
        }
    
    @classmethod
    def is_registered(cls, agent_type: AgentType) -> bool:
        """Check if an agent type is registered.
        
        Args:
            agent_type: Type of agent to check
            
        Returns:
            True if registered, False otherwise
        """
        return agent_type in cls._agents
    
    @classmethod
    def unregister_agent(cls, agent_type: AgentType) -> bool:
        """Unregister an agent from the system.
        
        Args:
            agent_type: Type of agent to unregister
            
        Returns:
            True if agent was unregistered, False if not found
        """
        if agent_type in cls._agents:
            del cls._agents[agent_type]
            cls._agent_configs.pop(agent_type, None)
            
            logger.info(
                "Agent unregistered",
                agent_type=agent_type.value
            )
            return True
        
        logger.warning(
            "Attempted to unregister non-existent agent",
            agent_type=agent_type.value
        )
        return False
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered agents."""
        agent_count = len(cls._agents)
        cls._agents.clear()
        cls._agent_configs.clear()
        cls._initialized = False
        
        logger.info(
            "Registry cleared",
            cleared_agents=agent_count
        )
    
    @classmethod
    async def health_check(cls) -> Dict[AgentType, bool]:
        """Perform health check on all registered agents.
        
        Returns:
            Dictionary mapping agent types to their health status
        """
        health_status = {}
        
        for agent_type, agent in cls._agents.items():
            try:
                # Use BaseAgent health check method if available
                if hasattr(agent, 'health_check'):
                    health_status[agent_type] = await agent.health_check()
                else:
                    # Fallback to simple check
                    health_status[agent_type] = agent is not None
            except Exception as e:
                logger.error(
                    "Agent health check failed",
                    agent_type=agent_type.value,
                    error=str(e)
                )
                health_status[agent_type] = False
        
        return health_status
    
    @classmethod
    async def get_registry_stats(cls) -> Dict:
        """Get statistics about the agent registry.
        
        Returns:
            Dictionary containing registry statistics
        """
        return {
            "total_agents": len(cls._agents),
            "agent_types": list(cls._agents.keys()),
            "initialized": cls._initialized,
            "health_status": await cls.health_check()
        }


def initialize_agent_registry(dependencies: SystemDependencies) -> None:
    """Initialize the agent registry with core system agents.
    
    This function will be called during system startup to register
    all available agents with the registry.
    
    Args:
        dependencies: System dependencies for agent initialization
    """
    if AgentRegistry._initialized:
        logger.warning("Agent registry already initialized")
        return
    
    logger.info("Initializing agent registry")
    
    # Note: Actual agent implementations will be imported and registered
    # in their respective modules. This is just the initialization framework.
    
    AgentRegistry._initialized = True
    logger.info("Agent registry initialized successfully")