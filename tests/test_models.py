import pytest
import asyncio
import asyncpg
from models.feed_item import FeedItem

@pytest.mark.asyncio
async def test_feed_item_creation():
    """Test creation of FeedItem model."""
    # Test FeedItem creation
    feed_item = FeedItem(
        id="12345",
        liked=True,
        media_type="image"
    )
    
    # Check that the FeedItem was created correctly
    assert feed_item.id == "12345"
    assert feed_item.liked == True
    assert feed_item.media_type == "image"

@pytest.mark.asyncio
async def test_feed_item_attributes():
    """Test FeedItem attributes."""
    # Test FeedItem with different values
    feed_item = FeedItem(
        id="67890",
        liked=False,
        media_type="video"
    )
    
    # Check that the FeedItem was created correctly
    assert feed_item.id == "67890"
    assert feed_item.liked == False
    assert feed_item.media_type == "video"
