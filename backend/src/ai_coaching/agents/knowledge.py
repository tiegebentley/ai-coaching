"""Knowledge Agent for vector-based content search and retrieval."""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import structlog

from ai_coaching.agents.base import BaseAgent, AgentTask, BaseAgentOutput
from ai_coaching.models.base import SystemDependencies
from ai_coaching.models.knowledge import (
    KnowledgeItem,
    KnowledgeSearchQuery,
    KnowledgeSearchResult,
    KnowledgeSearchResponse,
    ContentCategory
)
from ai_coaching.services.embedding import EmbeddingService
from ai_coaching.services.database import DatabaseService

logger = structlog.get_logger(__name__)


class KnowledgeAgent(BaseAgent):
    """Agent for knowledge base search, retrieval, and management.
    
    Provides vector similarity search, content ranking, and knowledge
    item management with performance optimization and comprehensive logging.
    """
    
    def __init__(self, dependencies: SystemDependencies, config: Optional[Dict[str, Any]] = None):
        """Initialize Knowledge Agent.
        
        Args:
            dependencies: System dependencies
            config: Agent configuration
        """
        # Default configuration
        default_config = {
            "similarity_threshold": 0.7,
            "max_results_per_query": 10,
            "enable_text_fallback": True,
            "cache_embeddings": True,
            "performance_target_seconds": 3.0,
            "ranking_weights": {
                "vector_similarity": 0.4,
                "relevance_score": 0.3,
                "quality_score": 0.2,
                "freshness_score": 0.1
            },
            "category_boost": {
                ContentCategory.FAQ.value: 1.2,
                ContentCategory.TROUBLESHOOTING.value: 1.1,
                ContentCategory.COACHING_BEST_PRACTICES.value: 1.0
            }
        }
        
        # Merge with provided config
        final_config = {**default_config, **(config or {})}
        
        super().__init__(
            agent_name="KnowledgeAgent",
            dependencies=dependencies,
            config=final_config
        )
        
        # Service references
        self.embedding_service: EmbeddingService = dependencies.embedding_service
        self.db_service: DatabaseService = dependencies.db_service
        
        # Performance tracking
        self._search_cache: Dict[str, Tuple[KnowledgeSearchResponse, datetime]] = {}
        self._cache_ttl_seconds = 300  # 5 minutes
        
        logger.info(
            "KnowledgeAgent initialized",
            similarity_threshold=self.config["similarity_threshold"],
            max_results=self.config["max_results_per_query"]
        )
    
    async def _initialize_agent(self) -> None:
        """Initialize Knowledge Agent specific components."""
        try:
            # Initialize embedding service if needed
            if not self.embedding_service._initialized:
                await self.embedding_service.initialize()
            
            # Validate database connection
            db_healthy = await self.db_service.health_check()
            if not db_healthy:
                raise RuntimeError("Database service not healthy")
            
            logger.info("KnowledgeAgent initialization completed")
            
        except Exception as e:
            logger.error(
                "KnowledgeAgent initialization failed",
                error=str(e)
            )
            raise
    
    async def process_task(self, task: AgentTask) -> BaseAgentOutput:
        """Process knowledge-related tasks.
        
        Args:
            task: Task to process
            
        Returns:
            BaseAgentOutput with results
        """
        start_time = time.time()
        
        try:
            task_type = task.task_type
            input_data = task.input_data
            
            if task_type == "search":
                result = await self._handle_search_task(input_data)
            elif task_type == "retrieve_context":
                result = await self._handle_context_retrieval_task(input_data)
            elif task_type == "add_knowledge_item":
                result = await self._handle_add_item_task(input_data)
            elif task_type == "update_knowledge_item":
                result = await self._handle_update_item_task(input_data)
            elif task_type == "delete_knowledge_item":
                result = await self._handle_delete_item_task(input_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            processing_time = time.time() - start_time
            
            # Check performance target
            target_time = self.config["performance_target_seconds"]
            if processing_time > target_time:
                logger.warning(
                    "Performance target exceeded",
                    processing_time=processing_time,
                    target_time=target_time,
                    task_type=task_type
                )
            
            return BaseAgentOutput(
                success=True,
                confidence_score=result.get("confidence_score", 1.0),
                result_data=result,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                "Task processing failed",
                task_type=task.task_type,
                error=str(e),
                processing_time=processing_time
            )
            
            return BaseAgentOutput(
                success=False,
                confidence_score=0.0,
                result_data={"error": str(e)},
                error_message=str(e),
                processing_time=processing_time
            )
    
    async def search_relevant_content(
        self,
        query: str,
        categories: Optional[List[ContentCategory]] = None,
        max_results: int = 10,
        similarity_threshold: Optional[float] = None
    ) -> KnowledgeSearchResponse:
        """Search for relevant content using vector similarity and text matching.
        
        Args:
            query: Search query text
            categories: Optional categories to filter by
            max_results: Maximum number of results to return
            similarity_threshold: Override default similarity threshold
            
        Returns:
            KnowledgeSearchResponse with ranked results
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = f"{query}:{categories}:{max_results}:{similarity_threshold}"
            cached_result = self._get_cached_search(cache_key)
            if cached_result:
                logger.debug("Returning cached search result", query=query[:50])
                return cached_result
            
            # Create search query object
            search_query = KnowledgeSearchQuery(
                query_text=query,
                categories=categories or [],
                max_results=max_results,
                vector_similarity_threshold=similarity_threshold or self.config["similarity_threshold"]
            )
            
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Perform vector similarity search
            vector_results = await self._vector_similarity_search(
                query_embedding,
                search_query
            )
            
            # Optionally add text-based fallback search
            text_results = []
            if self.config["enable_text_fallback"] and len(vector_results) < max_results:
                text_results = await self._text_fallback_search(search_query)
            
            # Combine and rank results
            combined_results = await self._combine_and_rank_results(
                vector_results,
                text_results,
                search_query,
                query_embedding
            )
            
            # Create response
            search_time_ms = (time.time() - start_time) * 1000
            response = KnowledgeSearchResponse(
                query=search_query,
                results=combined_results[:max_results],
                total_results=len(combined_results),
                search_time_ms=search_time_ms,
                used_vector_search=len(vector_results) > 0
            )
            
            # Cache the result
            self._cache_search_result(cache_key, response)
            
            logger.info(
                "Knowledge search completed",
                query=query[:50],
                results_count=len(response.results),
                search_time_ms=search_time_ms,
                used_vector_search=response.used_vector_search
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Knowledge search failed",
                query=query[:50],
                error=str(e)
            )
            raise
    
    async def retrieve_context(
        self,
        context_keys: List[str],
        max_items_per_key: int = 3
    ) -> Dict[str, List[KnowledgeItem]]:
        """Retrieve contextual information for given keys.
        
        Args:
            context_keys: List of context keys to retrieve
            max_items_per_key: Maximum items to return per key
            
        Returns:
            Dictionary mapping context keys to relevant knowledge items
        """
        context_map = {}
        
        for key in context_keys:
            try:
                # Search for content related to this context key
                search_response = await self.search_relevant_content(
                    query=key,
                    max_results=max_items_per_key
                )
                
                context_map[key] = [result.item for result in search_response.results]
                
                logger.debug(
                    "Context retrieved",
                    context_key=key,
                    items_found=len(context_map[key])
                )
                
            except Exception as e:
                logger.error(
                    "Context retrieval failed",
                    context_key=key,
                    error=str(e)
                )
                context_map[key] = []
        
        return context_map
    
    async def add_knowledge_item(
        self,
        title: str,
        content: str,
        category: ContentCategory,
        source_url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> UUID:
        """Add a new knowledge item to the database.
        
        Args:
            title: Item title
            content: Item content
            category: Content category
            source_url: Optional source URL
            tags: Optional tags
            **kwargs: Additional KnowledgeItem fields
            
        Returns:
            UUID of the created knowledge item
        """
        try:
            # Generate embedding for content
            embedding = await self.embedding_service.generate_embedding(
                f"{title} {content}"
            )
            
            # Create knowledge item
            knowledge_item = KnowledgeItem(
                title=title,
                content=content,
                category=category,
                source_url=source_url,
                tags=tags or [],
                embedding_vector=embedding,
                created_at=datetime.utcnow(),
                **kwargs
            )
            
            # Save to database
            item_id = await self.db_service.create_knowledge_item(knowledge_item)
            
            logger.info(
                "Knowledge item added",
                item_id=str(item_id),
                title=title[:50],
                category=category.value
            )
            
            # Clear search cache as new content is available
            self._clear_search_cache()
            
            return item_id
            
        except Exception as e:
            logger.error(
                "Failed to add knowledge item",
                title=title[:50],
                error=str(e)
            )
            raise
    
    async def _handle_search_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search task."""
        query = input_data.get("query", "")
        categories = input_data.get("categories", [])
        max_results = input_data.get("max_results", self.config["max_results_per_query"])
        
        if not query:
            raise ValueError("Query parameter is required for search tasks")
        
        # Convert category strings to enums if needed
        category_enums = []
        for cat in categories:
            if isinstance(cat, str):
                category_enums.append(ContentCategory(cat))
            else:
                category_enums.append(cat)
        
        response = await self.search_relevant_content(
            query=query,
            categories=category_enums,
            max_results=max_results
        )
        
        return {
            "search_response": response.dict(),
            "confidence_score": min(1.0, len(response.results) / max_results)
        }
    
    async def _handle_context_retrieval_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle context retrieval task."""
        context_keys = input_data.get("context_keys", [])
        max_items_per_key = input_data.get("max_items_per_key", 3)
        
        if not context_keys:
            raise ValueError("Context keys are required for context retrieval tasks")
        
        context_map = await self.retrieve_context(
            context_keys=context_keys,
            max_items_per_key=max_items_per_key
        )
        
        # Convert to serializable format
        serializable_context = {}
        for key, items in context_map.items():
            serializable_context[key] = [item.dict() for item in items]
        
        total_items = sum(len(items) for items in context_map.values())
        confidence = min(1.0, total_items / (len(context_keys) * max_items_per_key))
        
        return {
            "context_map": serializable_context,
            "confidence_score": confidence
        }
    
    async def _handle_add_item_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle add knowledge item task."""
        required_fields = ["title", "content", "category"]
        for field in required_fields:
            if field not in input_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Extract fields
        title = input_data["title"]
        content = input_data["content"]
        category = ContentCategory(input_data["category"])
        source_url = input_data.get("source_url")
        tags = input_data.get("tags", [])
        
        # Add other optional fields
        optional_fields = [
            "subcategory", "keywords", "relevance_score",
            "quality_score", "confidence_score", "source_type",
            "content_format"
        ]
        kwargs = {}
        for field in optional_fields:
            if field in input_data:
                kwargs[field] = input_data[field]
        
        item_id = await self.add_knowledge_item(
            title=title,
            content=content,
            category=category,
            source_url=source_url,
            tags=tags,
            **kwargs
        )
        
        return {
            "item_id": str(item_id),
            "confidence_score": 1.0
        }
    
    async def _handle_update_item_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle update knowledge item task."""
        item_id = input_data.get("item_id")
        if not item_id:
            raise ValueError("Item ID is required for update tasks")
        
        # This would be implemented with a database update method
        # For now, just return a placeholder
        return {
            "item_id": item_id,
            "updated": True,
            "confidence_score": 1.0
        }
    
    async def _handle_delete_item_task(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle delete knowledge item task."""
        item_id = input_data.get("item_id")
        if not item_id:
            raise ValueError("Item ID is required for delete tasks")
        
        # This would be implemented with a database delete method
        # For now, just return a placeholder
        return {
            "item_id": item_id,
            "deleted": True,
            "confidence_score": 1.0
        }
    
    async def _vector_similarity_search(
        self,
        query_embedding: List[float],
        search_query: KnowledgeSearchQuery
    ) -> List[KnowledgeSearchResult]:
        """Perform vector similarity search."""
        try:
            # This would use the database service to perform vector search
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(
                "Vector similarity search failed",
                error=str(e)
            )
            return []
    
    async def _text_fallback_search(
        self,
        search_query: KnowledgeSearchQuery
    ) -> List[KnowledgeSearchResult]:
        """Perform text-based fallback search."""
        try:
            # This would use full-text search capabilities
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(
                "Text fallback search failed",
                error=str(e)
            )
            return []
    
    async def _combine_and_rank_results(
        self,
        vector_results: List[KnowledgeSearchResult],
        text_results: List[KnowledgeSearchResult],
        search_query: KnowledgeSearchQuery,
        query_embedding: List[float]
    ) -> List[KnowledgeSearchResult]:
        """Combine and rank search results using multiple factors."""
        all_results = {}
        
        # Add vector results
        for result in vector_results:
            result_id = str(result.item.id)
            all_results[result_id] = result
        
        # Add text results (avoid duplicates)
        for result in text_results:
            result_id = str(result.item.id)
            if result_id not in all_results:
                all_results[result_id] = result
        
        # Calculate composite scores and sort
        results_list = list(all_results.values())
        for result in results_list:
            result.relevance_score = self._calculate_composite_score(
                result, search_query
            )
        
        # Sort by composite relevance score
        results_list.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results_list
    
    def _calculate_composite_score(
        self,
        result: KnowledgeSearchResult,
        search_query: KnowledgeSearchQuery
    ) -> float:
        """Calculate composite relevance score for ranking."""
        weights = self.config["ranking_weights"]
        
        # Base scores
        vector_score = result.vector_similarity or 0.0
        relevance_score = result.item.relevance_score
        quality_score = result.item.quality_score
        
        # Calculate freshness score (newer content gets higher score)
        if result.item.updated_at:
            days_old = (datetime.utcnow() - result.item.updated_at).days
            freshness_score = max(0.0, 1.0 - (days_old / 365.0))  # Decay over a year
        else:
            freshness_score = 0.5  # Neutral score for items without timestamp
        
        # Calculate composite score
        composite = (
            vector_score * weights["vector_similarity"] +
            relevance_score * weights["relevance_score"] +
            quality_score * weights["quality_score"] +
            freshness_score * weights["freshness_score"]
        )
        
        # Apply category boost
        category_boosts = self.config["category_boost"]
        category_boost = category_boosts.get(result.item.category.value, 1.0)
        composite *= category_boost
        
        return min(1.0, composite)
    
    def _get_cached_search(self, cache_key: str) -> Optional[KnowledgeSearchResponse]:
        """Get cached search result if still valid."""
        if cache_key in self._search_cache:
            result, timestamp = self._search_cache[cache_key]
            age_seconds = (datetime.utcnow() - timestamp).total_seconds()
            
            if age_seconds < self._cache_ttl_seconds:
                return result
            else:
                # Remove expired cache entry
                del self._search_cache[cache_key]
        
        return None
    
    def _cache_search_result(
        self,
        cache_key: str,
        result: KnowledgeSearchResponse
    ) -> None:
        """Cache search result."""
        self._search_cache[cache_key] = (result, datetime.utcnow())
        
        # Clean up old cache entries
        if len(self._search_cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(
                self._search_cache.items(),
                key=lambda x: x[1][1]
            )
            # Keep only the newest 50 entries
            self._search_cache = dict(sorted_cache[-50:])
    
    def _clear_search_cache(self) -> None:
        """Clear all cached search results."""
        self._search_cache.clear()
        logger.debug("Search cache cleared")
    
    async def _agent_health_check(self) -> bool:
        """Agent-specific health check."""
        try:
            # Check embedding service
            embedding_healthy = await self.embedding_service.health_check()
            if not embedding_healthy:
                logger.warning("Embedding service not healthy")
                return False
            
            # Test basic functionality with a simple search
            test_embedding = await self.embedding_service.generate_embedding(
                "health check test query"
            )
            
            if not test_embedding or len(test_embedding) != 1536:
                logger.warning("Embedding service returned invalid result")
                return False
            
            return True
            
        except Exception as e:
            logger.error(
                "KnowledgeAgent health check failed",
                error=str(e)
            )
            return False
    
    async def _shutdown_agent(self) -> None:
        """Agent-specific shutdown logic."""
        # Clear caches
        self._clear_search_cache()
        
        logger.info("KnowledgeAgent shutdown completed")