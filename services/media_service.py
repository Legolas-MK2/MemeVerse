class MediaService:
    def __init__(self, pool):
        self.pool = pool

    async def serve_media(self, media_id: int) -> dict:
        """
        Serve media by ID
        Returns dict with media data and metadata, or None if not found
        """
        try:
            async with self.pool.acquire() as conn:
                media = await conn.fetchrow(
                    'SELECT file_data, media_type FROM memes WHERE id = $1',
                    media_id
                )

                if not media:
                    return None

                # Determine content type based on media type
                if media['media_type'] == 'image':
                    content_type = 'image/jpeg'
                elif media['media_type'] == 'video':
                    content_type = 'video/mp4'
                else:
                    content_type = 'application/octet-stream'

                filename = f"media_{media_id}.{'jpg' if media['media_type'] == 'image' else 'mp4'}"

                return {
                    'file_data': media['file_data'],
                    'content_type': content_type,
                    'filename': filename,
                    'media_type': media['media_type']
                }

        except Exception as e:
            print(f"Error serving media {media_id}: {str(e)}")
            return None
