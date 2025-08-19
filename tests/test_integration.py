import pytest
import asyncio
import asyncpg
import bcrypt
from services.user_service import UserService
from services.like_service import LikeService
from services.feed_service import FeedService
from services.media_service import MediaService
from unittest.mock import patch

@pytest.mark.asyncio
async def test_user_registration_and_authentication(db_pool):
    """Test complete user registration and authentication flow."""
    # Skip if database is not available
    if db_pool is None:
        pytest.skip("Database not available")
        
    # Create services
    user_service = UserService(db_pool)
    
    # Mock the session
    with patch('services.user_service.session', {}) as mock_session:
        # Test registration
        test_username = "integration_test_user"
        test_password = "integration_test_password"
        
        result, error = await user_service.register_user(test_username, test_password)
        
        # Check that registration was successful
        assert result is True
        assert error == ""
        
        # Test authentication
        auth_result = await user_service.authenticate_user(test_username, test_password)
        
        # Check that authentication was successful
        assert auth_result is True

@pytest.mark.asyncio
async def test_feed_and_like_integration(db_pool):
    """Test feed generation and like functionality integration."""
    # Skip if database is not available
    if db_pool is None:
        pytest.skip("Database not available")
        
    # Create services
    feed_service = FeedService(db_pool)
    like_service = LikeService(db_pool)
    
    # Create a test user
    test_username = "feed_like_test_user"
    test_password = "feed_like_test_password"
    
    # Hash the password
    hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
    
    # Add test user to database
    async with db_pool.acquire() as conn:
        try:
            await conn.execute(
                'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                test_username, hashed_password
            )
        except asyncpg.UniqueViolationError:
            pass  # User already exists
    
    # Mock the session
    with patch('services.like_service.session', {'username': test_username}):
        # Test getting feed items
        items, has_more = await feed_service.get_feed_items(5)
        
        # Check that we got a list
        assert isinstance(items, list)
        
        # Test toggling like if we have items
        if items:
            # Test toggling like on the first item
            result = await like_service.toggle_like(items[0]['id'])
            
            # Check that we got a result
            assert isinstance(result, dict)
            assert 'status' in result

@pytest.mark.asyncio
async def test_media_serving(db_pool):
    """Test media serving functionality."""
    # Create service
    media_service = MediaService(db_pool)
    
    # Test serving media for a non-existent meme
    result = await media_service.serve_media(999999)
    
    # Check that we got None for non-existent meme
    assert result is None

@pytest.mark.asyncio
async def test_user_profile_and_feed(db_pool):
    """Test user profile and feed functionality."""
    # Skip if database is not available
    if db_pool is None:
        pytest.skip("Database not available")
        
    # Create services
    user_service = UserService(db_pool)
    
    # Create a test user
    test_username = "profile_feed_test_user"
    test_password = "profile_feed_test_password"
    
    # Hash the password
    hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
    
    # Add test user to database
    async with db_pool.acquire() as conn:
        try:
            await conn.execute(
                'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                test_username, hashed_password
            )
        except asyncpg.UniqueViolationError:
            pass  # User already exists
    
    # Mock the session
    with patch('services.user_service.session', {'username': test_username}):
        # Test getting current user profile
        profile = await user_service.get_current_user_profile()
        
        # Check that profile was retrieved
        assert profile is not None
        assert profile['username'] == test_username
