import pytest
import asyncio
import asyncpg
import bcrypt
from services.like_service import LikeService
from unittest.mock import patch

@pytest.mark.asyncio
async def test_like_service_initialization(db_pool):
    """Test LikeService initialization."""
    # Create LikeService with db_pool
    like_service = LikeService(db_pool)
    
    # Check that the service was created correctly
    assert like_service.pool == db_pool

@pytest.mark.asyncio
async def test_toggle_like(db_pool):
    """Test toggling like status."""
    # Skip if database is not available
    if db_pool is None:
        pytest.skip("Database not available")
        
    # Create a test user
    test_username = "test_like_user"
    test_password = "test_password"
    
    # Hash the password
    hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
    
    # Add test user to database
    try:
        async with db_pool.acquire() as conn:
            try:
                await conn.execute(
                    'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                    test_username, hashed_password
                )
            except asyncpg.UniqueViolationError:
                pass  # User already exists
    except Exception:
        pass  # Database error
    
    # Create a test meme
    test_meme_id = 777777
    test_meme_url = "https://example.com/test_like.jpg"
    
    # Add test meme to database
    try:
        async with db_pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO memes (id, url, title, media_type, width, height, nsfw, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ''', test_meme_id, test_meme_url, "Test Like Meme", "image", 800, 600, False, 
                    "2023-01-01 00:00:00", "2023-01-01 00:00:00")
            except asyncpg.UniqueViolationError:
                pass  # Meme already exists
    except Exception:
        pass  # Database error
    
    # Create LikeService
    like_service = LikeService(db_pool)
    
    # Mock the session
    with patch('services.like_service.session', {'username': test_username}):
        # Test toggling like
        result = await like_service.toggle_like(str(test_meme_id))
        
        # Check that we got a dict result
        assert isinstance(result, dict)
        assert 'status' in result

@pytest.mark.asyncio
async def test_get_user_liked_memes(db_pool):
    """Test getting user liked memes."""
    # Skip if database is not available
    if db_pool is None:
        pytest.skip("Database not available")
        
    # Create a test user
    test_username = "test_liked_memes_user"
    test_password = "test_password"
    
    # Hash the password
    hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
    
    # Add test user to database
    try:
        async with db_pool.acquire() as conn:
            try:
                await conn.execute(
                    'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                    test_username, hashed_password
                )
            except asyncpg.UniqueViolationError:
                pass  # User already exists
    except Exception:
        pass  # Database error
    
    # Create LikeService
    like_service = LikeService(db_pool)
    
    # Mock the session
    with patch('services.like_service.session', {'username': test_username}):
        # Test getting user liked memes
        result = await like_service.get_user_liked_memes()
        
        # Check that we got a dict result
        assert isinstance(result, dict)
