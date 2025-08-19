import bcrypt
import json
import uuid
from quart import session


class UserService:
    def __init__(self, pool):
        self.pool = pool

    async def ensure_user_id(self):
        """
        Ensure user has a session ID
        """
        if 'user_id' not in session:
            session['user_id'] = str(uuid.uuid4())

    async def authenticate_user(self, username: str, password: str) -> bool:
        """
        Authenticate user with username and password
        Returns True if authentication successful, False otherwise
        """
        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT * FROM users WHERE username = $1',
                    username
                )

                if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                    session['username'] = username
                    session['user_id'] = user['id']
                    return True
                else:
                    return False
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return False

    async def register_user(self, username: str, password: str) -> tuple[bool, str]:
        """
        Register a new user
        Returns tuple of (success, error_message)
        """
        try:
            if not username or not password:
                return False, 'Username and password are required'

            hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

            async with self.pool.acquire() as conn:
                try:
                    await conn.execute(
                        'INSERT INTO users (username, password_hash) VALUES ($1, $2)',
                        username, hashed_password
                    )
                    session['username'] = username
                    return True, ''
                except asyncpg.UniqueViolationError:
                    return False, 'Username already exists'
                except Exception as e:
                    print(f"Registration error: {str(e)}")
                    return False, 'Registration failed'
        except Exception as e:
            print(f"Registration error: {str(e)}")
            return False, 'Registration failed'

    async def get_user_profile(self, username: str) -> dict:
        """
        Get user profile information
        """
        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT username, created_at, liked_memes FROM users WHERE username = $1',
                    username
                )

                if not user:
                    return None

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
                        print("Error decoding liked_memes JSON")

                return {
                    'user': user,
                    'liked_memes': liked_memes[::-1]  # Newest first
                }
        except Exception as e:
            print(f"Error fetching user profile: {str(e)}")
            return None

    async def get_current_user_profile(self) -> dict:
        """
        Get current user's profile information
        """
        if 'username' not in session:
            return None

        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT username, created_at, bio, ui_settings FROM users WHERE username = $1',
                    session['username']
                )

                if not user:
                    return None

                navbar_settings = {}
                if user['ui_settings']:
                    try:
                        # Handle case where ui_settings might be a JSON string
                        if isinstance(user['ui_settings'], str):
                            ui_settings = json.loads(user['ui_settings'])
                        else:
                            ui_settings = user['ui_settings']
                        # Extract navbar settings from the ui_settings structure
                        if 'navbar' in ui_settings:
                            navbar_settings = ui_settings['navbar']
                        else:
                            navbar_settings = ui_settings
                    except Exception as e:
                        print(f"Error processing ui_settings: {str(e)}")

                return {
                    'username': user['username'],
                    'member_since': user['created_at'].strftime('%B %Y'),
                    'bio': user['bio'],
                    'navbar_settings': navbar_settings
                }
        except Exception as e:
            print(f"Error fetching profile: {str(e)}")
            return None

    async def update_user_bio(self, bio: str) -> bool:
        """
        Update user's bio
        """
        if 'username' not in session:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    'UPDATE users SET bio = $1 WHERE username = $2',
                    bio.strip(),
                    session['username']
                )
                return True
        except Exception as e:
            print(f"Error updating bio: {str(e)}")
            return False

    async def get_all_users(self) -> list:
        """
        Get all users with their like counts
        """
        try:
            async with self.pool.acquire() as conn:
                users = await conn.fetch('''
                    SELECT 
                        u.username,
                        u.created_at,
                        CASE 
                            WHEN u.liked_memes IS NULL THEN 0
                            ELSE json_array_length(u.liked_memes::json)
                        END as like_count
                    FROM users u
                    ORDER BY u.created_at DESC
                ''')

                # Convert to list of dicts
                user_list = []
                for user in users:
                    user_dict = dict(user)
                    user_list.append(user_dict)

                return user_list
        except Exception as e:
            print(f"Error fetching users: {str(e)}")
            return []
