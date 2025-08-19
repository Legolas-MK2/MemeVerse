from dataclasses import dataclass
from typing import List
from quart import session
import json


@dataclass
class FeedItem:
    id: str
    liked: bool  # if the current user already liked this meme
    media_type: str


class FeedManager:
    def __init__(self, pool):
        self.items: List[FeedItem] = []
        self.liked_items = set()
        # self.items_per_page = 15 # No longer fixed per page
        # self.preload_threshold = 5 # Frontend handles trigger logic
        self.pool = pool
        # Keep track of served IDs in memory *per session* might be complex.
        # Relying on RANDOM() and frontend handling duplicates is simpler for now.
        # Consider adding a seen mechanism later if duplicates become a major issue.

    # Modify _get_media_items to accept a limit
    async def _get_media_items(self, limit: int) -> List[dict]:
        if limit <= 0:
            return []
        try:
            async with self.pool.acquire() as conn:
                # Ensure we don't request more than available, though RANDOM helps
                # A more robust approach might involve tracking seen IDs per user session
                query = '''
                    SELECT id, url, file_data, timestamp, author_id, media_type
                    FROM memes
                    WHERE file_data IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT $1
                '''
                rows = await conn.fetch(query, limit)

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
            print(f"Database error in _get_media_items: {str(e)}")
            return []

    async def get_total_items(self) -> int:
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval('SELECT COUNT(*) FROM memes WHERE file_data IS NOT NULL')
                return count
        except Exception as e:
            print(f"Error getting total items: {str(e)}")
            return 0

    async def generate_feed_data(self, count: int) -> List[FeedItem]:
        try:
            media_items = await self._get_media_items(count)
            new_items = []

            for media in media_items:
                # Check if the current user has liked this meme
                liked = False
                if 'username' in session:
                    async with self.pool.acquire() as conn:
                        user = await conn.fetchrow(
                            'SELECT liked_memes FROM users WHERE username = $1',
                            session['username']
                        )
                        if user and user['liked_memes']:
                            try:
                                liked_memes = json.loads(user['liked_memes'])
                                liked = str(media['meme_id']) in liked_memes
                            except json.JSONDecodeError:
                                pass

                new_items.append(FeedItem(
                    id=str(media['meme_id']),
                    liked=liked,
                    media_type=media['media_type']
                ))
            return new_items
        except Exception as e:
            print(f"Error in generate_feed_data: {str(e)}")
            return []

    async def get_feed_items(self, count: int) -> tuple[List[FeedItem], bool]:
        # 'hasMore' becomes less critical if frontend manages cache size,
        # but we can keep it to indicate if the DB *might* have more.
        new_items = await self.generate_feed_data(count)
        # A simple approximation for hasMore: if we received fewer items than requested,
        # assume we've run out. This isn't perfect with RANDOM().
        # A better way needs total count vs seen count per user.
        has_more = len(new_items) == count if count > 0 else False
        return new_items, has_more
