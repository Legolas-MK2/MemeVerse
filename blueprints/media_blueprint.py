from quart import Blueprint, Response
from services.media_service import MediaService


media_bp = Blueprint('media', __name__)


def init_media_routes(app, pool):
    media_service = MediaService(pool)
    
    @media_bp.route('/media/<int:media_id>')
    async def serve_media(media_id):
        try:
            print(f"Media request received for ID: {media_id}")
            media_data = await media_service.serve_media(media_id)
            
            if not media_data:
                print(f"Media not found for ID: {media_id}")
                return Response('Media not found', status=404)
            
            print(f"Serving media ID: {media_id}, Type: {media_data['media_type']}, Size: {len(media_data['file_data'])} bytes")
            
            response = Response(media_data['file_data'], content_type=media_data['content_type'])
            response.headers['Accept-Ranges'] = 'bytes'
            # Cache for 1 year (31536000 seconds)
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['Content-Length'] = str(len(media_data['file_data']))
            # Add ETag for cache validation
            response.headers['ETag'] = f'"{media_id}-{len(media_data["file_data"])}"'
            response.headers['Content-Disposition'] = f'inline; filename="{media_data["filename"]}"'
            
            return response
            
        except Exception as e:
            print(f"Error serving media {media_id}: {str(e)}")
            return Response('Error serving media', status=500)
            
    app.register_blueprint(media_bp)
