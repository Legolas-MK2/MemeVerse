import pytest
import asyncio
import asyncpg
from services.database_service import create_database_pool, DB_CONFIG

@pytest.mark.asyncio
async def test_database_connection():
    """Test that we can create a database connection pool."""
    try:
        pool = await create_database_pool()
        assert pool is not None
        
        # Test that we can acquire a connection
        async with pool.acquire() as conn:
            assert conn is not None
            
        await pool.close()
    except Exception as e:
        pytest.fail(f"Database connection failed: {str(e)}")

@pytest.mark.asyncio
async def test_database_config():
    """Test that database configuration is properly loaded."""
    assert 'user' in DB_CONFIG
    assert 'password' in DB_CONFIG
    assert 'database' in DB_CONFIG
    assert 'host' in DB_CONFIG
    assert 'port' in DB_CONFIG
    
    # Check that required values are not None
    assert DB_CONFIG['user'] is not None
    assert DB_CONFIG['password'] is not None
    assert DB_CONFIG['database'] is not None
    assert DB_CONFIG['host'] is not None
    assert DB_CONFIG['port'] is not None
