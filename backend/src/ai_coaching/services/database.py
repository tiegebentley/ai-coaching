"""Database service for Supabase integration with pgvector support."""

from typing import Any, Dict, List, Optional
import asyncio
from datetime import datetime
import json

import structlog
import asyncpg
from supabase import create_client, Client as SupabaseClient
from supabase.lib.client_options import ClientOptions

from ai_coaching.config.settings import DatabaseConfig
from ai_coaching.models.base import BaseTask, TaskStatus
from ai_coaching.database.schema import DatabaseMigrator, KnowledgeItem, EmailLog, User
from ai_coaching.database.schema import search_knowledge_by_vector, create_knowledge_item, get_user_by_email

logger = structlog.get_logger(__name__)


class DatabaseService:
    """Database service for managing Supabase operations."""
    
    def __init__(self, config: DatabaseConfig):
        """Initialize database service.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self._client: Optional[SupabaseClient] = None
        self._pg_connection: Optional[asyncpg.Connection] = None
        self._migrator: Optional[DatabaseMigrator] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database connection and run migrations."""
        if self._initialized:
            return
        
        try:
            # Create Supabase client
            self._client = create_client(
                self.config.url,
                self.config.service_key,
                options=ClientOptions(
                    postgrest_client_timeout=self.config.connection_timeout
                )
            )
            
            # Initialize database migrator
            # Convert Supabase URL to PostgreSQL connection string
            pg_connection_string = self._build_pg_connection_string()
            self._migrator = DatabaseMigrator(pg_connection_string)
            
            # Run database migrations
            logger.info("Running database migrations...")
            migration_success = await self._migrator.migrate_to_latest()
            if not migration_success:
                raise RuntimeError("Database migration failed")
            
            # Validate schema
            schema_validation = await self._migrator.validate_schema()
            if not schema_validation["schema_valid"]:
                raise RuntimeError(f"Schema validation failed: {schema_validation.get('error')}")
            
            logger.info("Database schema validated successfully", 
                       current_migration=schema_validation["current_migration"])
            
            # Test connection
            await self.health_check()
            
            self._initialized = True
            logger.info("Database service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize database service", error=str(e))
            raise
    
    def _build_pg_connection_string(self) -> str:
        """Build PostgreSQL connection string from Supabase URL."""
        # Extract database connection details from Supabase URL
        # Supabase URLs are typically: https://xxx.supabase.co
        # The database connection uses the same host with port 5432
        host = self.config.url.replace('https://', '').replace('http://', '')
        
        # Build PostgreSQL connection string
        # Note: In production, you would get these from secure config
        return f"postgresql://postgres:{self.config.password}@db.{host}:5432/postgres"
    
    @property
    def client(self) -> SupabaseClient:
        """Get Supabase client instance."""
        if not self._client:
            raise RuntimeError("Database service not initialized")
        return self._client
    
    @property
    def migrator(self) -> DatabaseMigrator:
        """Get database migrator instance."""
        if not self._migrator:
            raise RuntimeError("Database service not initialized")
        return self._migrator
    
    async def health_check(self) -> bool:
        """Check database connectivity and performance.
        
        Returns:
            True if database is healthy, False otherwise
        """
        try:
            start_time = datetime.utcnow()
            
            # Test Supabase client connectivity
            result = self.client.table('system_config').select('*').limit(1).execute()
            
            response_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Additional check: validate schema if migrator is available
            schema_health = True
            if self._migrator:
                schema_validation = await self._migrator.validate_schema()
                schema_health = schema_validation["schema_valid"] and schema_validation["connection_healthy"]
            
            is_healthy = response_time < 1.0 and hasattr(result, 'data') and schema_health
            
            logger.info(
                "Database health check completed",
                response_time=response_time,
                schema_healthy=schema_health,
                is_healthy=is_healthy
            )
            
            return is_healthy
            
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
    
    async def vector_similarity_search(
        self,
        query_embedding: List[float],
        category: Optional[str] = None,
        threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search on knowledge base.
        
        Args:
            query_embedding: Query vector embedding
            category: Optional category filter
            threshold: Similarity threshold
            max_results: Maximum number of results
            
        Returns:
            List of matching knowledge items with similarity scores
        """
        try:
            # Convert embedding to proper format for pgvector
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            
            # Build query
            query = self.client.rpc(
                'search_knowledge',
                {
                    'query_embedding': embedding_str,
                    'similarity_threshold': threshold,
                    'max_results': max_results
                }
            )
            
            # Apply category filter if provided
            if category:
                query = query.eq('category', category)
            
            result = query.execute()
            
            logger.info(
                "Vector similarity search completed",
                results_count=len(result.data),
                category=category,
                threshold=threshold
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Vector similarity search failed",
                error=str(e),
                category=category
            )
            raise
    
    async def store_knowledge_item(
        self,
        title: str,
        content: str,
        category: str,
        embedding: List[float],
        tags: Optional[List[str]] = None,
        source_url: Optional[str] = None,
        relevance_score: float = 0.0
    ) -> str:
        """Store new knowledge item with vector embedding.
        
        Args:
            title: Knowledge item title
            content: Knowledge item content
            category: Content category
            embedding: Vector embedding
            tags: Optional tags
            source_url: Optional source URL
            relevance_score: Relevance score
            
        Returns:
            ID of the stored knowledge item
        """
        try:
            # Convert embedding to proper format
            embedding_str = f"[{','.join(map(str, embedding))}]"
            
            data = {
                'title': title,
                'content': content,
                'category': category,
                'embedding': embedding_str,
                'tags': tags or [],
                'source_url': source_url,
                'relevance_score': relevance_score
            }
            
            result = self.client.table('knowledge_base').insert(data).execute()
            
            knowledge_id = result.data[0]['id']
            
            logger.info(
                "Knowledge item stored",
                knowledge_id=knowledge_id,
                title=title,
                category=category
            )
            
            return knowledge_id
            
        except Exception as e:
            logger.error(
                "Failed to store knowledge item",
                error=str(e),
                title=title
            )
            raise
    
    async def log_email_processing(
        self,
        gmail_id: str,
        sender: str,
        subject: str,
        draft_content: str,
        confidence: float,
        requires_review: bool = False
    ) -> str:
        """Log email processing results.
        
        Args:
            gmail_id: Gmail message ID
            sender: Sender email address
            subject: Email subject
            draft_content: Generated draft content
            confidence: Confidence score
            requires_review: Whether human review is required
            
        Returns:
            ID of the log entry
        """
        try:
            data = {
                'gmail_message_id': gmail_id,
                'sender_email': sender,
                'subject': subject,
                'processing_status': 'draft_generated',
                'draft_content': draft_content,
                'confidence_score': confidence,
                'requires_review': requires_review
            }
            
            result = self.client.table('email_logs').insert(data).execute()
            
            log_id = result.data[0]['id']
            
            logger.info(
                "Email processing logged",
                log_id=log_id,
                gmail_id=gmail_id,
                confidence=confidence
            )
            
            return log_id
            
        except Exception as e:
            logger.error(
                "Failed to log email processing",
                error=str(e),
                gmail_id=gmail_id
            )
            raise
    
    async def get_task_queue(
        self,
        agent_type: Optional[str] = None,
        status: str = "pending",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve pending tasks for agent processing.
        
        Args:
            agent_type: Filter by agent type
            status: Task status filter
            limit: Maximum number of tasks
            
        Returns:
            List of task records
        """
        try:
            query = self.client.table('task_queue').select('*')
            
            if agent_type:
                query = query.eq('agent_type', agent_type)
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('priority', desc=True).limit(limit).execute()
            
            logger.info(
                "Retrieved task queue",
                agent_type=agent_type,
                status=status,
                task_count=len(result.data)
            )
            
            return result.data
            
        except Exception as e:
            logger.error(
                "Failed to retrieve task queue",
                error=str(e),
                agent_type=agent_type
            )
            raise
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result_data: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update task completion status and results.
        
        Args:
            task_id: Task ID
            status: New status
            result_data: Task result data
            error_message: Error message if failed
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            data = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if result_data:
                data['result_data'] = result_data
            
            if error_message:
                data['error_message'] = error_message
            
            if status in ['completed', 'failed', 'cancelled']:
                data['completed_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table('task_queue').update(data).eq('id', task_id).execute()
            
            success = len(result.data) > 0
            
            logger.info(
                "Task status updated",
                task_id=task_id,
                status=status,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to update task status",
                error=str(e),
                task_id=task_id
            )
            return False
    
    async def get_system_config(self, key: str) -> Optional[Dict[str, Any]]:
        """Get system configuration value.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value or None if not found
        """
        try:
            result = self.client.table('system_config').select('*').eq('config_key', key).execute()
            
            if result.data:
                return result.data[0]['config_value']
            
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get system config",
                error=str(e),
                key=key
            )
            return None
    
    async def set_system_config(self, key: str, value: Dict[str, Any], description: str = "") -> bool:
        """Set system configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            description: Configuration description
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'config_key': key,
                'config_value': value,
                'description': description
            }
            
            # Use upsert to handle both insert and update
            result = self.client.table('system_config').upsert(data).execute()
            
            success = len(result.data) > 0
            
            logger.info(
                "System config updated",
                key=key,
                success=success
            )
            
            return success
            
        except Exception as e:
            logger.error(
                "Failed to set system config",
                error=str(e),
                key=key
            )
            return False