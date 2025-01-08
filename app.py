from quart import Quart, render_template, jsonify, request, url_for, session, Response, redirect
import asyncpg
from dotenv import load_dotenv
load_dotenv()
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
import bcrypt
import os

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'user': os.getenv('POSTGREST_USERNAME', 'discord_meme'),
    'password': os.getenv('POSTGREST_PASSWORD'),
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
        self.items_per_page = 15
        self.preload_threshold = 5
        self.pool = pool

    async def _get_media_items(self, page: int) -> List[dict]:
        try:
            async with self.pool.acquire() as conn:
                query = '''
                    SELECT id, url, file_data, timestamp, author_id, media_type 
                    FROM memes 
                    WHERE file_data IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT $1
                '''
                rows = await conn.fetch(query, self.items_per_page)
                
                media_items = []
                for row in rows:
                    media_items.append({
                        'meme_id': row['id'],
                        'url': row['url'],
                        'media_data': row['file_data'],
                        'timestamp': row['timestamp'],
                        'author_id': row['author_id'],
                        'media_type': row['media_type']
                    })
                return media_items
        except Exception as e:
            logger.error(f"Database error in _get_media_items: {str(e)}")
            return []

    async def get_total_items(self) -> int:
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval('SELECT COUNT(*) FROM memes WHERE file_data IS NOT NULL')
                return count
        except Exception as e:
            logger.error(f"Error getting total items: {str(e)}")
            return 0

    async def generate_feed_data(self, page: int) -> List[FeedItem]:
        try:
            media_items = await self._get_media_items(page)
            new_items = []
            
            for media in media_items:
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
    app = Quart(__name__, static_folder='static')
    app.secret_key = 'your-secret-key-here'

    try:
        pool = await asyncpg.create_pool(**DB_CONFIG)
        logger.info("Successfully connected to database")
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

    app.db_pool = pool
    feed_manager = FeedManager(pool)

    @app.before_request
    async def ensure_user_id():
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())
        
        if request.endpoint not in ['login', 'static', 'register'] and 'username' not in session:
            return redirect(url_for('login'))

    @app.template_filter('format_number')
    def format_number(value):
        if value >= 1000000:
            return f'{value/1000000:.1f}M'
        elif value >= 1000:
            return f'{value/1000:.1f}K'
        return str(value)

    @app.route('/api/liked-memes')
    async def api_liked_memes():
        logger.info("Received request for liked memes API")
        if 'username' not in session:
            logger.warning("Unauthorized access attempt to liked memes API")
            return jsonify({'error': 'Not authenticated'}), 401
            
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 12))
            
            logger.info(f"Fetching liked memes for user {session['username']}, page {page}")
            
            async with app.db_pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT liked_memes FROM users WHERE username = $1',
                    session['username']
                )
                
                if not user:
                    logger.warning(f"User {session['username']} not found")
                    return jsonify({'error': 'User not found'}), 404

                if not user['liked_memes']:
                    logger.info(f"No liked memes found for user {session['username']}")
                    return jsonify({
                        'memes': [],
                        'hasMore': False
                    })

                try:
                    liked_meme_ids = json.loads(user['liked_memes'])[::-1]  # Newest first
                    
                    # Calculate pagination
                    start_idx = (page - 1) * per_page
                    end_idx = start_idx + per_page
                    page_meme_ids = liked_meme_ids[start_idx:end_idx]
                    
                    logger.debug(f"Fetching memes {start_idx} to {end_idx}")
                    
                    memes = []
                    for meme_id in page_meme_ids:
                        meme = await conn.fetchrow(
                            'SELECT id, media_type FROM memes WHERE id = $1',
                            int(meme_id)
                        )
                        if meme:
                            memes.append({
                                'id': meme['id'],
                                'media_type': meme['media_type']
                            })
                    
                    response_data = {
                        'memes': memes,
                        'hasMore': end_idx < len(liked_meme_ids)
                    }
                    logger.info(f"Returning {len(memes)} memes")
                    return jsonify(response_data)
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return jsonify({'error': 'Invalid data format'}), 500
                    
        except Exception as e:
            logger.error(f"Error in api_liked_memes: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/')
    async def index():
        try:
            first_page_items, has_more = await feed_manager.get_feed_items(1)
            return await render_template('index.html', 
                feed_items=first_page_items, 
                has_more=has_more
            )
        except Exception as e:
            logger.error(f"Error in index route: {str(e)}")
            return f"An error occurred: {str(e)}", 500

    @app.route('/login', methods=['GET', 'POST'])
    async def login():
        if request.method == 'POST':
            try:
                data = await request.form
                username = data.get('username')
                password = data.get('password')
                
                async with app.db_pool.acquire() as conn:
                    user = await conn.fetchrow(
                        'SELECT * FROM users WHERE username = $1',
                        username
                    )
                    
                    if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                        session['username'] = username
                        session['user_id'] = user['id']
                        return redirect(url_for('index'))
                    else:
                        return await render_template('login.html', error='Invalid credentials')
                        
            except Exception as e:
                logger.error(f"Login error: {str(e)}")
                return await render_template('login.html', error='Login failed')
                
        return await render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    async def register():
        if request.method == 'POST':
            try:
                data = await request.form
                username = data.get('username')
                password = data.get('password')
                
                if not username or not password:
                    return await render_template('register.html', error='Username and password are required')
                
                hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                
                async with app.db_pool.acquire() as conn:
                    try:
                        await conn.execute(
                            'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                            username, hashed_password
                        )
                        session['username'] = username
                        return redirect(url_for('index'))
                    except asyncpg.UniqueViolationError:
                        return await render_template('register.html', error='Username already exists')
                    except Exception as e:
                        logger.error(f"Registration error: {str(e)}")
                        return await render_template('register.html', error='Registration failed')
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                return await render_template('register.html', error='Registration failed')
        
        return await render_template('register.html')

    @app.route('/users')
    async def users():
        if 'username' not in session:
            return redirect(url_for('login'))
            
        try:
            async with app.db_pool.acquire() as conn:
                users = await conn.fetch(
                    'SELECT username, created_at FROM users ORDER BY created_at DESC'
                )
                return await render_template('users.html', users=users)
                
        except Exception as e:
            logger.error(f"Error fetching users: {str(e)}")
            return redirect(url_for('index'))

    @app.route('/user/<username>')
    async def user_profile(username):
        if 'username' not in session:
            return redirect(url_for('login'))
            
        try:
            async with app.db_pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT username, created_at, liked_memes FROM users WHERE username = $1',
                    username
                )
                
                if not user:
                    return redirect(url_for('index'))

                liked_memes = []
                if user['liked_memes']:
                    try:
                        liked_meme_ids = json.loads(user['liked_memes'])
                        for meme_id in liked_meme_ids:
                            meme = await conn.fetchrow(
                                'SELECT id, media_type FROM memes WHERE id = $1',
                                int(meme_id)
                            )
                            if meme:
                                liked_memes.append({
                                    'id': meme['id'],
                                    'media_type': meme['media_type']
                                })
                    except json.JSONDecodeError:
                        logger.error("Error decoding liked_memes JSON")
                
                return await render_template('user_profile.html', 
                    user=user,
                    liked_memes=liked_memes
                )
                
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return redirect(url_for('index'))

    @app.route('/profile')
    async def profile():
        if 'username' not in session:
            return redirect(url_for('login'))
            
        try:
            async with app.db_pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT username, created_at, bio FROM users WHERE username = $1',
                    session['username']
                )
                
                if not user:
                    return redirect(url_for('index'))

                # Read the loading animation SVG from static file
                try:
                    with open('static/loading-animation.svg', 'r') as f:
                        loading_svg = f.read()
                except Exception as e:
                    logger.error(f"Error reading loading animation SVG: {str(e)}")
                    loading_svg = '<div>Loading...</div>'

                return await render_template('profile.html', 
                    username=user['username'],
                    member_since=user['created_at'].strftime('%B %Y'),
                    bio=user['bio'],
                    loading_svg=loading_svg
                )
                
        except Exception as e:
            logger.error(f"Error fetching profile: {str(e)}")
            return redirect(url_for('index'))

    @app.route('/settings', methods=['GET', 'POST'])
    async def settings():
        if 'username' not in session:
            return redirect(url_for('login'))
            
        try:
            async with app.db_pool.acquire() as conn:
                if request.method == 'POST':
                    form = await request.form
                    new_bio = form.get('bio', '').strip()
                    
                    await conn.execute(
                        'UPDATE users SET bio = $1 WHERE username = $2',
                        new_bio,
                        session['username']
                    )
                    return redirect(url_for('settings'))
                
                user = await conn.fetchrow(
                    'SELECT username, bio FROM users WHERE username = $1',
                    session['username']
                )
                return await render_template('settings.html', bio=user['bio'])
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            return redirect(url_for('index'))

    @app.route('/search')
    async def search():
        if 'username' not in session:
            return redirect(url_for('login'))
            
        try:
            query = request.args.get('q', '')
            results = []
            
            if query:
                async with app.db_pool.acquire() as conn:
                    # Search users
                    users = await conn.fetch(
                        'SELECT username FROM users WHERE username ILIKE $1 LIMIT 10',
                        f'%{query}%'
                    )
                    
                    # Search memes
                    memes = await conn.fetch(
                        'SELECT id, media_type FROM memes WHERE description ILIKE $1 LIMIT 10',
                        f'%{query}%'
                    )
                    
                    results = [
                        *[{'type': 'user', 'data': u} for u in users],
                        *[{'type': 'meme', 'data': m} for m in memes]
                    ]
            
            return await render_template('search.html', 
                query=query,
                results=results
            )
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return redirect(url_for('index'))

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
                    'media_url': url_for('serve_media', media_id=int(item.id), _external=True)
                } for item in items],
                'hasMore': has_more
            })
        except Exception as e:
            logger.error(f"Error in get_feed: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/media/<int:media_id>')
    async def serve_media(media_id):
        try:
            logger.debug(f"Media request received for ID: {media_id}")
            async with app.db_pool.acquire() as conn:
                media = await conn.fetchrow(
                    'SELECT file_data, media_type FROM memes WHERE id = $1',
                    media_id
                )
                
                if not media:
                    logger.debug(f"Media not found for ID: {media_id}")
                    return Response('Media not found', status=404)
                
                # Determine content type based on media type
                if media['media_type'] == 'image':
                    content_type = 'image/jpeg'
                elif media['media_type'] == 'video':
                    content_type = 'video/mp4'
                else:
                    content_type = 'application/octet-stream'
                
                logger.debug(f"Serving media ID: {media_id}, Type: {media['media_type']}, Size: {len(media['file_data'])} bytes")
                
                response = Response(media['file_data'], content_type=content_type)
                response.headers['Accept-Ranges'] = 'bytes'
                response.headers['Cache-Control'] = 'no-cache'
                response.headers['Content-Length'] = str(len(media['file_data']))
                
                filename = f"media_{media_id}.{'jpg' if media['media_type'] == 'image' else 'mp4'}"
                response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
                
                return response
                
        except Exception as e:
            logger.error(f"Error serving media {media_id}: {str(e)}")
            return Response('Error serving media', status=500)

    @app.route('/api/like/<item_id>', methods=['POST'])
    async def toggle_like(item_id):
        if 'username' not in session:
            return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
            
        try:
            async with app.db_pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT liked_memes FROM users WHERE username = $1',
                    session['username']
                )
                
                if not user:
                    return jsonify({'status': 'error', 'message': 'User not found'}), 404
                
                liked_memes = []
                if user['liked_memes']:
                    try:
                        liked_memes = json.loads(user['liked_memes'])
                    except json.JSONDecodeError:
                        liked_memes = []
                
                item_id_str = str(item_id)
                
                if item_id_str in liked_memes:
                    liked_memes.remove(item_id_str)
                    action = 'unliked'
                else:
                    liked_memes.append(item_id_str)
                    action = 'liked'
                
                await conn.execute(
                    'UPDATE users SET liked_memes = $1::jsonb WHERE username = $2',
                    json.dumps(liked_memes),
                    session['username']
                )
                
                return jsonify({'status': 'success', 'action': action})
                
        except Exception as e:
            logger.error(f"Error toggling like for item {item_id}: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # Debug route to list all registered routes
    @app.route('/debug/routes')
    async def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
        return jsonify(routes)

    # Log all registered routes
    logger.info("Application routes registered:")
    for rule in app.url_map.iter_rules():
        logger.info(f"Route: {rule.endpoint} -> {rule}")

    return app

async def main():
    try:
        app = await create_app()
        config = Config()
        config.bind = ["0.0.0.0:5001"]
        await serve(app, config)
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == '__main__':
    asyncio.run(main())