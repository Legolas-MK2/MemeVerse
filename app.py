from quart import Quart, jsonify
import logging
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Import our modules
from services.database_service import create_database_pool
from blueprints.auth_blueprint import init_auth_routes
from blueprints.feed_blueprint import init_feed_routes
from blueprints.user_blueprint import init_user_routes
from blueprints.media_blueprint import init_media_routes
from blueprints.like_blueprint import init_like_routes
from blueprints.tag_blueprint import init_tag_routes
from utils.helpers import format_number





# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_app():
    app = Quart(__name__, static_folder='static')
    app.secret_key = 'your-secret-key-here'

    # Register the format_number template filter
    @app.template_filter('format_number')
    def format_number_filter(value):
        return format_number(value)

    try:
        pool = await create_database_pool()
        logger.info("Successfully connected to database")
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

    app.db_pool = pool

    # Initialize all blueprint routes
    init_auth_routes(app, pool)
    init_feed_routes(app, pool)
    init_user_routes(app, pool)
    init_media_routes(app, pool)
    init_like_routes(app, pool)
    init_tag_routes(app, pool)

    # Debug route to list all registered routes
    @app.route('/debug/routes')
    async def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
        return jsonify(routes)

    # Log all registered routes
    logger.info("Application routes registered:")
    for rule in app.url_map.iter_rules():
        logger.info(f"Route: {rule.endpoint} -> {rule}")

    return app


async def main():
    try:
        app = await create_app()
        config = Config()
        config.bind = ["[::]:5000"]
        await serve(app, config)
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
