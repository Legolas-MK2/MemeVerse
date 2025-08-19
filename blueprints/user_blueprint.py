from quart import Blueprint, render_template, request, redirect, url_for, session, jsonify
from services.user_service import UserService
from services.tag_service import TagService
import json


user_bp = Blueprint('user', __name__)


def init_user_routes(app, pool):
    user_service = UserService(pool)
    tag_service = TagService(pool)
    
    @user_bp.before_request
    async def require_login():
        if request.endpoint not in ['static'] and 'username' not in session:
            return redirect(url_for('auth.login'))

    @user_bp.route('/users')
    async def users():
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
            
            user_list = await user_service.get_all_users()
            return await render_template('users.html', 
                                        users=user_list,
                                        navbar_position=f"nav-{navbar_position}")
        except Exception as e:
            print(f"Error fetching users: {str(e)}")
            return redirect(url_for('feed.index'))

    @user_bp.route('/user/<username>')
    async def user_profile(username):
        try:
            profile_data = await user_service.get_user_profile(username)
            if not profile_data:
                return redirect(url_for('feed.index'))
            
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
            
            return await render_template('user_profile.html', 
                user=profile_data['user'],
                liked_memes=profile_data['liked_memes'],
                navbar_position=f"nav-{navbar_position}"
            )
        except Exception as e:
            print(f"Error fetching user profile: {str(e)}")
            return redirect(url_for('feed.index'))

    @user_bp.route('/profile')
    async def profile():
        try:
            profile_data = await user_service.get_current_user_profile()
            if not profile_data:
                return redirect(url_for('auth.login'))

            # Get navbar position for current user
            navbar_position = 'bottom'  # Default position
            if profile_data and profile_data.get('navbar_settings'):
                navbar_settings_data = profile_data['navbar_settings']
                # Get the position for the navbar
                navbar_position = navbar_settings_data.get('pc', navbar_settings_data.get('PC', 'bottom'))
            
            # Read the loading animation SVG from static file
            try:
                with open('static/loading-animation.svg', 'r') as f:
                    loading_svg = f.read()
            except Exception as e:
                print(f"Error reading loading animation SVG: {str(e)}")
                loading_svg = '<div>Loading...</div>'

            return await render_template('profile.html', 
                username=profile_data['username'],
                member_since=profile_data['member_since'],
                bio=profile_data['bio'],
                loading_svg=loading_svg,
                navbar_position=f"nav-{navbar_position}"
            )
        except Exception as e:
            print(f"Error fetching profile: {str(e)}")
            return redirect(url_for('feed.index'))

    @user_bp.route('/settings', methods=['GET', 'POST'])
    async def settings():
        try:
            if request.method == 'POST':
                form = await request.form
                new_bio = form.get('bio', '').strip()
                
                if await user_service.update_user_bio(new_bio):
                    return redirect(url_for('user.settings'))
                else:
                    return redirect(url_for('feed.index'))
            
            # GET request - show settings page
            async with pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT username, bio FROM users WHERE username = $1',
                    session['username']
                )
            # Get navbar settings
            navbar_settings = await user_service.get_current_user_profile()
            navbar_settings_json = '{"PC": "left", "Mobile": "bottom"}'  # Default navbar settings
            navbar_position = 'bottom'  # Default position
            
            if navbar_settings and navbar_settings.get('navbar_settings'):
                navbar_settings_data = navbar_settings['navbar_settings']
                # Extract just the navbar positioning from ui_settings.navbar
                if 'navbar' in navbar_settings_data:
                    navbar_settings_json = json.dumps(navbar_settings_data['navbar'])
                    # Get the position for the navbar
                    navbar_position = navbar_settings_data['navbar'].get('pc', navbar_settings_data['navbar'].get('PC', 'bottom'))
                else:
                    navbar_settings_json = json.dumps(navbar_settings_data)
                    # Get the position for the navbar
                    navbar_position = navbar_settings_data.get('pc', navbar_settings_data.get('PC', 'bottom'))
            
            return await render_template('settings.html', 
                                        bio=user['bio'], 
                                        navbar_settings=navbar_settings_json,
                                        navbar_position=f"nav-{navbar_position}")
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
            return redirect(url_for('feed.index'))

    @user_bp.route('/api/settings/navbar', methods=['POST'])
    async def update_navbar_settings():
        try:
            data = await request.get_json()
            navbar_settings = data.get('navbarSettings', {})
            
            async with pool.acquire() as conn:
                # Get current ui_settings
                user = await conn.fetchrow(
                    'SELECT ui_settings FROM users WHERE username = $1',
                    session['username']
                )
                
                # Update navbar settings within ui_settings
                current_ui_settings = {}
                if user['ui_settings']:
                    try:
                        # Parse the JSON string if it's a string, otherwise use as-is
                        if isinstance(user['ui_settings'], str):
                            current_ui_settings = json.loads(user['ui_settings'])
                        else:
                            current_ui_settings = user['ui_settings']
                    except (json.JSONDecodeError, TypeError):
                        # If parsing fails, start with an empty dict
                        current_ui_settings = {}
                
                current_ui_settings['navbar'] = navbar_settings
                
                await conn.execute(
                    'UPDATE users SET ui_settings = $1 WHERE username = $2',
                    json.dumps(current_ui_settings),
                    session['username']
                )
            
            return jsonify({'success': True})
        except Exception as e:
            print(f"Error updating navbar settings: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

            
    @user_bp.route('/search')
    async def search():
        try:
            query = request.args.get('q', '')
            results = []
            
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
            
            if query:
                async with pool.acquire() as conn:
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
                results=results,
                navbar_position=f"nav-{navbar_position}"
            )
        except Exception as e:
            print(f"Error during search: {str(e)}")
            return redirect(url_for('feed.index'))
            
    @user_bp.route('/tags')
    async def tags():
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
            
            # Get user tags
            tags_result = await tag_service.get_user_tags(session.get('username'))
            
            return await render_template('tags.html', 
                navbar_position=f"nav-{navbar_position}"
            )
        except Exception as e:
            print(f"Error loading tags page: {str(e)}")
            return redirect(url_for('feed.index'))
            
    app.register_blueprint(user_bp)
