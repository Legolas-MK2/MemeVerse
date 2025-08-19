from quart import Blueprint, jsonify, request, session
from services.tag_service import TagService


tag_bp = Blueprint('tag', __name__)


def init_tag_routes(app, pool):
    tag_service = TagService(pool)
    
    @tag_bp.route('/api/tags', methods=['GET'])
    async def get_user_tags():
        result = await tag_service.get_user_tags(session.get('username'))
        if result['status'] == 'error' and result['message'] == 'Not logged in':
            return jsonify(result), 401
        return jsonify(result)
        
    @tag_bp.route('/api/tags', methods=['POST'])
    async def create_tag():
        try:
            data = await request.get_json()
            tag_name = data.get('name')
            tag_color = data.get('color', '#94a3b8')  # Default color if not provided
            
            result = await tag_service.create_tag(tag_name, tag_color)
            if result['status'] == 'error' and result['message'] == 'Not logged in':
                return jsonify(result), 401
            return jsonify(result)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
            
    @tag_bp.route('/api/tags/<int:tag_id>', methods=['DELETE'])
    async def delete_tag(tag_id):
        result = await tag_service.delete_tag(tag_id)
        if result['status'] == 'error' and result['message'] == 'Not logged in':
            return jsonify(result), 401
        elif result['status'] == 'error' and result['message'] == 'Tag not found or not owned by user':
            return jsonify(result), 404
        return jsonify(result)
        
    @tag_bp.route('/api/memes/<int:meme_id>/tags', methods=['GET'])
    async def get_meme_tags(meme_id):
        result = await tag_service.get_meme_tags(meme_id)
        if result['status'] == 'error' and result['message'] == 'Not logged in':
            return jsonify(result), 401
        return jsonify(result)
        
    @tag_bp.route('/api/memes/<int:meme_id>/tags', methods=['POST'])
    async def add_tags_to_meme(meme_id):
        try:
            data = await request.get_json()
            tag_ids = data.get('tag_ids', [])
            
            result = await tag_service.add_tags_to_meme(meme_id, tag_ids)
            if result['status'] == 'error' and result['message'] == 'Not logged in':
                return jsonify(result), 401
            return jsonify(result)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
            
    @tag_bp.route('/api/memes/<int:meme_id>/tags/<int:tag_id>', methods=['DELETE'])
    async def remove_tag_from_meme(meme_id, tag_id):
        result = await tag_service.remove_tag_from_meme(meme_id, tag_id)
        if result['status'] == 'error' and result['message'] == 'Not logged in':
            return jsonify(result), 401
        elif result['status'] == 'error' and result['message'] == 'Tag not found on meme':
            return jsonify(result), 404
        return jsonify(result)
        
    app.register_blueprint(tag_bp)
