#!/usr/bin/env python3
"""Quick validation script for the EmbeddingService."""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to Python path
backend_dir = Path(__file__).parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from ai_coaching.config.settings import AIConfig
from ai_coaching.services.embedding import EmbeddingService


async def test_embedding_service():
    """Test embedding service functionality."""
    print("Testing EmbeddingService...")
    
    # Check if OpenAI API key is configured
    if not os.getenv("AI_OPENAI_API_KEY"):
        print("❌ OpenAI API key not found. Set AI_OPENAI_API_KEY environment variable.")
        return False
    
    try:
        # Initialize service
        config = AIConfig()
        service = EmbeddingService(config)
        print("✅ EmbeddingService initialized")
        
        # Test single embedding generation
        print("\nTesting single embedding...")
        test_text = "This is a test text for embedding generation."
        embedding = await service.generate_embedding(test_text)
        
        print(f"✅ Generated embedding with {len(embedding)} dimensions")
        
        if len(embedding) != 1536:
            print(f"❌ Expected 1536 dimensions, got {len(embedding)}")
            return False
        
        # Test batch embedding generation
        print("\nTesting batch embeddings...")
        test_texts = [
            "First test text",
            "Second test text", 
            "Third test text"
        ]
        
        batch_embeddings = await service.batch_embed(test_texts)
        print(f"✅ Generated {len(batch_embeddings)} batch embeddings")
        
        if len(batch_embeddings) != len(test_texts):
            print(f"❌ Expected {len(test_texts)} embeddings, got {len(batch_embeddings)}")
            return False
        
        # Test caching
        print("\nTesting caching...")
        cached_embedding = await service.generate_embedding(test_text)  # Should be cached
        
        if cached_embedding != embedding:
            print("❌ Cached embedding doesn't match original")
            return False
        
        print("✅ Caching works correctly")
        
        # Test health check
        print("\nTesting health check...")
        is_healthy = await service.health_check()
        
        if not is_healthy:
            print("❌ Health check failed")
            return False
        
        print("✅ Health check passed")
        
        # Display cache stats
        stats = service.get_cache_stats()
        print(f"\nCache stats: {stats}")
        
        print("\n🎉 All embedding service tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_embedding_service())
    sys.exit(0 if success else 1)