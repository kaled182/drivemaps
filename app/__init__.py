from flask import Flask
from flask_session import Session

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'sua_senha_super_secreta'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB upload

    Session(app)
    from .routes import main_routes
    app.register_blueprint(main_routes)

    return app
