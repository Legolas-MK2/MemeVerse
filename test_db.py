import asyncio
import asyncpg
from private_conf import POSTGREST_USERNAME, POSTGREST_PASSWORD

async def count_rows():
    try:
        # Connect to the database
        conn = await asyncpg.connect(
            user=POSTGREST_USERNAME,
            password=POSTGREST_PASSWORD,
            database='memedb',
            host='192.168.178.23',
            port=5433
        )
        
        # Check if table exists
        table_exists = await conn.fetchval('''
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'memes'
            )
        ''')
        
        if not table_exists:
            print("Error: The table 'memes' does not exist.")
            return
            
        # Execute the count query
        count = await conn.fetchval("SELECT COUNT(*) FROM memes")
        print(f"Number of rows in memes table: {count}")
        
    except asyncpg.InvalidCatalogNameError:
        print("Error: The database 'memedb' does not exist.")
        print("Please verify the database name or create the database.")
    except asyncpg.InsufficientPrivilegeError:
        print("Error: Permission denied for table memes.")
        print("Please verify that the user has SELECT permissions on the table.")
    except Exception as e:
        print(f"Error counting rows: {str(e)}")
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    pass