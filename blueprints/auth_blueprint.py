from quart import Blueprint, render_template, request, redirect, url_for, session
from services.user_service import UserService


auth_bp = Blueprint('auth', __name__)


def init_auth_routes(app, pool):
    user_service = UserService(pool)
    
    @auth_bp.before_request
    async def ensure_user_id():
        await user_service.ensure_user_id()

    @auth_bp.route('/login', methods=['GET', 'POST'])
    async def login():
        if request.method == 'POST':
            try:
                data = await request.form
                username = data.get('username')
                password = data.get('password')
                
                if await user_service.authenticate_user(username, password):
                    return redirect(url_for('feed.index'))
                else:
                    return await render_template('login.html', 
                                               error='Invalid credentials',
                                               navbar_position='nav-bottom')
                    
            except Exception as e:
                print(f"Login error: {str(e)}")
                return await render_template('login.html', 
                                           error='Login failed',
                                           navbar_position='nav-bottom')
                
        return await render_template('login.html', navbar_position='nav-bottom')

    @auth_bp.route('/register', methods=['GET', 'POST'])
    async def register():
        if request.method == 'POST':
            try:
                data = await request.form
                username = data.get('username')
                password = data.get('password')
                
                success, error = await user_service.register_user(username, password)
                if success:
                    return redirect(url_for('feed.index'))
                else:
                    return await render_template('register.html', 
                                               error=error,
                                               navbar_position='nav-bottom')
            except Exception as e:
                print(f"Registration error: {str(e)}")
                return await render_template('register.html', 
                                           error='Registration failed',
                                           navbar_position='nav-bottom')
        
        return await render_template('register.html', navbar_position='nav-bottom')
        
    app.register_blueprint(auth_bp)
