"""Embedding service for vector generation using OpenAI."""

import asyncio
import hashlib
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time

import structlog
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from ai_coaching.config.settings import AIConfig

logger = structlog.get_logger(__name__)


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """Initialize embedding cache.
        
        Args:
            ttl_seconds: Time to live for cached embeddings
        """
        self._cache: Dict[str, Dict] = {}
        self._ttl = ttl_seconds
    
    def _generate_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model."""
        content = f"{text}:{model}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get embedding from cache."""
        key = self._generate_key(text, model)
        
        if key in self._cache:
            entry = self._cache[key]
            
            # Check if entry is still valid
            if datetime.utcnow() < entry['expires_at']:
                logger.debug("Embedding cache hit", key=key[:8])
                return entry['embedding']
            else:
                # Remove expired entry
                del self._cache[key]
                logger.debug("Embedding cache expired", key=key[:8])
        
        return None
    
    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """Store embedding in cache."""
        key = self._generate_key(text, model)
        
        self._cache[key] = {
            'embedding': embedding,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(seconds=self._ttl)
        }
        
        logger.debug("Embedding cached", key=key[:8])
    
    def clear(self) -> None:
        """Clear all cached embeddings."""
        count = len(self._cache)
        self._cache.clear()
        logger.info("Embedding cache cleared", cleared_count=count)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        valid_entries = sum(
            1 for entry in self._cache.values()
            if now < entry['expires_at']
        )
        
        return {
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self._cache) - valid_entries
        }


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, requests_per_minute: int = 3000):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute
        """
        self._requests_per_minute = requests_per_minute
        self._requests = []
    
    async def acquire(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = time.time()
        
        # Remove requests older than 1 minute
        self._requests = [req_time for req_time in self._requests if now - req_time < 60]
        
        # Check if we need to wait
        if len(self._requests) >= self._requests_per_minute:
            # Wait until the oldest request is more than 1 minute old
            oldest_request = min(self._requests)
            wait_time = 60 - (now - oldest_request)
            
            if wait_time > 0:
                logger.info("Rate limiting - waiting", wait_time=wait_time)
                await asyncio.sleep(wait_time)
        
        # Record this request
        self._requests.append(now)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""
    
    def __init__(self, config: AIConfig):
        """Initialize embedding service.
        
        Args:
            config: AI configuration
        """
        self.config = config
        self._client: Optional[openai.AsyncOpenAI] = None
        self._cache = EmbeddingCache()
        self._rate_limiter = RateLimiter(config.rate_limit_rpm)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize OpenAI client."""
        if self._initialized:
            return
        
        try:
            self._client = openai.AsyncOpenAI(
                api_key=self.config.openai_api_key,
                timeout=self.config.request_timeout
            )
            
            # Test the connection
            await self.generate_embedding("test", use_cache=False)
            
            self._initialized = True
            logger.info("Embedding service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize embedding service", error=str(e))
            raise
    
    @property
    def client(self) -> openai.AsyncOpenAI:
        """Get OpenAI client instance."""
        if not self._client:
            raise RuntimeError("Embedding service not initialized")
        return self._client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        use_cache: bool = True
    ) -> List[float]:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
            model: Embedding model to use
            use_cache: Whether to use caching
            
        Returns:
            Embedding vector
        """
        if not text.strip():
            raise ValueError("Text cannot be empty")
        
        model = model or self.config.embedding_model
        
        # Check cache first
        if use_cache:
            cached_embedding = self._cache.get(text, model)
            if cached_embedding:
                return cached_embedding
        
        try:
            # Respect rate limits
            await self._rate_limiter.acquire()
            
            start_time = time.time()
            
            # Generate embedding
            response = await self.client.embeddings.create(
                input=text,
                model=model
            )
            
            processing_time = time.time() - start_time
            
            # Extract embedding vector
            embedding = response.data[0].embedding
            
            # Validate embedding dimensions
            if len(embedding) != 1536:  # text-embedding-ada-002 dimensions
                logger.warning(
                    "Unexpected embedding dimensions",
                    expected=1536,
                    actual=len(embedding),
                    model=model
                )
            
            # Cache the result
            if use_cache:
                self._cache.set(text, model, embedding)
            
            logger.debug(
                "Embedding generated",
                text_length=len(text),
                model=model,
                processing_time=processing_time,
                dimensions=len(embedding)
            )
            
            return embedding
            
        except Exception as e:
            logger.error(
                "Failed to generate embedding",
                error=str(e),
                text_length=len(text),
                model=model
            )
            raise
    
    async def batch_embed(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 100,
        use_cache: bool = True
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            model: Embedding model to use
            batch_size: Number of texts per batch
            use_cache: Whether to use caching
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        model = model or self.config.embedding_model
        embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Check cache for batch items
            batch_results = []
            uncached_texts = []
            uncached_indices = []
            
            for j, text in enumerate(batch):
                if use_cache:
                    cached_embedding = self._cache.get(text, model)
                    if cached_embedding:
                        batch_results.append((j, cached_embedding))
                        continue
                
                uncached_texts.append(text)
                uncached_indices.append(j)
            
            # Generate embeddings for uncached texts
            if uncached_texts:
                try:
                    # Respect rate limits
                    await self._rate_limiter.acquire()
                    
                    start_time = time.time()
                    
                    # Generate batch embeddings
                    response = await self.client.embeddings.create(
                        input=uncached_texts,
                        model=model
                    )
                    
                    processing_time = time.time() - start_time
                    
                    # Process results
                    for k, embedding_data in enumerate(response.data):
                        original_index = uncached_indices[k]
                        embedding = embedding_data.embedding
                        
                        batch_results.append((original_index, embedding))
                        
                        # Cache the result
                        if use_cache:
                            self._cache.set(uncached_texts[k], model, embedding)
                    
                    logger.info(
                        "Batch embeddings generated",
                        batch_size=len(uncached_texts),
                        processing_time=processing_time,
                        model=model
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to generate batch embeddings",
                        error=str(e),
                        batch_size=len(uncached_texts)
                    )
                    raise
            
            # Sort results by original index and add to final results
            batch_results.sort(key=lambda x: x[0])
            embeddings.extend([result[1] for result in batch_results])
        
        logger.info(
            "Batch embedding completed",
            total_texts=len(texts),
            total_embeddings=len(embeddings)
        )
        
        return embeddings
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        return self._cache.get_stats()
    
    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._cache.clear()
    
    async def health_check(self) -> bool:
        """Check embedding service health.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Try to generate a simple embedding
            test_embedding = await self.generate_embedding("health check", use_cache=False)
            
            is_healthy = isinstance(test_embedding, list) and len(test_embedding) == 1536
            
            logger.info(
                "Embedding service health check",
                is_healthy=is_healthy,
                embedding_dimensions=len(test_embedding) if test_embedding else 0
            )
            
            return is_healthy
            
        except Exception as e:
            logger.error("Embedding service health check failed", error=str(e))
            return False