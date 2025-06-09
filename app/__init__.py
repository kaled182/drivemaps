from flask import Flask
from dotenv import load_dotenv
import os

load_dotenv()  # Carrega .env localmente

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY')  # Seguro!

    # Registra Blueprints
    from app.routes import main_routes
    app.register_blueprint(main_routes)

    return app