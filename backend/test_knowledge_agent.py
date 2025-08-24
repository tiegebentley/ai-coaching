#!/usr/bin/env python3
"""Test script for KnowledgeAgent implementation."""

import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Add src directory to Python path
backend_dir = Path(__file__).parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from ai_coaching.agents.knowledge import KnowledgeAgent
from ai_coaching.agents.base import AgentTask
from ai_coaching.models.base import SystemDependencies
from ai_coaching.models.knowledge import ContentCategory
from ai_coaching.config.settings import SystemConfig
import structlog

# Mock logger to prevent import issues
structlog.get_logger = lambda x: MagicMock()


def create_mock_dependencies():
    """Create mock system dependencies for testing."""
    dependencies = MagicMock(spec=SystemDependencies)
    
    # Mock embedding service
    embedding_service = AsyncMock()
    embedding_service._initialized = True
    embedding_service.health_check = AsyncMock(return_value=True)
    embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    dependencies.embedding_service = embedding_service
    
    # Mock database service
    db_service = AsyncMock()
    db_service.health_check = AsyncMock(return_value=True)
    db_service.create_knowledge_item = AsyncMock(return_value="test-uuid-123")
    dependencies.db_service = db_service
    
    # Mock other services
    dependencies.airtable_service = AsyncMock()
    dependencies.gmail_service = AsyncMock()
    dependencies.config = MagicMock()
    dependencies.logger = MagicMock()
    
    return dependencies


async def test_knowledge_agent_initialization():
    """Test KnowledgeAgent initialization."""
    print("Testing KnowledgeAgent initialization...")
    
    try:
        dependencies = create_mock_dependencies()
        
        agent = KnowledgeAgent(dependencies)
        
        # Test initialization
        init_success = await agent.initialize()
        
        if not init_success:
            print("❌ Agent initialization failed")
            return False
        
        print("✅ KnowledgeAgent initialized successfully")
        print(f"   - Agent name: {agent.agent_name}")
        print(f"   - Similarity threshold: {agent.config['similarity_threshold']}")
        print(f"   - Max results: {agent.config['max_results_per_query']}")
        
        # Test status
        status = await agent.get_status()
        
        if not status.is_healthy:
            print("❌ Agent status shows unhealthy")
            return False
        
        print("✅ Agent status is healthy")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent initialization test failed: {e}")
        return False


async def test_search_task_processing():
    """Test search task processing."""
    print("\nTesting search task processing...")
    
    try:
        dependencies = create_mock_dependencies()
        agent = KnowledgeAgent(dependencies)
        
        await agent.initialize()
        
        # Create a search task
        task = AgentTask(
            task_type="search",
            input_data={
                "query": "How to handle difficult parents?",
                "categories": [ContentCategory.PARENT_COMMUNICATION.value],
                "max_results": 5
            }
        )
        
        # Process the task
        result = await agent.process_task(task)
        
        if not result.success:
            print(f"❌ Search task failed: {result.error_message}")
            return False
        
        print("✅ Search task processed successfully")
        print(f"   - Processing time: {result.processing_time:.3f}s")
        print(f"   - Confidence score: {result.confidence_score:.3f}")
        
        # Verify result structure
        if "search_response" not in result.result_data:
            print("❌ Search response not found in result data")
            return False
        
        print("✅ Search response structure is valid")
        
        return True
        
    except Exception as e:
        print(f"❌ Search task test failed: {e}")
        return False


async def test_add_knowledge_item_task():
    """Test adding knowledge item."""
    print("\nTesting add knowledge item task...")
    
    try:
        dependencies = create_mock_dependencies()
        agent = KnowledgeAgent(dependencies)
        
        await agent.initialize()
        
        # Create an add item task
        task = AgentTask(
            task_type="add_knowledge_item",
            input_data={
                "title": "Effective Parent Communication",
                "content": "Best practices for communicating with parents about their children's soccer development.",
                "category": ContentCategory.PARENT_COMMUNICATION.value,
                "tags": ["communication", "parents", "development"],
                "source_url": "https://example.com/parent-guide",
                "relevance_score": 0.9,
                "quality_score": 0.8
            }
        )
        
        # Process the task
        result = await agent.process_task(task)
        
        if not result.success:
            print(f"❌ Add item task failed: {result.error_message}")
            return False
        
        print("✅ Add knowledge item task processed successfully")
        print(f"   - Item ID: {result.result_data.get('item_id')}")
        print(f"   - Processing time: {result.processing_time:.3f}s")
        
        # Verify embedding service was called
        embedding_call_count = dependencies.embedding_service.generate_embedding.call_count
        if embedding_call_count == 0:
            print("❌ Embedding service was not called")
            return False
        
        print("✅ Embedding service was properly utilized")
        
        # Verify database service was called
        db_call_count = dependencies.db_service.create_knowledge_item.call_count
        if db_call_count == 0:
            print("❌ Database service was not called")
            return False
        
        print("✅ Database service was properly utilized")
        
        return True
        
    except Exception as e:
        print(f"❌ Add item task test failed: {e}")
        return False


