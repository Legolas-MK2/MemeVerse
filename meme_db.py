import sqlite3
import random
import os

def save_random_memes():
    # Connect to source database
    source_conn = sqlite3.connect('discord_media.db')
    source_cursor = source_conn.cursor()
    
    # Get total row count
    source_cursor.execute('SELECT COUNT(*) FROM media')
    total_rows = source_cursor.fetchone()[0]
    
    # Generate 100 random row IDs
    random_ids = random.sample(range(1, total_rows + 1), min(100, total_rows))
    
    # Create new database
    dest_conn = sqlite3.connect('random_memes.db')
    dest_cursor = dest_conn.cursor()
    
    # Create table structure (assuming same as source)
    source_cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='media'")
    create_table_sql = source_cursor.fetchone()[0]
    dest_cursor.execute(create_table_sql)
    
    # Copy random rows
    for row_id in random_ids:
        source_cursor.execute(f'SELECT * FROM media WHERE rowid = {row_id}')
        row = source_cursor.fetchone()
        dest_cursor.execute('INSERT INTO media VALUES (?, ?, ?, ?, ?, ?)', row)
    
    # Commit and close connections
    dest_conn.commit()
    dest_conn.close()
    source_conn.close()

if __name__ == '__main__':
    if os.path.exists("random_memes.db"):
        os.remove("random_memes.db")
    save_random_memes()
