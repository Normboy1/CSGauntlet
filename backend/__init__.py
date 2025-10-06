from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
socketio = SocketIO()
login_manager = LoginManager()

# Initialize OpenAI
import openai
openai.api_key = os.getenv('OPENAI_API_KEY')

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///whos_quicker.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Register blueprints
    from .auth import auth
    from .main import main
    app.register_blueprint(auth)
    app.register_blueprint(main)

    return app
