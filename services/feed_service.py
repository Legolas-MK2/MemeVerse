import json


class FeedService:
    def __init__(self, pool):
        self.pool = pool

    async def get_feed_items(self, count: int) -> tuple[list, bool]:
        """
        Get feed items for the user
        Returns tuple of (items, has_more)
        """
        if count <= 0:
            return [], False

        try:
            async with self.pool.acquire() as conn:
                # Get random media items
                query = '''
                    SELECT id, url, file_data, timestamp, author_id, media_type
                    FROM memes
                    WHERE file_data IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT $1
                '''
                rows = await conn.fetch(query, count)

                items = []
                has_more = len(rows) == count

                for row in rows:
                    # Note: liked status is now handled in the blueprint
                    # since we need access to the session there
                    items.append({
                        'id': str(row['id']),
                        'media_type': row['media_type'],
                        'media_url': f"/media/{row['id']}"
                    })

                return items, has_more
        except Exception as e:
            print(f"Error in get_feed_items: {str(e)}")
            return [], False

    async def get_total_items(self) -> int:
        """
        Get total number of items in the feed
        """
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval('SELECT COUNT(*) FROM memes WHERE file_data IS NOT NULL')
                return count
        except Exception as e:
            print(f"Error getting total items: {str(e)}")
            return 0
