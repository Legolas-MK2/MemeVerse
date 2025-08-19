import pytest
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from unittest.mock import AsyncMock, Mock
import sys
import pathlib

# Add the project root to the Python path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv()

# Database configuration from environment variables
DB_CONFIG = {
    'user': os.getenv('POSTGREST_USERNAME', 'discord_meme'),
    'password': os.getenv('POSTGREST_PASSWORD'),
    'database': 'memedb',
    'host': '192.168.178.23',
    'port': 5433
}

# Test database configuration (same as main but with test-specific handling)
TEST_DB_CONFIG = {
    'user': os.getenv('POSTGREST_USERNAME', 'discord_meme'),
    'password': os.getenv('POSTGREST_PASSWORD'),
    'database': 'memedb',
    'host': '192.168.178.23',
    'port': 5433
}

@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default event loop policy."""
    return asyncio.get_event_loop_policy()

@pytest.fixture(scope="session")
def db_pool():
    """Create a database connection pool for testing."""
    # Always provide a mock database pool for testing
    mock_pool = AsyncMock()
    
    # Create a mock connection that supports async context manager protocol
    mock_conn = AsyncMock()
    
    # Set up default return values
    mock_conn.fetch.return_value = []
    mock_conn.fetchval.return_value = None
    mock_conn.execute.return_value = "OK"
    
    # Special handling for user registration/authentication
    import bcrypt
    test_users = {}
    
    async def mock_fetchrow(query, *args):
        if 'users WHERE username' in query:
            username = args[0]
            if username in test_users:
                return test_users[username]
            else:
                return None
        return None
    
    async def mock_execute(query, *args):
        if 'INSERT INTO users' in query:
            username, hashed_password = args
            # Store the test user
            test_users[username] = {
                'username': username,
                'password_hash': hashed_password,
                'id': 1
            }
            return "INSERT OK"
        return "OK"
    
    # Apply the special handlers
    mock_conn.fetchrow.side_effect = mock_fetchrow
    mock_conn.execute.side_effect = mock_execute
    
    # Create an async context manager for acquire
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_conn
        
        async def __aexit__(self, *args):
            pass
    
    # Set up the acquire method to return an async context manager directly
    def mock_acquire():
        return AsyncContextManager()
    
    mock_pool.acquire = mock_acquire
    
    return mock_pool
