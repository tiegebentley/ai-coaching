"""Knowledge base data models with comprehensive validation and typing."""

import re
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
import structlog

logger = structlog.get_logger(__name__)


class ContentCategory(str, Enum):
    """Knowledge base content categories."""
    COACHING_BEST_PRACTICES = "coaching_best_practices"
    YOUTH_DEVELOPMENT = "youth_development"
    PARENT_COMMUNICATION = "parent_communication"
    SCHEDULE_MANAGEMENT = "schedule_management"
    SAFETY_PROTOCOLS = "safety_protocols"
    TEAM_BUILDING = "team_building"
    TECHNICAL_SKILLS = "technical_skills"
    ADMINISTRATIVE = "administrative"
    POLICIES_PROCEDURES = "policies_procedures"
    FAQ = "faq"
    TROUBLESHOOTING = "troubleshooting"
    OTHER = "other"


class ContentSource(str, Enum):
    """Source of knowledge content."""
    MANUAL_ENTRY = "manual_entry"
    DOCUMENTATION = "documentation"
    EMAIL_THREAD = "email_thread"
    WEBSITE = "website"
    TRAINING_MATERIAL = "training_material"
    BEST_PRACTICES = "best_practices"
    FAQ_SYSTEM = "faq_system"
    EXTERNAL_API = "external_api"
    USER_GENERATED = "user_generated"


class ContentFormat(str, Enum):
    """Format of the content."""
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    STRUCTURED_DATA = "structured_data"


class KnowledgeItemMetadata(BaseModel):
    """Metadata for knowledge base items."""
    language: str = Field(default="en", description="Content language code")
    word_count: Optional[int] = Field(None, description="Approximate word count")
    reading_time_minutes: Optional[int] = Field(None, description="Estimated reading time")
    last_reviewed: Optional[datetime] = Field(None, description="Last content review date")
    review_frequency_days: Optional[int] = Field(None, description="How often content should be reviewed")
    access_count: int = Field(default=0, description="Number of times content was accessed")
    usefulness_score: float = Field(default=0.0, ge=0.0, le=1.0, description="User-rated usefulness")
    freshness_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Content freshness/recency")


class KnowledgeItem(BaseModel):
    """Enhanced knowledge base item with comprehensive validation."""
    
    # Core fields
    id: Optional[UUID] = Field(None, description="Unique identifier")
    title: str = Field(..., min_length=1, max_length=500, description="Item title")
    content: str = Field(..., min_length=1, description="Main content")
    summary: Optional[str] = Field(None, max_length=1000, description="Brief content summary")
    
    # Classification
    category: ContentCategory = Field(..., description="Content category")
    subcategory: Optional[str] = Field(None, max_length=100, description="More specific classification")
    tags: List[str] = Field(default_factory=list, description="Content tags for filtering")
    keywords: List[str] = Field(default_factory=list, description="Important keywords")
    
    # Source and format
    source_type: ContentSource = Field(..., description="Content source type")
    source_url: Optional[str] = Field(None, description="Original source URL")
    source_reference: Optional[str] = Field(None, description="Additional source reference")
    content_format: ContentFormat = Field(default=ContentFormat.TEXT, description="Content format")
    
    # Relevance and quality
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Content relevance score")
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Content quality score")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in accuracy")
    
    # Vector embedding
    embedding_vector: Optional[List[float]] = Field(None, description="Vector embedding for similarity search")
    embedding_model: str = Field(default="text-embedding-ada-002", description="Model used for embedding")
    
    # Metadata
    metadata: KnowledgeItemMetadata = Field(default_factory=KnowledgeItemMetadata, description="Additional metadata")
    
    # Relationships
    parent_id: Optional[UUID] = Field(None, description="Parent item for hierarchical content")
    related_items: List[UUID] = Field(default_factory=list, description="Related knowledge items")
    
    # Versioning
    version: int = Field(default=1, description="Content version number")
    is_current_version: bool = Field(default=True, description="Whether this is the current version")
    superseded_by: Optional[UUID] = Field(None, description="ID of item that supersedes this one")
    
    # Access control
    is_public: bool = Field(default=True, description="Whether content is publicly accessible")
    required_role: Optional[str] = Field(None, description="Minimum role required to access")
    
    # Audit fields
    created_by: Optional[UUID] = Field(None, description="User who created the item")
    updated_by: Optional[UUID] = Field(None, description="User who last updated the item")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            UUID: lambda uuid: str(uuid)
        }
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        """Validate title format."""
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace only')
        return v.strip()
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate content format."""
        if not v.strip():
            raise ValueError('Content cannot be empty or whitespace only')
        if len(v) > 1_000_000:  # 1MB text limit
            raise ValueError('Content too large (max 1MB)')
        return v.strip()
    
    @field_validator('embedding_vector')
    @classmethod
    def validate_embedding_dimensions(cls, v):
        """Validate embedding vector dimensions."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError('Embedding vector must be a list')
            if len(v) != 1536:
                raise ValueError('Embedding must have exactly 1536 dimensions for text-embedding-ada-002')
            if not all(isinstance(x, (int, float)) for x in v):
                raise ValueError('Embedding vector must contain only numeric values')
        return v
    
    @field_validator('tags', 'keywords')
    @classmethod
    def validate_tags_keywords(cls, v):
        """Validate tags and keywords format."""
        if v is None:
            return []
        
        # Clean and validate each tag/keyword
        cleaned = []
        for item in v:
            if isinstance(item, str) and item.strip():
                # Remove extra whitespace and convert to lowercase
                clean_item = re.sub(r'\s+', ' ', item.strip().lower())
                if len(clean_item) <= 50:  # Max length per tag
                    cleaned.append(clean_item)
        
        return cleaned
    
    @field_validator('source_url')
    @classmethod
    def validate_source_url(cls, v):
        """Validate source URL format."""
        if v is not None:
            v = v.strip()
            if v and not (v.startswith('http://') or v.startswith('https://') or v.startswith('file://')):
                raise ValueError('Source URL must be a valid HTTP, HTTPS, or file URL')
        return v
    
    @model_validator(mode='after')
    def validate_scores_consistency(self):
        """Validate score relationships and consistency."""
        relevance = self.relevance_score
        quality = self.quality_score
        confidence = self.confidence_score
        
        # Quality cannot exceed confidence (you can't be sure about something you're not confident in)
        if confidence > 0 and quality > confidence:
            raise ValueError('Quality score cannot exceed confidence score')
        
        # High relevance with very low quality is suspicious
        if relevance > 0.8 and quality < 0.3:
            logger.warning("High relevance with low quality detected", relevance=relevance, quality=quality)
        
        return self
    
    def calculate_composite_score(self) -> float:
        """Calculate a composite score for ranking."""
        weights = {
            'relevance': 0.4,
            'quality': 0.3,
            'confidence': 0.2,
            'usefulness': 0.1
        }
        
        composite = (
            self.relevance_score * weights['relevance'] +
            self.quality_score * weights['quality'] +
            self.confidence_score * weights['confidence'] +
            self.metadata.usefulness_score * weights['usefulness']
        )
        
        return round(composite, 3)
    
    def update_access_stats(self) -> None:
        """Update access statistics."""
        self.metadata.access_count += 1
        self.updated_at = datetime.utcnow()
    
    def is_outdated(self, max_age_days: int = 365) -> bool:
        """Check if content is potentially outdated."""
        if not self.updated_at:
            return True
        
        age_days = (datetime.utcnow() - self.updated_at).days
        return age_days > max_age_days
    
    def to_search_text(self) -> str:
        """Generate optimized text for search indexing."""
        search_parts = [
            self.title,
            self.content,
            self.summary or "",
            " ".join(self.tags),
            " ".join(self.keywords),
            self.category.value.replace('_', ' '),
            self.subcategory or ""
        ]
        
        return " ".join(filter(None, search_parts))


