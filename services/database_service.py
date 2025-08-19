import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()


# Database configuration
DB_CONFIG = {
    'user': os.getenv('POSTGREST_USERNAME', 'discord_meme'),
    'password': os.getenv('POSTGREST_PASSWORD'),
    'database': 'memedb',
    'host': '192.168.178.23',
    'port': 5433
}


async def create_database_pool():
    """
    Create and return a database connection pool
    """
    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        print("Successfully connected to database")
        return pool
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        raise
