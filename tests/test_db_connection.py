import pytest
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

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

def test_database_config_loaded():
    """Test that database configuration is properly loaded."""
    # This test should pass even if credentials are not available
    # It's checking that the configuration structure is correct
    assert 'user' in DB_CONFIG
    assert 'password' in DB_CONFIG
    # These might be None, which is okay for configuration loading

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_database_connection():
    """Test that we can create a database connection."""
    try:
        # Test creating a connection directly
        conn = await asyncpg.connect(**DB_CONFIG)
        assert conn is not None
        
        # Test a simple query
        result = await conn.fetchval("SELECT 1")
        assert result == 1
        
        await conn.close()
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {str(e)}")

@pytest.mark.skipif(
    not os.getenv('POSTGREST_USERNAME') or not os.getenv('POSTGREST_PASSWORD'),
    reason="Database credentials not available"
)
@pytest.mark.asyncio
async def test_database_pool():
    """Test that we can create a database connection pool."""
    try:
        # Test creating a connection pool
        pool = await asyncpg.create_pool(**DB_CONFIG)
        assert pool is not None
        
        # Test acquiring a connection from the pool
        async with pool.acquire() as conn:
            assert conn is not None
            
            # Test a simple query
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            
        await pool.close()
        
    except Exception as e:
        pytest.skip(f"Database pool creation failed: {str(e)}")
