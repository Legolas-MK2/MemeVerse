from quart import Quart, render_template, jsonify, request, url_for, session, Response, redirect
import asyncpg
from dataclasses import dataclass
from typing import List
import random
from datetime import datetime
import uuid
import logging
import json
from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
from private_conf import POSTGREST_PASSWORD, POSTGREST_USERNAME
import bcrypt

# Set up logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'user': 'discord_meme',
    'password': POSTGREST_PASSWORD,
    'database': 'memedb',
    'host': '192.168.178.23',
    'port': 5433
}

@dataclass
class FeedItem:
    id: str
    type: str
    username: str
    description: str
    likes: int
    comments: int
    shares: int
    created_at: datetime
    media_data: bytes
    media_type: str
    url: str

class FeedManager:
    def __init__(self, pool):
        self.items: List[FeedItem] = []
        self.liked_items = set()
        self.items_per_page = 5
        self.pool = pool

    async def _get_media_items(self, page: int) -> List[dict]:
        try:
            async with self.pool.acquire() as conn:
                # Calculate offset
                offset = (page - 1) * self.items_per_page

                query = '''
                    SELECT id, url, file_data, timestamp, author_id, media_type 
                    FROM memes 
                    WHERE file_data IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT $1 OFFSET $2
                '''
                rows = await conn.fetch(query, self.items_per_page, offset)
                
                media_items = []
                for row in rows:
                    try:
                        media_items.append({
                            'meme_id': row['id'],
                            'url': row['url'],
                            'media_data': row['file_data'],
                            'timestamp': row['timestamp'],
                            'author_id': row['author_id'],
                            'media_type': row['media_type']
                        })
                    except Exception as e:
                        logger.error(f"Error processing row: {row}, Error: {str(e)}")
                
                logger.info(f"Retrieved {len(media_items)} media items for page {page}")
                return media_items
        except Exception as e:
            logger.error(f"Database error in _get_media_items: {str(e)}")
            return []

    async def get_total_items(self) -> int:
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval('SELECT COUNT(*) FROM memes WHERE file_data IS NOT NULL')
                logger.info(f"Total items in database: {count}")
                return count
        except Exception as e:
            logger.error(f"Error getting total items: {str(e)}")
            return 0

    async def generate_feed_data(self, page: int) -> List[FeedItem]:
        try:
            media_items = await self._get_media_items(page)
            new_items = []
            
            for media in media_items:
                try:
                    new_items.append(FeedItem(
                        id=str(media['meme_id']),
                        type=media['media_type'],
                        username=f'@{media["author_id"]}',
                        description=f'Check out this {media["media_type"]}!',
                        likes=random.randint(0, 100000),
                        comments=random.randint(0, 1000),
                        shares=random.randint(0, 500),
                        created_at=media['timestamp'],
                        media_data=media['media_data'],
                        media_type=media['media_type'],
                        url=media['url']
                    ))
                except Exception as e:
                    logger.error(f"Error creating FeedItem: {str(e)}, Media: {media}")
            
            logger.info(f"Generated feed data for page {page} with {len(new_items)} items")
            return new_items
        except Exception as e:
            logger.error(f"Error in generate_feed_data: {str(e)}")
            return []

    async def get_feed_items(self, page: int) -> tuple[List[FeedItem], bool]:
        total_items = await self.get_total_items()
        new_items = await self.generate_feed_data(page)
        has_more = (page * self.items_per_page) < total_items
        return new_items, has_more

