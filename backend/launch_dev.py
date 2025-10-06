"""
Simple development server launcher for CS Gauntlet
Launches the core game functionality without full security stack
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS

# Import basic models and routes
try:
    from backend.models import db, User, Problem, GameMode
    from backend.auth import auth
    from backend.main import main
    MODELS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Models not available: {e}")
    MODELS_AVAILABLE = False

def create_simple_app():
    """Create a simple Flask app for development"""
    
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DEBUG'] = True
    
    # Initialize extensions
    CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000"])
    
    if MODELS_AVAILABLE:
        # Initialize database
        db.init_app(app)
        
        # Initialize login manager
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.login_view = 'auth.login'
        
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        # Register blueprints
        app.register_blueprint(auth)
        app.register_blueprint(main)
        
        # Create database tables and sample data
        with app.app_context():
            db.create_all()
            create_sample_data()
    
    else:
        # Simple fallback routes
        @app.route('/')
        def home():
            return {
                'status': 'CS Gauntlet Development Server',
                'message': 'Backend is running!',
                'frontend_url': 'http://localhost:3000'
            }
        
        @app.route('/health')
        def health():
            return {'status': 'healthy', 'timestamp': str(datetime.utcnow())}
    
    # Basic socket events
    @socketio.on('connect')
    def handle_connect():
        print(f"Client connected")
        socketio.emit('connected', {'status': 'connected'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"Client disconnected")
    
    return app, socketio

def create_sample_data():
    """Create sample data for testing"""
    
    try:
        # Check if we already have data
        if User.query.first():
            print("📊 Sample data already exists")
            return
        
        print("📊 Creating sample data...")
        
        # Create sample users
        users = [
            {'username': 'alice', 'email': 'alice@example.com', 'password': 'password123'},
            {'username': 'bob', 'email': 'bob@example.com', 'password': 'password123'},
            {'username': 'charlie', 'email': 'charlie@example.com', 'password': 'password123'}
        ]
        
        for user_data in users:
            user = User(
                username=user_data['username'],
                email=user_data['email']
            )
            user.set_password(user_data['password'])
            db.session.add(user)
        
        # Create sample problems
        problems = [
            {
                'title': 'Two Sum',
                'description': 'Find two numbers that add up to target',
                'example': 'Input: [2,7,11,15], target=9\nOutput: [0,1]',
                'solution': 'def two_sum(nums, target):\n    # Solution here\n    pass',
                'difficulty': 'easy'
            },
            {
                'title': 'Reverse String',
                'description': 'Reverse a string in-place',
                'example': 'Input: "hello"\nOutput: "olleh"',
                'solution': 'def reverse_string(s):\n    return s[::-1]',
                'difficulty': 'easy'
            }
        ]
        
        for problem_data in problems:
            problem = Problem(**problem_data)
            db.session.add(problem)
        
        db.session.commit()
        print("✅ Sample data created successfully")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")

def main():
    """Main application entry point"""
    
    print("🎮 CS Gauntlet - Development Server")
    print("=" * 40)
    
    try:
        # Create application
        app, socketio = create_simple_app()
        
        print("✅ Application created successfully")
        print(f"🌐 Backend Server: http://localhost:5001")
        print(f"🎯 Frontend Server: http://localhost:3000")
        print(f"📡 WebSocket: ws://localhost:5001")
        
        if MODELS_AVAILABLE:
            print("✅ Database and models loaded")
            print("🔑 Test Credentials:")
            print("   Username: alice    Password: password123")
            print("   Username: bob      Password: password123")
        else:
            print("⚠️  Running in basic mode (models not available)")
        
        print("\n🚀 Starting development server...")
        
        # Run the application
        socketio.run(
            app,
            debug=True,
            host='0.0.0.0',
            port=5001,
            use_reloader=False  # Disable reloader to prevent duplicate processes
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n💥 Server error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    from datetime import datetime
    main()