"""System configuration settings using Pydantic Settings."""

from typing import List, Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SUPABASE_",
        env_file=".env",
        case_sensitive=False
    )
    
    url: str = Field(description="Supabase project URL")
    anon_key: str = Field(description="Supabase anonymous key")
    service_key: str = Field(description="Supabase service role key")
    password: str = Field(description="Supabase database password")
    max_connections: int = Field(default=20, description="Maximum database connections")
    connection_timeout: int = Field(default=30, description="Connection timeout in seconds")


class AIConfig(BaseSettings):
    """AI model configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="AI_",
        env_file=".env",
        case_sensitive=False
    )
    
    openai_api_key: str = Field(description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    default_model: str = Field(default="openai:gpt-4o", description="Default AI model")
    embedding_model: str = Field(default="text-embedding-ada-002", description="Embedding model")
    max_tokens: int = Field(default=4096, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Model temperature")
    request_timeout: int = Field(default=60, description="AI request timeout in seconds")
    rate_limit_rpm: int = Field(default=3000, description="Rate limit requests per minute")


class AirtableConfig(BaseSettings):
    """Airtable integration configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="AIRTABLE_",
        env_file=".env",
        case_sensitive=False
    )
    
    api_key: str = Field(description="Airtable API key")
    base_id: str = Field(default="appsdldIgkZ1fDzX2", description="secondBrainExec base ID")
    rate_limit_rps: int = Field(default=5, description="Rate limit requests per second")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Maximum retry attempts")


class GmailConfig(BaseSettings):
    """Gmail API configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="GOOGLE_",
        env_file=".env",
        case_sensitive=False
    )
    
    client_id: str = Field(description="Google OAuth client ID")
    client_secret: str = Field(description="Google OAuth client secret")
    redirect_uri: str = Field(default="http://localhost:8000/auth/google/callback", description="OAuth redirect URI")
    scopes: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify"
        ],
        description="Gmail API scopes"
    )
    webhook_endpoint: str = Field(default="/api/gmail-webhook", description="Gmail webhook endpoint")


class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    model_config = SettingsConfigDict(
        env_prefix="SECURITY_",
        env_file=".env",
        case_sensitive=False
    )
    
    jwt_secret_key: str = Field(description="JWT signing secret")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_hours: int = Field(default=24, description="JWT token expiration hours")
    password_hash_rounds: int = Field(default=12, description="bcrypt hash rounds")
    api_rate_limit: int = Field(default=100, description="API requests per minute")
    encryption_key: str = Field(description="Data encryption key")


class SystemConfig(BaseSettings):
    """Main system configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
    # Environment settings
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=True, description="Auto-reload in development")
    
    # Application settings
    app_name: str = Field(default="AI Coaching Management System", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    
    # Performance settings
    worker_processes: int = Field(default=1, description="Number of worker processes")
    max_request_size: int = Field(default=16 * 1024 * 1024, description="Max request size in bytes")
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    airtable: AirtableConfig = Field(default_factory=AirtableConfig)
    gmail: GmailConfig = Field(default_factory=GmailConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment."""
        valid_envs = {"development", "testing", "staging", "production"}
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment. Must be one of: {valid_envs}")
        return v.lower()


# Global configuration instance
config = SystemConfig()


def get_config() -> SystemConfig:
    """Get the global configuration instance."""
    return config