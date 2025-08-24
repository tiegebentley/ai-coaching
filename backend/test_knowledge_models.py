#!/usr/bin/env python3
"""Test script for knowledge base models."""

import sys
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add src directory to Python path
backend_dir = Path(__file__).parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from ai_coaching.models.knowledge import (
    KnowledgeItem,
    ContentCategory,
    ContentSource,
    ContentFormat,
    KnowledgeItemMetadata,
    KnowledgeSearchQuery,
    KnowledgeSearchResult,
    KnowledgeSearchResponse,
    KnowledgeStats
)


def test_knowledge_item_creation():
    """Test creating a knowledge item with validation."""
    print("Testing KnowledgeItem creation and validation...")
    
    try:
        # Test valid knowledge item
        item = KnowledgeItem(
            title="Effective Communication with Parents",
            content="Best practices for communicating with parents about their children's progress...",
            category=ContentCategory.PARENT_COMMUNICATION,
            source_type=ContentSource.MANUAL_ENTRY,
            tags=["communication", "parents", "feedback"],
            keywords=["parent", "communication", "feedback", "progress"],
            relevance_score=0.9,
            quality_score=0.8,
            confidence_score=0.85
        )
        
        print("✅ Valid knowledge item created successfully")
        print(f"   - Title: {item.title}")
        print(f"   - Category: {item.category}")
        print(f"   - Composite Score: {item.calculate_composite_score()}")
        
        # Test embedding validation
        item.embedding_vector = [0.1] * 1536  # Valid embedding
        print("✅ Valid embedding vector accepted")
        
        # Test invalid embedding
        try:
            item.embedding_vector = [0.1] * 512  # Invalid dimensions
            print("❌ Should have failed with invalid embedding dimensions")
            return False
        except ValueError as e:
            print(f"✅ Correctly rejected invalid embedding: {e}")
        
        # Reset to valid embedding
        item.embedding_vector = [0.1] * 1536
        
        # Test score validation
        try:
            invalid_item = KnowledgeItem(
                title="Test Item",
                content="Test content",
                category=ContentCategory.FAQ,
                source_type=ContentSource.MANUAL_ENTRY,
                quality_score=0.9,
                confidence_score=0.5  # Quality > confidence should fail
            )
            print("❌ Should have failed with quality > confidence")
            return False
        except ValueError as e:
            print(f"✅ Correctly rejected invalid score relationship: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Knowledge item test failed: {e}")
        return False


def test_search_query_validation():
    """Test search query model validation."""
    print("\nTesting KnowledgeSearchQuery validation...")
    
    try:
        query = KnowledgeSearchQuery(
            query_text="How to handle difficult parents?",
            categories=[ContentCategory.PARENT_COMMUNICATION, ContentCategory.FAQ],
            tags=["communication", "conflict"],
            min_relevance_score=0.5,
            max_results=20
        )
        
        print("✅ Valid search query created successfully")
        print(f"   - Query: {query.query_text}")
        print(f"   - Categories: {[c.value for c in query.categories]}")
        print(f"   - Max results: {query.max_results}")
        
        return True
        
    except Exception as e:
        print(f"❌ Search query test failed: {e}")
        return False


def test_knowledge_stats():
    """Test knowledge stats model."""
    print("\nTesting KnowledgeStats model...")
    
    try:
        stats = KnowledgeStats(
            total_items=150,
            items_by_category={
                "parent_communication": 25,
                "coaching_best_practices": 40,
                "safety_protocols": 15,
                "administrative": 30,
                "other": 40
            },
            items_by_source={
                "manual_entry": 80,
                "documentation": 35,
                "email_thread": 20,
                "website": 15
            },
            avg_relevance_score=0.75,
            avg_quality_score=0.68,
            total_access_count=1250,
            outdated_items_count=12,
            items_without_embeddings=8,
            last_updated=datetime.utcnow()
        )
        
        print("✅ Knowledge stats created successfully")
        print(f"   - Total items: {stats.total_items}")
        print(f"   - Average relevance: {stats.avg_relevance_score}")
        print(f"   - Outdated items: {stats.outdated_items_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Knowledge stats test failed: {e}")
        return False


def test_model_serialization():
    """Test JSON serialization/deserialization."""
    print("\nTesting model serialization...")
    
    try:
        # Create a knowledge item
        original = KnowledgeItem(
            id=uuid4(),
            title="Test Serialization",
            content="Test content for serialization validation",
            category=ContentCategory.TROUBLESHOOTING,
            source_type=ContentSource.USER_GENERATED,
            embedding_vector=[0.1] * 1536,
            created_at=datetime.utcnow()
        )
        
        # Serialize to JSON
        json_data = original.json()
        print("✅ Model serialized to JSON successfully")
        
        # Deserialize from JSON
        restored = KnowledgeItem.parse_raw(json_data)
        print("✅ Model deserialized from JSON successfully")
        
        # Verify data integrity
        if original.id == restored.id and original.title == restored.title:
            print("✅ Data integrity maintained through serialization")
            return True
        else:
            print("❌ Data integrity lost during serialization")
            return False
        
    except Exception as e:
        print(f"❌ Serialization test failed: {e}")
        return False


def main():
    """Run all knowledge model tests."""
    print("Running Knowledge Base Model Tests")
    print("=" * 50)
    
    tests = [
        test_knowledge_item_creation,
        test_search_query_validation,
        test_knowledge_stats,
        test_model_serialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All knowledge model tests passed!")
        return True
    else:
        print(f"❌ {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)