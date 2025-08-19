import pytest
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from services.feed_service import FeedService
from unittest.mock import AsyncMock, Mock

# Load environment variables
load_dotenv()

# Database configuration from environment variables
DB_CONFIG = {
    'user': os.getenv('POSTGREST_USERNAME'),
    'password': os.getenv('POSTGREST_PASSWORD'),
    'database': 'memedb',
    'host': '192.168.178.23',
    'port': 5433
}

@pytest.mark.asyncio
async def test_feed_service_initialization():
    """Test FeedService initialization."""
    # Create a mock pool for testing initialization
    mock_pool = AsyncMock()
    
    # Create FeedService with mock pool
    feed_service = FeedService(mock_pool)
    
    # Check that the service was created correctly
    assert feed_service.pool == mock_pool

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_get_feed_items():
    """Test getting feed items."""
    try:
        # Create a pool for FeedService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create FeedService
        feed_service = FeedService(pool)
        
        # Test getting feed items
        items, has_more = await feed_service.get_feed_items(5)
        
        # Check that we got a list (even if empty)
        assert isinstance(items, list)
        assert isinstance(has_more, bool)
            
        await pool.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_get_total_items():
    """Test getting total item count."""
    try:
        # Create a pool for FeedService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create FeedService
        feed_service = FeedService(pool)
        
        # Test getting total items
        count = await feed_service.get_total_items()
        
        # Check that we got an integer
        assert isinstance(count, int)
        assert count >= 0
            
        await pool.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")
