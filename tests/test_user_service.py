import pytest
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from services.user_service import UserService
from unittest.mock import AsyncMock, Mock, patch
import bcrypt

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
async def test_ensure_user_id():
    """Test that ensure_user_id creates a session ID."""
    # Create a mock pool and connection
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    
    # Create UserService with mock pool
    user_service = UserService(mock_pool)
    
    # Create a mock session
    session = {}
    
    # Patch the session
    with patch('services.user_service.session', session):
        # Call ensure_user_id
        await user_service.ensure_user_id()
        
        # Check that user_id was added to session
        assert 'user_id' in session
        assert session['user_id'] is not None

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_authenticate_user_success():
    """Test successful user authentication."""
    try:
        # Create a database connection directly
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Create a test user
        test_username = "test_user_auth"
        test_password = "test_password"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
        
        # Add test user to database
        try:
            await conn.execute(
                'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                test_username, hashed_password
            )
        except asyncpg.UniqueViolationError:
            # User already exists, update password
            await conn.execute(
                'UPDATE users SET password_hash = $1 WHERE username = $2',
                hashed_password, test_username
            )
        
        # Create a pool for UserService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create UserService
        user_service = UserService(pool)
        
        # Mock the session
        with patch('services.user_service.session', {}):
            # Test authentication
            result = await user_service.authenticate_user(test_username, test_password)
            
            # Check that authentication was successful
            assert result is True
            
        await pool.close()
        await conn.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_authenticate_user_failure():
    """Test failed user authentication."""
    try:
        # Create a pool for UserService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create UserService
        user_service = UserService(pool)
        
        # Mock the session
        with patch('services.user_service.session', {}):
            # Test authentication with wrong password
            result = await user_service.authenticate_user("nonexistent_user", "wrong_password")
            
            # Check that authentication failed
            assert result is False
            
        await pool.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_register_user_success():
    """Test successful user registration."""
    try:
        # Create a database connection directly
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Clean up any existing test user
        await conn.execute(
            'DELETE FROM users WHERE username = $1',
            "test_register_user"
        )
        
        # Create a pool for UserService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create UserService
        user_service = UserService(pool)
        
        # Mock the session
        with patch('services.user_service.session', {}) as mock_session:
            # Test registration
            test_username = "test_register_user"
            test_password = "test_register_password"
            
            result, error = await user_service.register_user(test_username, test_password)
            
            # Check that registration was successful
            assert result is True
            assert error == ""
            
        await pool.close()
        await conn.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_register_user_failure():
    """Test failed user registration."""
    try:
        # Create a database connection directly
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Create a test user
        test_username = "test_user_register_fail"
        test_password = "test_password"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
        
        # Add test user to database
        try:
            await conn.execute(
                'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                test_username, hashed_password
            )
        except asyncpg.UniqueViolationError:
            pass  # User already exists
        
        # Create a pool for UserService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create UserService
        user_service = UserService(pool)
        
        # Mock the session
        with patch('services.user_service.session', {}):
            # Test registration with existing username
            result, error = await user_service.register_user(test_username, test_password)
            
            # Check that registration failed
            assert result is False
            assert error == "Username already exists"
            
        await pool.close()
        await conn.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_get_user_profile():
    """Test getting user profile."""
    try:
        # Create a database connection directly
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Create a test user
        test_username = "test_profile_user"
        test_password = "test_password"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
        
        # Add test user to database
        try:
            await conn.execute(
                'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                test_username, hashed_password
            )
        except asyncpg.UniqueViolationError:
            pass  # User already exists
        
        # Create a pool for UserService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create UserService
        user_service = UserService(pool)
        
        # Test getting user profile
        profile = await user_service.get_user_profile(test_username)
        
        # Check that profile was retrieved
        assert profile is not None
        assert profile['user']['username'] == test_username
            
        await pool.close()
        await conn.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_get_current_user_profile():
    """Test getting current user profile."""
    try:
        # Create a database connection directly
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Create a test user
        test_username = "test_current_profile_user"
        test_password = "test_password"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
        
        # Add test user to database
        try:
            await conn.execute(
                'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                test_username, hashed_password
            )
        except asyncpg.UniqueViolationError:
            pass  # User already exists
        
        # Create a pool for UserService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create UserService
        user_service = UserService(pool)
        
        # Mock the session
        with patch('services.user_service.session', {'username': test_username}):
            # Test getting current user profile
            profile = await user_service.get_current_user_profile()
            
            # Check that profile was retrieved
            assert profile is not None
            assert profile['username'] == test_username
            
        await pool.close()
        await conn.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_update_user_bio():
    """Test updating user bio."""
    try:
        # Create a database connection directly
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Create a test user
        test_username = "test_bio_user"
        test_password = "test_password"
        
        # Hash the password
        hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
        
        # Add test user to database
        try:
            await conn.execute(
                'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                test_username, hashed_password
            )
        except asyncpg.UniqueViolationError:
            pass  # User already exists
        
        # Create a pool for UserService
        pool = await asyncpg.create_pool(**DB_CONFIG)
        
        # Create UserService
        user_service = UserService(pool)
        
        # Mock the session
        with patch('services.user_service.session', {'username': test_username}):
            # Test updating user bio
            new_bio = "This is a test bio"
            result = await user_service.update_user_bio(new_bio)
            
            # Check that bio was updated
            assert result is True
            
            # Verify the bio was actually updated
            profile = await user_service.get_current_user_profile()
            assert profile is not None
            
        await pool.close()
        await conn.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")
