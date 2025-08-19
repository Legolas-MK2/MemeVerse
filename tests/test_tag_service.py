import pytest
import asyncio
import asyncpg
from services.tag_service import TagService
from unittest.mock import AsyncMock, Mock, patch

@pytest.mark.asyncio
async def test_tag_service_initialization(db_pool):
    """Test TagService initialization."""
    # Create TagService with db_pool
    tag_service = TagService(db_pool)
    
    # Check that the service was created correctly
    assert tag_service.pool == db_pool

@pytest.mark.asyncio
async def test_get_user_tags(db_pool):
    """Test getting user tags."""
    # Skip if database is not available
    if db_pool is None:
        pytest.skip("Database not available")
        
    # Create TagService
    tag_service = TagService(db_pool)
    
    # Mock the session
    with patch('services.tag_service.session', {'username': 'test_user'}):
        # Test getting user tags
        result = await tag_service.get_user_tags('test_user')
        
        # Check that we got a dict
        assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_create_tag(db_pool):
    """Test creating a tag."""
    # Skip if database is not available
    if db_pool is None:
        pytest.skip("Database not available")
        
    # Create TagService
    tag_service = TagService(db_pool)
    
    # Mock the session
    with patch('services.tag_service.session', {'username': 'test_user'}):
        # Test creating a tag
        result = await tag_service.create_tag("test_tag")
        
        # Check that we got a dict
        assert isinstance(result, dict)
