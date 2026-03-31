class MediaService:
    def __init__(self, pool):
        self.pool = pool

    @staticmethod
    def _detect_image_type(data: bytes) -> str:
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'image/png'
        if data[:3] == b'GIF':
            return 'image/gif'
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'image/webp'
        return 'image/jpeg'

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

                # Determine content type based on media type and file magic bytes
                if media['media_type'] == 'image':
                    content_type = self._detect_image_type(media['file_data'])
                elif media['media_type'] == 'video':
                    content_type = 'video/mp4'
                else:
                    content_type = 'application/octet-stream'

                ext_map = {
                    'image/jpeg': 'jpg', 'image/png': 'png',
                    'image/gif': 'gif', 'image/webp': 'webp',
                    'video/mp4': 'mp4',
                }
                ext = ext_map.get(content_type, 'bin')
                filename = f"media_{media_id}.{ext}"

                return {
                    'file_data': media['file_data'],
                    'content_type': content_type,
                    'filename': filename,
                    'media_type': media['media_type']
                }

        except Exception as e:
            print(f"Error serving media {media_id}: {str(e)}")
            return None
