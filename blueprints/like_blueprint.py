from quart import Blueprint, jsonify, request, session
from services.like_service import LikeService


like_bp = Blueprint('like', __name__)


def init_like_routes(app, pool):
    like_service = LikeService(pool)
    
    @like_bp.route('/api/like/<item_id>', methods=['POST'])
    async def toggle_like(item_id):
        result = await like_service.toggle_like(item_id)
        if result['status'] == 'error' and result['message'] == 'Not logged in':
            return jsonify(result), 401
        return jsonify(result)
        
    @like_bp.route('/api/liked-memes')
    async def api_liked_memes():
        # Get query parameters
        target_username = request.args.get('username')
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 12))
        except ValueError:
            page = 1
            per_page = 12
            
        result = await like_service.get_user_liked_memes(target_username, page, per_page)
        
        if 'error' in result:
            if result['error'] == 'Not authenticated':
                return jsonify(result), 401
            elif result['error'] == 'User not found':
                return jsonify(result), 404
            else:
                return jsonify(result), 500
                
        return jsonify(result)
        
    app.register_blueprint(like_bp)
