import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration from environment variables (same as conftest.py)
DB_CONFIG = {
    'user': os.getenv('POSTGREST_USERNAME', 'discord_meme'),
    'password': os.getenv('POSTGREST_PASSWORD'),
    'database': 'memedb',
    'host': '192.168.178.23',
    'port': 5433
}

async def test_db_connection():
    print("Testing database connection...")
    print(f"DB_CONFIG: {DB_CONFIG}")
    
    # Check if credentials are available
    if not DB_CONFIG['user'] or not DB_CONFIG['password']:
        print("Warning: Database credentials not available")
        return
        
    try:
        print("Attempting to create database pool...")
        pool = await asyncpg.create_pool(**DB_CONFIG)
        print("Successfully created database pool")
        
        # Test acquiring a connection
        print("Attempting to acquire connection...")
        async with pool.acquire() as conn:
            print("Successfully acquired connection")
            result = await conn.fetchval("SELECT 1")
            print(f"Query result: {result}")
            
        await pool.close()
        print("Successfully closed pool")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db_connection())
