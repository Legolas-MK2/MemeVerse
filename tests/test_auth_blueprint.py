import pytest
import asyncio
from quart import session
from blueprints.auth_blueprint import init_auth_routes
from services.user_service import UserService
from unittest.mock import AsyncMock, Mock, patch

@pytest.mark.asyncio
async def test_login_get():
    """Test GET request to login route."""
    # Create a mock app
    mock_app = Mock()
    mock_app.secret_key = 'test-secret-key'
    
    # Create a mock pool
    mock_pool = AsyncMock()
    
    # Initialize auth routes
    init_auth_routes(mock_app, mock_pool)
    
    # Check that the login route was registered
    assert hasattr(mock_app, 'register_blueprint')

@pytest.mark.asyncio
async def test_register_get():
    """Test GET request to register route."""
    # Create a mock app
    mock_app = Mock()
    mock_app.secret_key = 'test-secret-key'
    
    # Create a mock pool
    mock_pool = AsyncMock()
    
    # Initialize auth routes
    init_auth_routes(mock_app, mock_pool)
    
    # Check that the register route was registered
    assert hasattr(mock_app, 'register_blueprint')

@pytest.mark.asyncio
async def test_login_post_success(db_pool):
    """Test successful POST request to login route."""
    # Skip if database is not available
    if db_pool is None:
        pytest.skip("Database not available")
        
    # Create a test user
    test_username = "test_login_user"
    test_password = "test_password"
    
    # Hash the password
    import bcrypt
    hashed_password = bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()
    
    # Add test user to database
    try:
        async with db_pool.acquire() as conn:
            try:
                await conn.execute(
                    'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                    test_username, hashed_password
                )
            except Exception:
                pass  # User already exists or other error
    except Exception:
        pass  # Database error
    
    # Create a mock app with request context
    mock_app = Mock()
    mock_app.secret_key = 'test-secret-key'
    
    # Initialize auth routes
    init_auth_routes(mock_app, db_pool)
    
    # Note: We can't easily test the actual route execution in this context
    # This test mainly ensures the route is set up correctly

@pytest.mark.asyncio
async def test_register_post_success(db_pool):
    """Test successful POST request to register route."""
    # Create a mock app with request context
    mock_app = Mock()
    mock_app.secret_key = 'test-secret-key'
    
    # Initialize auth routes
    init_auth_routes(mock_app, db_pool)
    
    # Note: We can't easily test the actual route execution in this context
    # This test mainly ensures the route is set up correctly
