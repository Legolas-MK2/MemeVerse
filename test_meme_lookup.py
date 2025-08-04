import asyncio
import asyncpg
from private_conf import POSTGREST_USERNAME, POSTGREST_PASSWORD

async def lookup_meme(meme_id):
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
            
        # Look up the specific meme
        meme_data = await conn.fetchrow("SELECT * FROM memes WHERE id = $1", meme_id)
        
        if meme_data:
            print(f"Found meme with ID {meme_id}:")
            print(f"Data: {dict(meme_data)}")
        else:
            print(f"No meme found with ID {meme_id}")
            
    except asyncpg.InvalidCatalogNameError:
        print("Error: The database 'memedb' does not exist.")
        print("Please verify the database name or create the database.")
    except asyncpg.InsufficientPrivilegeError:
        print("Error: Permission denied for table memes.")
        print("Please verify that the user has SELECT permissions on the table.")
    except Exception as e:
        print(f"Error looking up meme: {str(e)}")
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    # Look up meme 98722
    asyncio.run(lookup_meme(98722))
