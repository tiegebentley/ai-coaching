"""Database schema definitions and migration utilities for AI Coaching System.

This module provides Pydantic models that correspond to the database schema,
migration utilities, and database connection management.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, validator
import asyncpg
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

# Enums matching database types
class UserRole(str, Enum):
    ADMIN = "admin"
    COACH = "coach"  
    ASSISTANT = "assistant"

class EmailCategory(str, Enum):
    SCHEDULE_REQUEST = "schedule_request"
    PAYMENT_INQUIRY = "payment_inquiry"
    ABSENCE_NOTICE = "absence_notice"
    GENERAL_QUESTION = "general_question"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    EMERGENCY = "emergency"
    OTHER = "other"

class EmailPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentType(str, Enum):
    EMAIL_PROCESSING = "email_processing"
    SCHEDULE_OPTIMIZATION = "schedule_optimization"
    KNOWLEDGE_BASE = "knowledge_base"
    ORCHESTRATOR = "orchestrator"

# Pydantic models for database entities
class User(BaseModel):
    """User model matching the users table schema."""
    id: UUID
    email: str
    name: str
    role: UserRole
    password_hash: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True

class KnowledgeItem(BaseModel):
    """Knowledge base item with vector embedding."""
    id: UUID
    title: str = Field(..., max_length=500)
    content: str
    source_url: Optional[str] = None
    category: str = Field(..., max_length=100)
    tags: List[str] = []
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    embedding: Optional[List[float]] = None  # Vector embedding
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    @validator('embedding')
    def validate_embedding_dimensions(cls, v):
        if v is not None and len(v) != 1536:
            raise ValueError('Embedding must have exactly 1536 dimensions for OpenAI text-embedding-ada-002')
        return v

class EmailLog(BaseModel):
    """Email processing log entry."""
    id: UUID
    thread_id: str
    message_id: str
    subject: str
    sender_name: Optional[str] = None
    sender_email: str
    recipient_email: str
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    category: EmailCategory = EmailCategory.OTHER
    priority: EmailPriority = EmailPriority.MEDIUM
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    ai_summary: Optional[str] = None
    ai_draft_response: Optional[str] = None
    is_processed: bool = False
    is_approved: bool = False
    is_sent: bool = False
    processed_by: Optional[UUID] = None
    processed_at: Optional[datetime] = None
    received_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True

class SystemConfig(BaseModel):
    """System configuration entry."""
    id: UUID
    key: str
    value: Dict[str, Any]  # JSONB field
    description: Optional[str] = None
    is_sensitive: bool = False
    updated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

class TaskQueue(BaseModel):
    """Asynchronous task queue entry."""
    id: UUID
    task_type: str
    agent_type: AgentType
    payload: Dict[str, Any]  # JSONB field
    status: TaskStatus = TaskStatus.PENDING
    priority: int = Field(default=5, ge=1, le=10)
    attempts: int = 0
    max_attempts: int = 3
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        use_enum_values = True

class AgentLog(BaseModel):
    """Agent activity log entry."""
    id: UUID
    agent_type: AgentType
    task_id: Optional[UUID] = None
    action: str
    details: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        use_enum_values = True

class EmailProcessingStats(BaseModel):
    """Email processing analytics model."""
    date: datetime
    category: EmailCategory
    priority: EmailPriority
    total_emails: int
    processed_emails: int
    approved_emails: int
    sent_emails: int
    avg_confidence: Optional[float] = None
    avg_processing_minutes: Optional[float] = None

    class Config:
        use_enum_values = True

# Migration utilities
class DatabaseMigrator:
    """Database migration manager for AI Coaching System."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.migrations_dir = Path(__file__).parent / "migrations"

    async def get_connection(self) -> asyncpg.Connection:
        """Get database connection."""
        return await asyncpg.connect(self.connection_string)

    async def get_current_migration_version(self) -> str:
        """Get the current migration version from database."""
        try:
            conn = await self.get_connection()
            try:
                result = await conn.fetchval(
                    "SELECT value->>'migration_version' FROM system_config WHERE key = 'migration_version'"
                )
                return result or "000"
            finally:
                await conn.close()
        except Exception as e:
            logger.warning("Could not fetch migration version, assuming fresh database", error=str(e))
            return "000"

    async def get_available_migrations(self) -> List[str]:
        """Get list of available migration files."""
        if not self.migrations_dir.exists():
            return []
        
        migrations = []
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            migration_id = file_path.stem.split('_')[0]
            migrations.append(migration_id)
        
        return migrations

    async def run_migration(self, migration_id: str) -> bool:
        """Run a specific migration."""
        migration_file = self.migrations_dir / f"{migration_id}_*.sql"
        migration_files = list(self.migrations_dir.glob(f"{migration_id}_*.sql"))
        
        if not migration_files:
            logger.error("Migration file not found", migration_id=migration_id)
            return False

        migration_file = migration_files[0]
        
        try:
            conn = await self.get_connection()
            try:
                # Read and execute migration SQL
                migration_sql = migration_file.read_text(encoding='utf-8')
                
                logger.info("Running migration", migration_id=migration_id, file=str(migration_file))
                
                # Execute in a transaction
                async with conn.transaction():
                    await conn.execute(migration_sql)
                    
                    # Update migration version
                    await conn.execute("""
                        INSERT INTO system_config (key, value, description) 
                        VALUES ('migration_version', to_jsonb($1), 'Current database migration version')
                        ON CONFLICT (key) DO UPDATE SET 
                            value = to_jsonb($1),
                            updated_at = NOW()
                    """, migration_id)

                logger.info("Migration completed successfully", migration_id=migration_id)
                return True
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error("Migration failed", migration_id=migration_id, error=str(e))
            return False

    async def migrate_to_latest(self) -> bool:
        """Run all pending migrations."""
        current_version = await self.get_current_migration_version()
        available_migrations = await self.get_available_migrations()
        
        if not available_migrations:
            logger.info("No migrations available")
            return True

        # Find migrations to run
        pending_migrations = [m for m in available_migrations if m > current_version]
        
        if not pending_migrations:
            logger.info("Database is up to date", current_version=current_version)
            return True

        logger.info("Running pending migrations", 
                   current_version=current_version,
                   pending_migrations=pending_migrations)

        # Run each pending migration
        for migration_id in pending_migrations:
            success = await self.run_migration(migration_id)
            if not success:
                logger.error("Migration sequence failed", failed_migration=migration_id)
                return False

        logger.info("All migrations completed successfully")
        return True

    async def validate_schema(self) -> Dict[str, Any]:
        """Validate database schema and return health information."""
        try:
            conn = await self.get_connection()
            try:
                # Check if required extensions are installed
                extensions = await conn.fetch("""
                    SELECT extname, extversion 
                    FROM pg_extension 
                    WHERE extname IN ('vector', 'uuid-ossp')
                """)
                
                # Check if required tables exist
                tables = await conn.fetch("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename IN ('users', 'knowledge_base', 'email_logs', 'system_config', 'task_queue', 'agent_logs')
                """)
                
                # Check if vector index exists
                vector_indexes = await conn.fetch("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'knowledge_base' 
                    AND indexdef LIKE '%vector%'
                """)

                # Get current migration version
                current_version = await self.get_current_migration_version()

                return {
                    "schema_valid": True,
                    "current_migration": current_version,
                    "extensions": [dict(r) for r in extensions],
                    "tables": [r['tablename'] for r in tables],
                    "vector_indexes": [r['indexname'] for r in vector_indexes],
                    "connection_healthy": True
                }
                
            finally:
                await conn.close()
                
        except Exception as e:
            logger.error("Schema validation failed", error=str(e))
            return {
                "schema_valid": False,
                "error": str(e),
                "connection_healthy": False
            }

# Utility functions for common database operations
async def get_user_by_email(conn: asyncpg.Connection, email: str) -> Optional[User]:
    """Get user by email address."""
    row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
    return User(**dict(row)) if row else None

async def create_knowledge_item(conn: asyncpg.Connection, item: KnowledgeItem) -> UUID:
    """Create a new knowledge base item."""
    item_id = await conn.fetchval("""
        INSERT INTO knowledge_base 
        (title, content, source_url, category, tags, relevance_score, embedding, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
    """, item.title, item.content, item.source_url, item.category, 
        item.tags, item.relevance_score, item.embedding, item.created_by)
    
    return item_id

async def search_knowledge_by_vector(
    conn: asyncpg.Connection, 
    query_embedding: List[float], 
    limit: int = 5,
    similarity_threshold: float = 0.7
) -> List[KnowledgeItem]:
    """Search knowledge base using vector similarity."""
    rows = await conn.fetch("""
        SELECT *, (embedding <=> $1) as distance
        FROM knowledge_base 
        WHERE embedding <=> $1 < $2
        ORDER BY embedding <=> $1
        LIMIT $3
    """, query_embedding, 1.0 - similarity_threshold, limit)
    
    return [KnowledgeItem(**dict(row)) for row in rows]