class KnowledgeSearchQuery(BaseModel):
    """Model for knowledge base search queries."""
    query_text: str = Field(..., min_length=1, description="Search query text")
    categories: List[ContentCategory] = Field(default_factory=list, description="Filter by categories")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    source_types: List[ContentSource] = Field(default_factory=list, description="Filter by source types")
    min_relevance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum relevance score")
    min_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum quality score")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    include_outdated: bool = Field(default=False, description="Include potentially outdated content")
    vector_similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Vector similarity threshold")
    
    class Config:
        use_enum_values = True


class KnowledgeSearchResult(BaseModel):
    """Search result with relevance scoring."""
    item: KnowledgeItem = Field(..., description="Found knowledge item")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Search relevance score")
    match_type: str = Field(..., description="Type of match (vector, text, tag, etc.)")
    matched_snippets: List[str] = Field(default_factory=list, description="Relevant text snippets")
    vector_similarity: Optional[float] = Field(None, description="Vector similarity score if applicable")
    
    class Config:
        use_enum_values = True


class KnowledgeSearchResponse(BaseModel):
    """Response from knowledge search operation."""
    query: KnowledgeSearchQuery = Field(..., description="Original search query")
    results: List[KnowledgeSearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of matching items")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    used_vector_search: bool = Field(default=False, description="Whether vector search was used")
    
    class Config:
        use_enum_values = True


class KnowledgeBatchOperation(BaseModel):
    """Model for batch operations on knowledge items."""
    operation: str = Field(..., description="Operation type: 'create', 'update', 'delete', 'reindex'")
    items: List[Union[KnowledgeItem, UUID]] = Field(..., description="Items to process")
    options: Dict[str, Any] = Field(default_factory=dict, description="Operation-specific options")
    batch_size: int = Field(default=100, ge=1, le=1000, description="Processing batch size")
    
    @field_validator('operation')
    @classmethod
    def validate_operation(cls, v):
        """Validate operation type."""
        valid_ops = {'create', 'update', 'delete', 'reindex', 'recalculate_scores', 'update_embeddings'}
        if v not in valid_ops:
            raise ValueError(f'Invalid operation. Must be one of: {valid_ops}')
        return v


class KnowledgeStats(BaseModel):
    """Knowledge base statistics."""
    total_items: int = Field(..., description="Total number of knowledge items")
    items_by_category: Dict[str, int] = Field(..., description="Count by category")
    items_by_source: Dict[str, int] = Field(..., description="Count by source type")
    avg_relevance_score: float = Field(..., description="Average relevance score")
    avg_quality_score: float = Field(..., description="Average quality score")
    total_access_count: int = Field(..., description="Total access count across all items")
    outdated_items_count: int = Field(..., description="Number of potentially outdated items")
    items_without_embeddings: int = Field(..., description="Items missing vector embeddings")
    last_updated: datetime = Field(..., description="When statistics were last calculated")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }