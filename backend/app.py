#!/usr/bin/env python3
"""
CS Gauntlet - Production Application Launcher
Complete competitive programming platform with AI grading and real-time multiplayer
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend import create_app, socketio, db
from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig

def create_production_app():
    """Create production-ready Flask application"""
    
    # Determine environment
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    if env == 'production':
        config_class = ProductionConfig
    elif env == 'testing':
        config_class = TestingConfig
    else:
        config_class = DevelopmentConfig
    
    # Create app with appropriate config
    app = create_app(config_class)
    
    # Setup logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = logging.handlers.RotatingFileHandler(
            'logs/cs_gauntlet.log', maxBytes=10240000, backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('CS Gauntlet startup')
    
    return app

def initialize_database(app):
    """Initialize database with sample data if needed"""
    with app.app_context():
        try:
            # Create tables
            db.create_all()
            
            # Check if we need to add sample data
            from backend.models import User, Problem, GameMode
            
            if User.query.count() == 0:
                app.logger.info("Adding sample data...")
                
                # Add sample users
                sample_users = [
                    User(username='alice', email='alice@example.com', password_hash='hashed_password'),
                    User(username='bob', email='bob@example.com', password_hash='hashed_password'),
                    User(username='charlie', email='charlie@example.com', password_hash='hashed_password')
                ]
                
                for user in sample_users:
                    db.session.add(user)
                
                # Add game modes
                game_modes = [
                    GameMode(name='casual', description='Casual competitive programming'),
                    GameMode(name='ranked', description='Ranked competitive matches'),
                    GameMode(name='blitz', description='Fast-paced coding challenges'),
                    GameMode(name='practice', description='Practice mode for skill building'),
                    GameMode(name='trivia', description='Programming trivia questions'),
                    GameMode(name='debug', description='Debug challenges'),
                    GameMode(name='custom', description='Custom game settings')
                ]
                
                for mode in game_modes:
                    db.session.add(mode)
                
                # Add sample problems
                sample_problems = [
                    Problem(
                        title="Two Sum",
                        description="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
                        difficulty="easy",
                        test_cases='[{"function": "two_sum", "args": [[2,7,11,15], 9], "expected": [0,1]}, {"function": "two_sum", "args": [[3,2,4], 6], "expected": [1,2]}]'
                    ),
                    Problem(
                        title="Reverse String",
                        description="Write a function that reverses a string. The input string is given as an array of characters s.",
                        difficulty="easy",
                        test_cases='[{"function": "reverse_string", "args": [["h","e","l","l","o"]], "expected": ["o","l","l","e","h"]}]'
                    ),
                    Problem(
                        title="Valid Parentheses",
                        description="Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
                        difficulty="medium",
                        test_cases='[{"function": "is_valid", "args": ["()"], "expected": true}, {"function": "is_valid", "args": ["()[]{}"], "expected": true}, {"function": "is_valid", "args": ["(]"], "expected": false}]'
                    )
                ]
                
                for problem in sample_problems:
                    db.session.add(problem)
                
                db.session.commit()
                app.logger.info("Sample data added successfully")
            
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")
            db.session.rollback()

def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    
    try:
        import redis
        import docker
        import aiohttp
    except ImportError as e:
        missing_deps.append(str(e))
    
    # Check Redis connection
    try:
        from backend import redis_client
        if redis_client:
            redis_client.ping()
    except Exception as e:
        print(f"Warning: Redis not available - {e}")
    
    # Check Docker availability
    try:
        import docker
        client = docker.from_env()
        client.ping()
    except Exception as e:
        print(f"Warning: Docker not available - {e}")
    
    # Check Ollama availability (optional)
    try:
        import aiohttp
        import asyncio
        
        async def check_ollama():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://localhost:11434/api/tags', timeout=aiohttp.ClientTimeout(total=2)) as response:
                        return response.status == 200
            except:
                return False
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ollama_available = loop.run_until_complete(check_ollama())
        loop.close()
        
        if not ollama_available:
            print("Warning: Ollama not available - AI grading will use fallback mode")
    except Exception as e:
        print(f"Warning: Could not check Ollama status - {e}")
    
    if missing_deps:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("Please install missing dependencies with: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main application entry point"""
    print("🎮 Starting CS Gauntlet - Competitive Programming Platform")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create application
    app = create_production_app()
    
    # Initialize database
    initialize_database(app)
    
    # Get configuration
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    print(f"🚀 Environment: {os.getenv('FLASK_ENV', 'development')}")
    print(f"🌐 Server: http://{host}:{port}")
    print(f"🤖 AI Grader: {'Enabled' if app.ai_grader else 'Disabled'}")
    print(f"🔒 Security: {'Enhanced' if hasattr(app, 'security_manager') else 'Basic'}")
    print("=" * 60)
    
    try:
        # Run the application
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            log_output=True
        )
    except KeyboardInterrupt:
        print("\n👋 CS Gauntlet shutting down...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