async def create_app():
    app = Quart(__name__)
    app.secret_key = 'your-secret-key-here'

    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        logger.info("Successfully connected to database")
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

    app.db_pool = pool
    
    # Initialize database with users table if it doesn't exist
    async def init_db():
        try:
            async with app.db_pool.acquire() as conn:
                # Try to create table if it doesn't exist
                try:
                    await conn.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username TEXT UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT NOW(),
                            bio TEXT,
                            avatar_url TEXT,
                            liked_memes JSONB DEFAULT '[]'::JSONB
                        )
                    ''')
                    
                    # Add missing columns if they don't exist
                    await conn.execute('''
                        DO $$
                        BEGIN
                            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name = 'users' 
                                       AND column_name = 'bio') THEN
                                ALTER TABLE users ADD COLUMN bio TEXT;
                            END IF;
                            
                            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name = 'users' 
                                       AND column_name = 'avatar_url') THEN
                                ALTER TABLE users ADD COLUMN avatar_url TEXT;
                            END IF;
                            
                            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                       WHERE table_name = 'users' 
                                       AND column_name = 'liked_memes') THEN
                                ALTER TABLE users ADD COLUMN liked_memes JSONB DEFAULT '[]'::JSONB;
                            END IF;
                        END $$;
                    ''')
                    logger.info("Successfully initialized database tables")
                except Exception as e:
                    logger.warning(f"Could not initialize database tables: {str(e)}")
                    logger.warning("Application will continue, but some features may not work properly")
        except Exception as e:
            logger.error(f"Error connecting to database during initialization: {str(e)}")
            raise
    
    await init_db()
    feed_manager = FeedManager(pool)

    @app.before_request
    async def ensure_user_id():
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        
        # Check if user is logged in
        if request.endpoint not in ['login', 'static', 'register'] and 'username' not in session:
            return redirect(url_for('login'))

    @app.template_filter('format_number')
    def format_number(value):
        if value >= 1000000:
            return f'{value/1000000:.1f}M'
        elif value >= 1000:
            return f'{value/1000:.1f}K'
        return str(value)

    @app.route('/login', methods=['GET', 'POST'])
    async def login():
        if request.method == 'POST':
            form = await request.form
            username = form.get('username')
            password = form.get('password')
            
            async with app.db_pool.acquire() as conn:
                user = await conn.fetchrow('SELECT * FROM users WHERE username = $1', username)
                
                if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                    session['username'] = username
                    return redirect(url_for('index'))
                return await render_template('login.html', error='Invalid username or password')
        return await render_template('login.html')

    @app.route('/logout')
    async def logout():
        session.pop('username', None)
        return redirect(url_for('login'))

    @app.route('/register', methods=['GET', 'POST'])
    async def register():
        if request.method == 'POST':
            form = await request.form
            username = form.get('username')
            password = form.get('password')
            
            if len(password) < 8:
                return await render_template('register.html', error='Password must be at least 8 characters')
            
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            try:
                async with app.db_pool.acquire() as conn:
                    await conn.execute('''
                        INSERT INTO users (username, password_hash)
                        VALUES ($1, $2)
                    ''', username, password_hash)
                return redirect(url_for('login'))
            except asyncpg.UniqueViolationError:
                return await render_template('register.html', error='Username already exists')
        return await render_template('register.html')

    @app.route('/')
    async def index():
        try:
            initial_items, has_more = await feed_manager.get_feed_items(1)
            logger.debug(f"Rendering template with {len(initial_items)} items")
            return await render_template('index.html', feed_items=initial_items, has_more=has_more)
        except Exception as e:
            logger.error(f"Error in index route: {str(e)}")
            return f"An error occurred: {str(e)}", 500

    @app.route('/media/<int:media_id>')
    async def serve_media(media_id):
        try:
            async with app.db_pool.acquire() as conn:
                query = 'SELECT file_data, url, media_type FROM memes WHERE id = $1'
                row = await conn.fetchrow(query, media_id)
                
                if row:
                    media_data = row['file_data']
                    media_type = row['media_type']
                    
                    content_type = {
                        'video': 'video/mp4',
                        'image': 'image/jpeg',
                        'gif': 'image/gif'
                    }.get(media_type, 'application/octet-stream')
                    
                    logger.info(f"Serving media ID {media_id} of type {media_type}")
                    return Response(media_data, content_type=content_type)
                
                logger.warning(f"Media ID {media_id} not found")
                return 'Media not found', 404
        except Exception as e:
            logger.error(f"Error serving media {media_id}: {str(e)}")
            return f"Error serving media: {str(e)}", 500

    @app.route('/api/feed')
    async def get_feed():
        try:
            page = request.args.get('page', '1')
            page = max(1, int(page))
        except ValueError:
            page = 1
        
        try:
            items, has_more = await feed_manager.get_feed_items(page)
            return jsonify({
                'items': [{
                    'id': item.id,
                    'type': item.type,
                    'username': item.username,
                    'description': item.description,
                    'likes': item.likes,
                    'comments': item.comments,
                    'shares': item.shares,
                    'created_at': item.created_at.isoformat(),
                    'media_url': url_for('serve_media', media_id=int(item.id))
                } for item in items],
                'hasMore': has_more
            })
        except Exception as e:
            logger.error(f"Error in get_feed: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/mute', methods=['POST'])
    async def toggle_mute():
        try:
            data = await request.json
            is_muted = data.get('is_muted', True)
            logger.info(f"Mute state changed to: {'muted' if is_muted else 'unmuted'}")
            return jsonify({'status': 'success', 'is_muted': is_muted})
        except Exception as e:
            logger.error(f"Error handling mute state: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api/like/<item_id>', methods=['POST'])
    async def toggle_like(item_id):
        if 'username' not in session:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
            
        try:
            async with app.db_pool.acquire() as conn:
                # First, get current user data
                user = await conn.fetchrow(
                    'SELECT liked_memes FROM users WHERE username = $1',
                    session['username']
                )
                
                if not user:
                    return jsonify({'status': 'error', 'message': 'User not found'}), 404
                
                # Initialize liked_memes as empty list if None
                liked_memes = []
                if user['liked_memes']:
                    try:
                        liked_memes = json.loads(user['liked_memes'])
                    except json.JSONDecodeError:
                        liked_memes = []
                
                # Ensure liked_memes is a list
                if not isinstance(liked_memes, list):
                    liked_memes = []
                
                # Convert item_id to string for consistency
                item_id_str = str(item_id)
                
                # Toggle like status
                if item_id_str in liked_memes:
                    liked_memes.remove(item_id_str)
                    action = 'unliked'
                else:
                    liked_memes.append(item_id_str)
                    action = 'liked'
                
                # Update database with new liked_memes array
                await conn.execute(
                    '''
                    UPDATE users 
                    SET liked_memes = $1::jsonb 
                    WHERE username = $2
                    ''',
                    json.dumps(liked_memes),
                    session['username']
                )
                
                logger.info(f"Item {item_id} was {action} by {session['username']}")
                return jsonify({'status': 'success', 'action': action})
                
        except Exception as e:
            logger.error(f"Error toggling like for item {item_id}: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/profile', methods=['GET', 'POST'])
    async def profile():
        if 'username' not in session:
            return redirect(url_for('login'))
            
        async with app.db_pool.acquire() as conn:
            if request.method == 'POST':
                form = await request.form
                bio = form.get('bio', '').strip()
                
                await conn.execute(
                    'UPDATE users SET bio = $1 WHERE username = $2',
                    bio, session['username']
                )
                return redirect(url_for('profile'))
            
            user = await conn.fetchrow(
                'SELECT username, bio, avatar_url, liked_memes FROM users WHERE username = $1',
                session['username']
            )
            
            # Fetch meme IDs for liked memes
            liked_memes = []
            if user['liked_memes']:
                try:
                    # Parse JSON string and keep IDs as strings
                    meme_ids = json.loads(user['liked_memes'])
                    if meme_ids:  # Check if array is not empty
                        query = '''
                            SELECT id, media_type FROM memes
                            WHERE id::text = ANY($1::text[])
                        '''
                        liked_memes = await conn.fetch(query, meme_ids)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Error parsing liked_memes: {str(e)}")
            
        return await render_template('profile.html',
            username=user['username'],
            bio=user['bio'],
            avatar_url=user['avatar_url'],
            liked_memes=liked_memes
        )

    return app

async def main():
    try:
        app = await create_app()
        config = Config()
        config.bind = ["127.0.0.1:5001"]
        await serve(app, config)
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == '__main__':
    asyncio.run(main())
