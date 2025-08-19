import re
import json
from quart import session


class TagService:
    def __init__(self, pool):
        self.pool = pool

    async def get_user_tags(self, username: str) -> dict:
        """
        Get all tags for a user
        """
        if 'username' not in session:
            return {'status': 'error', 'message': 'Not logged in'}

        try:
            async with self.pool.acquire() as conn:
                # Get user ID
                user = await conn.fetchrow(
                    'SELECT id FROM users WHERE username = $1',
                    session['username']
                )

                if not user:
                    return {'status': 'error', 'message': 'User not found'}

                user_id = user['id']

                # Get all tags for this user
                tags = await conn.fetch(
                    'SELECT id, name, color, created_at, last_used FROM tags WHERE user_id = $1 ORDER BY last_used DESC NULLS LAST, created_at DESC',
                    user_id
                )

                # Convert to list of dicts
                tag_list = [dict(tag) for tag in tags]

                return {'status': 'success', 'tags': tag_list}

        except Exception as e:
            print(f"Error getting user tags: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def create_tag(self, tag_name: str, tag_color: str = '#94a3b8') -> dict:
        """
        Create a new tag for the user
        """
        if 'username' not in session:
            return {'status': 'error', 'message': 'Not logged in'}

        try:
            # Validate tag name (not blank)
            if not tag_name or not tag_name.strip():
                return {'status': 'error', 'message': 'Tag name cannot be blank'}

            # Validate color format (hex)
            if not re.match(r'^#(?:[0-9a-f]{3}){1,2}$', tag_color, re.IGNORECASE):
                return {'status': 'error', 'message': 'Invalid color format'}

            async with self.pool.acquire() as conn:
                # Get user ID
                user = await conn.fetchrow(
                    'SELECT id FROM users WHERE username = $1',
                    session['username']
                )

                if not user:
                    return {'status': 'error', 'message': 'User not found'}

                user_id = user['id']

                # Create the tag
                tag = await conn.fetchrow(
                    '''
                    INSERT INTO tags (user_id, name, color)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, lower(name)) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id, name, color, created_at, last_used
                    ''',
                    user_id, tag_name.strip(), tag_color
                )

                return {
                    'status': 'success',
                    'tag': {
                        'id': tag['id'],
                        'name': tag['name'],
                        'color': tag['color'],
                        'created_at': tag['created_at'],
                        'last_used': tag['last_used']
                    }
                }

        except Exception as e:
            print(f"Error creating tag: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def delete_tag(self, tag_id: int) -> dict:
        """
        Delete a tag
        """
        if 'username' not in session:
            return {'status': 'error', 'message': 'Not logged in'}

        try:
            async with self.pool.acquire() as conn:
                # Get user ID
                user = await conn.fetchrow(
                    'SELECT id FROM users WHERE username = $1',
                    session['username']
                )

                if not user:
                    return {'status': 'error', 'message': 'User not found'}

                user_id = user['id']

                # Delete the tag (will also delete associated meme_tags due to CASCADE)
                result = await conn.execute(
                    'DELETE FROM tags WHERE id = $1 AND user_id = $2',
                    tag_id, user_id
                )

                if result == 'DELETE 0':
                    return {'status': 'error', 'message': 'Tag not found or not owned by user'}

                return {'status': 'success', 'message': 'Tag deleted'}

        except Exception as e:
            print(f"Error deleting tag: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def get_meme_tags(self, meme_id: int) -> dict:
        """
        Get tags for a specific meme
        """
        if 'username' not in session:
            return {'status': 'error', 'message': 'Not logged in'}

        try:
            async with self.pool.acquire() as conn:
                # Get user ID
                user = await conn.fetchrow(
                    'SELECT id FROM users WHERE username = $1',
                    session['username']
                )

                if not user:
                    return {'status': 'error', 'message': 'User not found'}

                user_id = user['id']

                # Get tags for this meme and user
                tags = await conn.fetch(
                    '''
                    SELECT t.id, t.name, t.color
                    FROM tags t
                    JOIN meme_tags mt ON t.id = mt.tag_id
                    WHERE mt.meme_id = $1 AND mt.user_id = $2 AND t.user_id = $2
                    ''',
                    meme_id, user_id
                )

                # Convert to list of dicts
                tag_list = [dict(tag) for tag in tags]

                return {'status': 'success', 'tags': tag_list}

        except Exception as e:
            print(f"Error getting meme tags: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def add_tags_to_meme(self, meme_id: int, tag_ids: list) -> dict:
        """
        Add tags to a meme
        """
        if 'username' not in session:
            return {'status': 'error', 'message': 'Not logged in'}

        try:
            if not tag_ids:
                return {'status': 'error', 'message': 'Tag IDs are required'}

            async with self.pool.acquire() as conn:
                # Get user ID
                user = await conn.fetchrow(
                    'SELECT id FROM users WHERE username = $1',
                    session['username']
                )

                if not user:
                    return {'status': 'error', 'message': 'User not found'}

                user_id = user['id']

                # Verify meme exists
                meme = await conn.fetchrow(
                    'SELECT id FROM memes WHERE id = $1',
                    meme_id
                )

                if not meme:
                    return {'status': 'error', 'message': 'Meme not found'}

                # Add tags to meme (will trigger last_used update)
                for tag_id in tag_ids:
                    try:
                        await conn.execute(
                            '''
                            INSERT INTO meme_tags (user_id, meme_id, tag_id)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (user_id, meme_id, tag_id) DO NOTHING
                            ''',
                            user_id, meme_id, tag_id
                        )
                    except Exception as e:
                        print(f"Error adding tag {tag_id} to meme {meme_id}: {str(e)}")
                        # Continue with other tags even if one fails

                return {'status': 'success', 'message': 'Tags added to meme'}

        except Exception as e:
            print(f"Error adding tags to meme: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def remove_tag_from_meme(self, meme_id: int, tag_id: int) -> dict:
        """
        Remove a tag from a meme
        """
        if 'username' not in session:
            return {'status': 'error', 'message': 'Not logged in'}

        try:
            async with self.pool.acquire() as conn:
                # Get user ID
                user = await conn.fetchrow(
                    'SELECT id FROM users WHERE username = $1',
                    session['username']
                )

                if not user:
                    return {'status': 'error', 'message': 'User not found'}

                user_id = user['id']

                # Remove tag from meme (will trigger last_used update)
                result = await conn.execute(
                    'DELETE FROM meme_tags WHERE user_id = $1 AND meme_id = $2 AND tag_id = $3',
                    user_id, meme_id, tag_id
                )

                if result == 'DELETE 0':
                    return {'status': 'error', 'message': 'Tag not found on meme'}

                return {'status': 'success', 'message': 'Tag removed from meme'}

        except Exception as e:
            print(f"Error removing tag from meme: {str(e)}")
            return {'status': 'error', 'message': str(e)}
