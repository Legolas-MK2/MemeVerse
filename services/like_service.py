import json
from quart import session


class LikeService:
    def __init__(self, pool):
        self.pool = pool

    async def get_meme_tags(self, conn, meme_id: int, user_id: int):
        """
        Get tags for a specific meme and user
        """
        try:
            tags = await conn.fetch(
                '''
                SELECT t.id, t.name, t.color
                FROM tags t
                JOIN meme_tags mt ON t.id = mt.tag_id
                WHERE mt.meme_id = $1 AND mt.user_id = $2 AND t.user_id = $2
                ''',
                meme_id, user_id
            )
            return [dict(tag) for tag in tags]
        except Exception as e:
            print(f"Error getting meme tags: {str(e)}")
            return []

    async def toggle_like(self, item_id: str) -> dict:
        """
        Toggle like status for an item
        Returns dict with status and action
        """
        if 'username' not in session:
            return {'status': 'error', 'message': 'Not logged in'}

        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT liked_memes FROM users WHERE username = $1',
                    session['username']
                )

                if not user:
                    return {'status': 'error', 'message': 'User not found'}

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

                return {'status': 'success', 'action': action}

        except Exception as e:
            print(f"Error toggling like for item {item_id}: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    async def get_user_liked_memes(self, target_username: str = None, page: int = 1, per_page: int = 12) -> dict:
        """
        Get liked memes for a user
        """
        # Check if we're requesting a specific user's liked memes
        if not target_username:
            # Default to current user if no username specified
            if 'username' not in session:
                return {'error': 'Not authenticated'}
            target_username = session['username']

        try:
            async with self.pool.acquire() as conn:
                user = await conn.fetchrow(
                    'SELECT liked_memes FROM users WHERE username = $1',
                    target_username
                )

                if not user:
                    return {'error': 'User not found'}

                if not user['liked_memes']:
                    return {
                        'memes': [],
                        'hasMore': False
                    }

                try:
                    liked_meme_ids = json.loads(user['liked_memes'])[::-1]  # Newest first

                    # Calculate pagination
                    start_idx = (page - 1) * per_page
                    end_idx = start_idx + per_page
                    page_meme_ids = liked_meme_ids[start_idx:end_idx]

                    # Get user ID for tag lookup
                    user_record = await conn.fetchrow(
                        'SELECT id FROM users WHERE username = $1',
                        target_username
                    )
                    user_id = user_record['id'] if user_record else None

                    memes = []
                    for meme_id in page_meme_ids:
                        meme = await conn.fetchrow(
                            'SELECT id, media_type FROM memes WHERE id = $1',
                            int(meme_id)
                        )
                        if meme:
                            # Get tags for this meme
                            tags = []
                            if user_id:
                                tags = await self.get_meme_tags(conn, meme['id'], user_id)
                            
                            memes.append({
                                'id': meme['id'],
                                'media_type': meme['media_type'],
                                'media_url': f'/media/{meme["id"]}',
                                'tags': tags
                            })

                    return {
                        'memes': memes,
                        'hasMore': end_idx < len(liked_meme_ids)
                    }

                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {str(e)}")
                    return {'error': 'Invalid data format'}

        except Exception as e:
            print(f"Error in get_user_liked_memes: {str(e)}")
            return {'error': str(e)}