async def test_context_retrieval_task():
    """Test context retrieval task."""
    print("\nTesting context retrieval task...")
    
    try:
        dependencies = create_mock_dependencies()
        agent = KnowledgeAgent(dependencies)
        
        await agent.initialize()
        
        # Create a context retrieval task
        task = AgentTask(
            task_type="retrieve_context",
            input_data={
                "context_keys": ["parent communication", "scheduling conflicts", "payment issues"],
                "max_items_per_key": 2
            }
        )
        
        # Process the task
        result = await agent.process_task(task)
        
        if not result.success:
            print(f"❌ Context retrieval task failed: {result.error_message}")
            return False
        
        print("✅ Context retrieval task processed successfully")
        print(f"   - Processing time: {result.processing_time:.3f}s")
        print(f"   - Confidence score: {result.confidence_score:.3f}")
        
        # Verify result structure
        context_map = result.result_data.get("context_map", {})
        if len(context_map) != 3:
            print(f"❌ Expected 3 context keys, got {len(context_map)}")
            return False
        
        print("✅ Context retrieval returned expected structure")
        
        return True
        
    except Exception as e:
        print(f"❌ Context retrieval task test failed: {e}")
        return False


async def test_agent_health_check():
    """Test agent health check."""
    print("\nTesting agent health check...")
    
    try:
        dependencies = create_mock_dependencies()
        agent = KnowledgeAgent(dependencies)
        
        await agent.initialize()
        
        # Perform health check
        is_healthy = await agent.health_check()
        
        if not is_healthy:
            print("❌ Agent health check failed")
            return False
        
        print("✅ Agent health check passed")
        
        # Test with unhealthy embedding service
        dependencies.embedding_service.health_check = AsyncMock(return_value=False)
        
        is_healthy = await agent.health_check()
        
        if is_healthy:
            print("❌ Agent should be unhealthy when embedding service is down")
            return False
        
        print("✅ Agent correctly reports unhealthy when dependencies fail")
        
        return True
        
    except Exception as e:
        print(f"❌ Health check test failed: {e}")
        return False


async def test_invalid_task_handling():
    """Test handling of invalid tasks."""
    print("\nTesting invalid task handling...")
    
    try:
        dependencies = create_mock_dependencies()
        agent = KnowledgeAgent(dependencies)
        
        await agent.initialize()
        
        # Test invalid task type
        invalid_task = AgentTask(
            task_type="invalid_task_type",
            input_data={}
        )
        
        result = await agent.process_task(invalid_task)
        
        if result.success:
            print("❌ Invalid task should have failed")
            return False
        
        print("✅ Invalid task type properly rejected")
        
        # Test missing required parameters
        incomplete_task = AgentTask(
            task_type="search",
            input_data={}  # Missing query parameter
        )
        
        result = await agent.process_task(incomplete_task)
        
        if result.success:
            print("❌ Incomplete task should have failed")
            return False
        
        print("✅ Incomplete task properly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Invalid task handling test failed: {e}")
        return False


async def main():
    """Run all KnowledgeAgent tests."""
    print("Running KnowledgeAgent Tests")
    print("=" * 50)
    
    tests = [
        test_knowledge_agent_initialization,
        test_search_task_processing,
        test_add_knowledge_item_task,
        test_context_retrieval_task,
        test_agent_health_check,
        test_invalid_task_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All KnowledgeAgent tests passed!")
        return True
    else:
        print(f"❌ {total - passed} tests failed")
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)