from quart import Blueprint, render_template, jsonify, request, session
from services.feed_service import FeedService
import json


feed_bp = Blueprint('feed', __name__)


def init_feed_routes(app, pool):
    feed_service = FeedService(pool)
    
    @feed_bp.route('/')
    async def index():
        try:
            # Get navbar position for current user
            navbar_position = 'bottom'  # Default position
            if 'username' in session:
                async with pool.acquire() as conn:
                    user = await conn.fetchrow(
                        'SELECT ui_settings FROM users WHERE username = $1',
                        session['username']
                    )
                    if user and user['ui_settings']:
                        try:
                            ui_settings = json.loads(user['ui_settings'])
                            if 'navbar' in ui_settings:
                                navbar_settings = ui_settings['navbar']
                                # Use PC position if available, otherwise use any position
                                navbar_position = navbar_settings.get('pc', navbar_settings.get('PC', 'bottom'))
                        except (json.JSONDecodeError, TypeError):
                            pass
            
            # Load the initial page with an empty feed
            # The first batch of memes will be loaded via /api/feed by JS
            return await render_template('index.html',
                                         feed_items=[], # Start empty
                                         has_more=True, # Assume more available initially
                                         navbar_position=f"nav-{navbar_position}" # Pass navbar position
                                        )
        except Exception as e:
            print(f"Error in index route: {str(e)}")
            return f"An error occurred: {str(e)}", 500

    @feed_bp.route('/api/feed')
    async def get_feed():
        try:
            # Get requested count from query parameters
            count_str = request.args.get('count', '1') # Default to 1 if not specified
            try:
                count = max(0, int(count_str))
            except ValueError:
                count = 1 # Default to 1 on invalid input

            # Fetch items based on requested count
            items, has_more = await feed_service.get_feed_items(count)

            # Add liked status for each item
            for item in items:
                item['liked'] = False
                if 'username' in session:
                    async with pool.acquire() as conn:
                        user = await conn.fetchrow(
                            'SELECT liked_memes FROM users WHERE username = $1',
                            session['username']
                        )
                        if user and user['liked_memes']:
                            try:
                                liked_memes = json.loads(user['liked_memes'])
                                item['liked'] = str(item['id']) in liked_memes
                            except json.JSONDecodeError:
                                pass

            # Prepare response data (exclude large media_data)
            response_items = []
            for item in items:
                response_items.append({
                    'id': item['id'],
                    'liked': item['liked'],
                    'media_url': item['media_url'],
                    'media_type': item['media_type']  # Send media_type to help frontend
                })

            return jsonify({
                'items': response_items,
                'hasMore': has_more  # Indicate if the backend *might* have more
            })
        except Exception as e:
            print(f"Error in get_feed: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    app.register_blueprint(feed_bp)
