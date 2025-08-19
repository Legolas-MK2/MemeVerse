import pytest
import asyncio
import asyncpg
from services.media_service import MediaService
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_media_service_initialization(db_pool):
    """Test MediaService initialization."""
    # Create MediaService with db_pool
    media_service = MediaService(db_pool)
    
    # Check that the service was created correctly
    assert media_service.pool == db_pool

@pytest.mark.asyncio
async def test_serve_media(db_pool):
    """Test serving media."""
    # Create MediaService
    media_service = MediaService(db_pool)
    
    # Test serving media for a non-existent meme
    result = await media_service.serve_media(999999)
    
    # Check that we got None for non-existent meme
    assert result is None
