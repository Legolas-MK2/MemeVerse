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
        next_url = request.args.get('next', url_for('feed.index'))
        if request.method == 'POST':
            try:
                data = await request.form
                username = data.get('username')
                password = data.get('password')

                if await user_service.authenticate_user(username, password):
                    return redirect(next_url)
                else:
                    return await render_template('login.html',
                                               error='Invalid credentials',
                                               navbar_position='nav-bottom',
                                               next=next_url)

            except Exception as e:
                print(f"Login error: {str(e)}")
                return await render_template('login.html',
                                           error='Login failed',
                                           navbar_position='nav-bottom',
                                           next=next_url)

        return await render_template('login.html', navbar_position='nav-bottom', next=next_url)

    @auth_bp.route('/register', methods=['GET', 'POST'])
    async def register():
        next_url = request.args.get('next', url_for('feed.index'))
        if request.method == 'POST':
            try:
                data = await request.form
                username = data.get('username')
                password = data.get('password')

                success, error = await user_service.register_user(username, password)
                if success:
                    return redirect(next_url)
                else:
                    return await render_template('register.html',
                                               error=error,
                                               navbar_position='nav-bottom',
                                               next=next_url)
            except Exception as e:
                print(f"Registration error: {str(e)}")
                return await render_template('register.html',
                                           error='Registration failed',
                                           navbar_position='nav-bottom',
                                           next=next_url)

        return await render_template('register.html', navbar_position='nav-bottom', next=next_url)
        
    app.register_blueprint(auth_bp)
