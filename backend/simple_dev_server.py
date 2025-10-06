"""
Simple development server for CS Gauntlet
Basic Flask server without complex dependencies
"""

import os
import sys
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO
# from flask_cors import CORS  # Using manual CORS headers instead
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func, text
from werkzeug.utils import secure_filename
import uuid

def create_app():
    """Create a simple Flask app for development"""
    
    app = Flask(__name__)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # File upload configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'profile_pics')
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Manual CORS configuration for development
    # This ensures CORS headers are always added
    
    # Initialize database
    db = SQLAlchemy(app)
    
    # Simple CORS headers for development - allow everything
    @app.after_request
    def after_request(response):
        print(f"Adding CORS headers to response for {request.path}")
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = '*'
        response.headers['Access-Control-Allow-Methods'] = '*'
        response.headers['X-Debug-CORS'] = 'added-by-after-request'
        print(f"CORS headers added: {dict(response.headers)}")
        return response
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    # Define database models
    from enum import Enum
    from werkzeug.security import generate_password_hash, check_password_hash
    
    class GameMode(str, Enum):
        CLASSIC = 'classic'
        CUSTOM = 'custom'
        BLITZ = 'blitz'
        PRACTICE = 'practice'
        RANKED = 'ranked'
        CASUAL = 'casual'
        TRIVIA = 'trivia'
        DEBUG = 'debug'
        ELECTRICAL = 'electrical'
    
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False, index=True)
        password_hash = db.Column(db.String(128))
        university = db.Column(db.String(120))
        college_name = db.Column(db.String(100))
        profile_picture = db.Column(db.String(255))  # Store filename/path
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        scores = db.relationship('Score', backref='user', lazy=True)
        
        def set_password(self, password):
            self.password_hash = generate_password_hash(password)
        
        def check_password(self, password):
            return check_password_hash(self.password_hash, password)
        
        def get_stats(self, game_mode=None):
            if game_mode:
                scores = Score.query.filter_by(user_id=self.id, game_mode=game_mode).all()
            else:
                scores = Score.query.filter_by(user_id=self.id).all()
            
            total_games = len(scores)
            wins = sum(1 for score in scores if score.is_win)
            win_rate = (wins / total_games) * 100 if total_games > 0 else 0
            
            return {
                'total_games': total_games,
                'wins': wins,
                'win_rate': win_rate
            }
    
    class Score(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        language = db.Column(db.String(20), nullable=False)
        is_win = db.Column(db.Boolean, default=False)
        game_mode = db.Column(db.Enum(GameMode), nullable=False)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)
        points = db.Column(db.Integer, default=0)
    
    # Create tables and handle migrations
    with app.app_context():
        try:
            db.create_all()
            # Test if profile_picture column exists by trying to query it
            try:
                User.query.with_entities(User.profile_picture).first()
            except Exception:
                # Column doesn't exist - add it manually
                print("Adding profile_picture column to User table...")
                with db.engine.connect() as connection:
                    connection.execute(text('ALTER TABLE user ADD COLUMN profile_picture VARCHAR(255)'))
                    connection.commit()
                print("Profile picture column added successfully!")
        except Exception as e:
            print(f"Database setup error: {e}")
            print("Creating fresh database...")
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            if os.path.exists(db_path):
                os.remove(db_path)
            db.create_all()
        
        # Create sample data if database is empty
        try:
            user_count = User.query.count()
        except Exception:
            user_count = 0
        
        if user_count == 0:
            print("Creating sample users and scores...")
            
            # Create sample users
            users_data = [
                {'username': 'alice', 'email': 'alice@mit.edu', 'password': 'password123', 'college_name': 'MIT'},
                {'username': 'bob', 'email': 'bob@stanford.edu', 'password': 'password123', 'college_name': 'Stanford'},
                {'username': 'charlie', 'email': 'charlie@berkeley.edu', 'password': 'password123', 'college_name': 'UC Berkeley'},
                {'username': 'diana', 'email': 'diana@cmu.edu', 'password': 'password123', 'college_name': 'Carnegie Mellon'},
                {'username': 'eve', 'email': 'eve@harvard.edu', 'password': 'password123', 'college_name': 'Harvard'},
            ]
            
            for user_data in users_data:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    college_name=user_data['college_name']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
            
            db.session.commit()
            
            # Create sample scores
            import random
            users = User.query.all()
            for user in users:
                # Generate random scores for each user
                num_games = random.randint(10, 35)
                for i in range(num_games):
                    score = Score(
                        user_id=user.id,
                        language='python',
                        is_win=random.choice([True, False]),
                        game_mode=random.choice(list(GameMode)),
                        points=random.randint(50, 200)
                    )
                    db.session.add(score)
            
            db.session.commit()
            print("Sample data created!")
    
    # Basic routes
    @app.route('/')
    def home():
        return jsonify({
            'status': 'CS Gauntlet Development Server',
            'message': 'Backend is running!',
            'timestamp': datetime.utcnow().isoformat(),
            'frontend_url': 'http://localhost:3000',
            'version': '1.0.0-dev'
        })
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'healthy', 
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': 'running'
        })
    
    @app.route('/api/test-cors')
    def test_cors():
        response = jsonify({'message': 'CORS test endpoint', 'status': 'working'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        return response

    @app.route('/api/status')
    def api_status():
        return jsonify({
            'api_status': 'active',
            'endpoints': [
                'GET /',
                'GET /health', 
                'GET /api/status',
                'POST /api/auth/login',
                'POST /api/auth/register',
                'GET /api/profile',
                'GET /api/leaderboard',
                'WebSocket /socket.io/'
            ],
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Basic authentication endpoints for development
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        try:
            data = request.get_json()
            
            username = data.get('username') or data.get('email', '')
            password = data.get('password', '')
            
            if not username or not password:
                return jsonify({'error': 'Username and password required'}), 400
            
            # Check if user exists in database
            user = User.query.filter_by(username=username).first()
            if not user:
                # For development, if user doesn't exist, still allow login
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'user': {
                        'id': 999,
                        'username': username,
                        'email': f"{username}@example.com"
                    },
                    'token': f'dev-token-{username}'
                })
            
            # For development, don't check password, just allow login
            # In production, you would use: user.check_password(password)
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                },
                'token': f'dev-token-{user.username}'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        try:
            data = request.get_json()
            
            username = data.get('username', '')
            email = data.get('email', '')
            password = data.get('password', '')
            
            if not all([username, email, password]):
                return jsonify({'error': 'Username, email, and password required'}), 400
            
            # Mock successful registration
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': {
                    'id': 1,
                    'username': username,
                    'email': email
                }
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def get_user_from_token(token):
        """Extract username from development token"""
        if token.startswith('dev-token-'):
            return token.replace('dev-token-', '')
        return None
    
    @app.route('/api/profile', methods=['GET'])
    def profile():
        try:
            # Check for authorization header
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization required'}), 401
            
            # Extract token and get username
            token = auth_header.replace('Bearer ', '')
            username = get_user_from_token(token)
            
            if not username:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Get user from database
            user = User.query.filter_by(username=username).first()
            if not user:
                # If user doesn't exist in database, return mock data for development
                return jsonify({
                    'username': username,
                    'email': f'{username}@example.com',
                    'college': 'Dev University',
                    'userRank': 'Coding Novice',
                    'totalScore': 1200,
                    'gamesPlayed': 0,
                    'winRate': 0.0,
                    'rank': 99,
                    'profilePicture': None
                })
            
            # Get user statistics
            stats = user.get_stats()
            total_games = stats['total_games']
            wins = stats['wins']
            win_rate = stats['win_rate']
            
            # Calculate rating and rank title
            base_rating = 1200
            if user.username.lower() == "normbeezy":
                rating = 999999
            else:
                rating = base_rating + (wins * 50) + int(win_rate * 5)
            
            rank_title = get_rank_title(rating, total_games, user.username)
            
            # Calculate rank position (simplified - could be more sophisticated)
            all_users = User.query.all()
            user_ratings = []
            for u in all_users:
                u_stats = u.get_stats()
                if u.username.lower() == "normbeezy":
                    u_rating = 999999
                else:
                    u_rating = base_rating + (u_stats['wins'] * 50) + int(u_stats['win_rate'] * 5)
                user_ratings.append((u.username, u_rating))
            
            # Sort by rating and find user's rank
            user_ratings.sort(key=lambda x: x[1], reverse=True)
            user_rank = next((i + 1 for i, (username, _) in enumerate(user_ratings) if username == user.username), 1)
            
            # Return profile data in the format frontend expects
            profile_picture_url = None
            if user.profile_picture:
                profile_picture_url = f'/api/profile/picture/{user.profile_picture}'
            
            return jsonify({
                'username': user.username,
                'email': user.email,
                'college': user.college_name or 'Unknown',
                'userRank': rank_title,
                'totalScore': rating,
                'gamesPlayed': total_games,
                'winRate': round(win_rate, 1),
                'rank': user_rank,
                'profilePicture': profile_picture_url
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def allowed_file(filename):
        """Check if the uploaded file is an allowed image type"""
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    
    @app.route('/api/profile/test-upload', methods=['GET'])
    def test_upload():
        return jsonify({'message': 'Upload route is working'})
    
    @app.route('/api/profile/upload-picture', methods=['POST'])
    def upload_profile_picture():
        try:
            # Check authorization
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization required'}), 401
            
            token = auth_header.replace('Bearer ', '')
            username = get_user_from_token(token)
            
            if not username:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Check if file is in request
            if 'file' not in request.files:
                return jsonify({'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Only PNG, JPG, JPEG, GIF, and WebP are allowed'}), 400
            
            # Generate unique filename
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{username}_{uuid.uuid4().hex[:8]}.{file_extension}"
            
            # Save file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Update user's profile picture in database
            user = User.query.filter_by(username=username).first()
            if user:
                # Remove old profile picture file if it exists
                if user.profile_picture:
                    old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)
                
                user.profile_picture = unique_filename
                db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Profile picture uploaded successfully',
                'filename': unique_filename,
                'url': f'/api/profile/picture/{unique_filename}'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/profile/picture/<filename>')
    def get_profile_picture(filename):
        """Serve profile pictures"""
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    @app.route('/api/profile/delete-picture', methods=['DELETE'])
    def delete_profile_picture():
        try:
            # Check authorization
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authorization required'}), 401
            
            token = auth_header.replace('Bearer ', '')
            username = get_user_from_token(token)
            
            if not username:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Get user from database
            user = User.query.filter_by(username=username).first()
            if not user or not user.profile_picture:
                return jsonify({'error': 'No profile picture to delete'}), 400
            
            # Remove file from filesystem
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Update database
            user.profile_picture = None
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Profile picture deleted successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    def get_rank_title(rating, games_played, username=None):
        """Determine rank title based on rating and experience"""
        # Special case for Creator
        if username and username.lower() == "normbeezy":
            return "Creator"
        elif games_played == 0:
            return "Keyboard Warrior"
        elif rating >= 2500:
            return "Coding Sage"
        elif rating >= 2200:
            return "Code Virtuoso"
        elif rating >= 2000:
            return "Coding Master"
        elif rating >= 1800:
            return "Code Ninja"
        elif rating >= 1600:
            return "Algorithm Ace"
        elif rating >= 1400:
            return "Logic Lord"
        elif rating >= 1200:
            return "Coding Novice"
        elif rating >= 1000:
            return "Vibe Coder"
        elif rating >= 800:
            return "Script Kiddie"
        else:
            return "Debug Dummy"
    
    @app.route('/api/leaderboard', methods=['GET', 'OPTIONS'])
    def leaderboard():
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            response = app.make_default_options_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET,OPTIONS'
            return response
        try:
            # Get all users with their stats from the database
            users = User.query.all()
            leaderboard_data = []
            
            for user in users:
                stats = user.get_stats()
                
                # Calculate rating based on wins, games played, and performance
                base_rating = 1200
                wins = stats['wins']
                total_games = stats['total_games']
                win_rate = stats['win_rate']
                
                # Special case for Creator - infinite rating
                if user.username.lower() == "normbeezy":
                    rating = 999999  # Use a very high number instead of infinity for JSON compatibility
                else:
                    # Simple rating calculation: base + wins*50 + win_rate bonus
                    rating = base_rating + (wins * 50) + int(win_rate * 5)
                
                # Get rank title
                rank_title = get_rank_title(rating, total_games, user.username)
                
                leaderboard_data.append({
                    'username': user.username,
                    'rating': rating,
                    'rank_title': rank_title,
                    'games_played': total_games,
                    'win_rate': round(win_rate, 1),
                    'college': user.college_name or 'Unknown'
                })
            
            # Sort by rating (highest first)
            leaderboard_data.sort(key=lambda x: x['rating'], reverse=True)
            
            # Create response with explicit CORS headers
            response = jsonify(leaderboard_data)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
            response.headers['Access-Control-Allow-Methods'] = 'GET,OPTIONS'
            response.headers['Access-Control-Max-Age'] = '86400'
            return response
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/clear-database', methods=['POST'])
    def clear_database():
        try:
            # Delete all scores first (due to foreign key constraints)
            Score.query.delete()
            
            # Delete all users
            User.query.delete()
            
            # Commit the changes
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Database cleared successfully',
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/create-sample-data', methods=['POST'])
    def create_sample_data_endpoint():
        try:
            # Create diverse sample users with different skill levels
            import random
            
            users_data = [
                {'username': 'codewizard', 'email': 'wizard@mit.edu', 'password': 'password123', 'college_name': 'MIT', 'skill': 'expert'},
                {'username': 'algorithmancer', 'email': 'algo@stanford.edu', 'password': 'password123', 'college_name': 'Stanford', 'skill': 'advanced'},
                {'username': 'debugger_pro', 'email': 'debug@berkeley.edu', 'password': 'password123', 'college_name': 'UC Berkeley', 'skill': 'intermediate'},
                {'username': 'novice_ninja', 'email': 'novice@cmu.edu', 'password': 'password123', 'college_name': 'Carnegie Mellon', 'skill': 'beginner'},
                {'username': 'vibe_master', 'email': 'vibe@harvard.edu', 'password': 'password123', 'college_name': 'Harvard', 'skill': 'casual'},
                {'username': 'script_hero', 'email': 'script@caltech.edu', 'password': 'password123', 'college_name': 'Caltech', 'skill': 'learning'},
            ]
            
            for user_data in users_data:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    college_name=user_data['college_name']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
            
            db.session.commit()
            
            # Create varied scores based on skill level
            users = User.query.all()
            skill_profiles = {
                'expert': {'games': (40, 60), 'win_rate': (0.8, 0.95)},
                'advanced': {'games': (25, 40), 'win_rate': (0.65, 0.8)},
                'intermediate': {'games': (15, 30), 'win_rate': (0.45, 0.65)},
                'beginner': {'games': (8, 20), 'win_rate': (0.3, 0.5)},
                'casual': {'games': (5, 15), 'win_rate': (0.4, 0.6)},
                'learning': {'games': (3, 10), 'win_rate': (0.2, 0.4)},
            }
            
            for i, user in enumerate(users):
                skill = list(skill_profiles.keys())[i % len(skill_profiles)]
                profile = skill_profiles[skill]
                
                num_games = random.randint(*profile['games'])
                target_win_rate = random.uniform(*profile['win_rate'])
                
                for j in range(num_games):
                    is_win = random.random() < target_win_rate
                    score = Score(
                        user_id=user.id,
                        language='python',
                        is_win=is_win,
                        game_mode=random.choice(list(GameMode)),
                        points=random.randint(100, 300) if is_win else random.randint(20, 80)
                    )
                    db.session.add(score)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Sample data with varied skill levels created successfully',
                'users_created': len(users_data)
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/game/debug/challenges', methods=['GET'])
    def get_debug_challenges():
        try:
            # Mock debug challenges data
            challenges = [
                {
                    'id': 1,
                    'title': 'Array Index Out of Bounds',
                    'difficulty': 'Easy',
                    'language': 'python',
                    'code': '''def find_max(arr):
    max_val = arr[0]
    for i in range(1, len(arr) + 1):  # Bug: should be len(arr)
        if arr[i] > max_val:
            max_val = arr[i]
    return max_val

# Test
numbers = [1, 5, 3, 9, 2]
print(find_max(numbers))''',
                    'bug_line': 3,
                    'explanation': 'The loop goes beyond array bounds. Should be len(arr) instead of len(arr) + 1'
                },
                {
                    'id': 2,
                    'title': 'Infinite Loop',
                    'difficulty': 'Medium',
                    'language': 'python',
                    'code': '''def countdown(n):
    while n > 0:
        print(n)
        # Bug: forgot to decrement n
    print("Done!")

countdown(5)''',
                    'bug_line': 4,
                    'explanation': 'Missing n -= 1 or n = n - 1 to decrement the counter'
                },
                {
                    'id': 3,
                    'title': 'Division by Zero',
                    'difficulty': 'Easy',
                    'language': 'python',
                    'code': '''def calculate_average(numbers):
    total = sum(numbers)
    count = len(numbers)
    return total / count  # Bug: what if count is 0?

# Test with empty list
result = calculate_average([])
print(result)''',
                    'bug_line': 4,
                    'explanation': 'Need to check if count > 0 before dividing to avoid division by zero'
                }
            ]
            
            return jsonify({
                'success': True,
                'challenges': challenges
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/game/trivia/questions', methods=['GET'])
    def get_trivia_questions():
        try:
            # Comprehensive trivia questions data
            questions = [
                {
                    'id': 1,
                    'question': 'What does "CPU" stand for?',
                    'options': ['Central Processing Unit', 'Computer Personal Unit', 'Central Program Unit', 'Computer Processing Unit'],
                    'correctAnswer': 0,
                    'difficulty': 'Easy',
                    'category': 'Hardware'
                },
                {
                    'id': 2,
                    'question': 'Which programming language was developed by Guido van Rossum?',
                    'options': ['Java', 'Python', 'C++', 'JavaScript'],
                    'correctAnswer': 1,
                    'difficulty': 'Easy',
                    'category': 'Programming'
                },
                {
                    'id': 3,
                    'question': 'What is the time complexity of bubble sort in the worst case?',
                    'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(log n)'],
                    'correctAnswer': 2,
                    'difficulty': 'Medium',
                    'category': 'Algorithms'
                },
                {
                    'id': 4,
                    'question': 'Which data structure uses LIFO (Last In, First Out) principle?',
                    'options': ['Queue', 'Stack', 'Array', 'Linked List'],
                    'correctAnswer': 1,
                    'difficulty': 'Easy',
                    'category': 'Data Structures'
                },
                {
                    'id': 5,
                    'question': 'What does "SQL" stand for?',
                    'options': ['Simple Query Language', 'Structured Query Language', 'Standard Query Language', 'System Query Language'],
                    'correctAnswer': 1,
                    'difficulty': 'Easy',
                    'category': 'Database'
                },
                {
                    'id': 6,
                    'question': 'Which of the following is NOT a programming paradigm?',
                    'options': ['Object-Oriented', 'Functional', 'Procedural', 'Algorithmic'],
                    'correctAnswer': 3,
                    'difficulty': 'Medium',
                    'category': 'Programming'
                },
                {
                    'id': 7,
                    'question': 'What is the maximum number of comparisons needed to find an element in a sorted array of 1000 elements using binary search?',
                    'options': ['10', '100', '500', '1000'],
                    'correctAnswer': 0,
                    'difficulty': 'Medium',
                    'category': 'Algorithms'
                },
                {
                    'id': 8,
                    'question': 'Which HTTP status code indicates "Not Found"?',
                    'options': ['200', '301', '404', '500'],
                    'correctAnswer': 2,
                    'difficulty': 'Easy',
                    'category': 'Web Development'
                },
                {
                    'id': 9,
                    'question': 'In Object-Oriented Programming, what does "polymorphism" mean?',
                    'options': ['Having multiple constructors', 'Ability to take multiple forms', 'Having multiple inheritance', 'Having multiple methods'],
                    'correctAnswer': 1,
                    'difficulty': 'Medium',
                    'category': 'Programming'
                },
                {
                    'id': 10,
                    'question': 'Which sorting algorithm has the best average-case time complexity?',
                    'options': ['Bubble Sort', 'Selection Sort', 'Merge Sort', 'Insertion Sort'],
                    'correctAnswer': 2,
                    'difficulty': 'Medium',
                    'category': 'Algorithms'
                },
                {
                    'id': 11,
                    'question': 'What does "RAM" stand for?',
                    'options': ['Random Access Memory', 'Rapid Access Memory', 'Read Access Memory', 'Real Access Memory'],
                    'correctAnswer': 0,
                    'difficulty': 'Easy',
                    'category': 'Hardware'
                },
                {
                    'id': 12,
                    'question': 'Which of these is a NoSQL database?',
                    'options': ['MySQL', 'PostgreSQL', 'MongoDB', 'SQLite'],
                    'correctAnswer': 2,
                    'difficulty': 'Easy',
                    'category': 'Database'
                },
                {
                    'id': 13,
                    'question': 'What is the space complexity of a recursive implementation of Fibonacci sequence?',
                    'options': ['O(1)', 'O(n)', 'O(n²)', 'O(2^n)'],
                    'correctAnswer': 1,
                    'difficulty': 'Hard',
                    'category': 'Algorithms'
                },
                {
                    'id': 14,
                    'question': 'Which design pattern ensures a class has only one instance?',
                    'options': ['Factory', 'Observer', 'Singleton', 'Strategy'],
                    'correctAnswer': 2,
                    'difficulty': 'Medium',
                    'category': 'Software Engineering'
                },
                {
                    'id': 15,
                    'question': 'What does "API" stand for?',
                    'options': ['Application Programming Interface', 'Applied Programming Interface', 'Advanced Programming Interface', 'Automated Programming Interface'],
                    'correctAnswer': 0,
                    'difficulty': 'Easy',
                    'category': 'Software Engineering'
                },
                {
                    'id': 16,
                    'question': 'Which protocol is used for secure web communication?',
                    'options': ['HTTP', 'FTP', 'HTTPS', 'SSH'],
                    'correctAnswer': 2,
                    'difficulty': 'Easy',
                    'category': 'Networking'
                },
                {
                    'id': 17,
                    'question': 'In a binary tree with n nodes, what is the maximum height?',
                    'options': ['log(n)', 'n', 'n-1', '2^n'],
                    'correctAnswer': 2,
                    'difficulty': 'Medium',
                    'category': 'Data Structures'
                },
                {
                    'id': 18,
                    'question': 'Which of the following is NOT a valid variable name in most programming languages?',
                    'options': ['_variable', 'variable1', '1variable', 'VARIABLE'],
                    'correctAnswer': 2,
                    'difficulty': 'Easy',
                    'category': 'Programming'
                },
                {
                    'id': 19,
                    'question': 'What is the output of this JavaScript code: console.log(typeof null)?',
                    'options': ['null', 'undefined', 'object', 'boolean'],
                    'correctAnswer': 2,
                    'difficulty': 'Hard',
                    'category': 'Programming'
                },
                {
                    'id': 20,
                    'question': 'Which data structure is best for implementing a LRU (Least Recently Used) cache?',
                    'options': ['Array', 'Stack', 'Hash Map + Doubly Linked List', 'Binary Tree'],
                    'correctAnswer': 2,
                    'difficulty': 'Hard',
                    'category': 'Data Structures'
                }
            ]
            
            return jsonify({
                'success': True,
                'questions': questions
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/create_custom_game', methods=['POST'])
    def create_custom_game():
        try:
            data = request.get_json()
            
            # Mock game creation
            game_id = f"game_{random.randint(1000, 9999)}"
            
            return jsonify({
                'success': True,
                'game_id': game_id,
                'message': 'Custom game created successfully',
                'game_settings': {
                    'mode': data.get('gameMode', 'custom'),
                    'time_limit': data.get('timeLimit', 15),
                    'difficulty': data.get('difficulty', 'medium'),
                    'max_players': data.get('maxPlayers', 2)
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/join_custom_game', methods=['POST'])
    def join_custom_game():
        try:
            data = request.get_json()
            game_id = data.get('gameId')
            
            if not game_id:
                return jsonify({'success': False, 'error': 'Game ID required'}), 400
            
            # Mock game joining
            return jsonify({
                'success': True,
                'message': f'Joined game {game_id} successfully',
                'game_id': game_id,
                'players': [
                    {'username': 'You', 'id': 'user_1'},
                    {'username': 'Player2', 'id': 'user_2'}
                ]
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/leaderboard/detailed', methods=['GET'])
    def get_detailed_leaderboard():
        try:
            period = request.args.get('period', 'all_time')
            type_filter = request.args.get('type', 'overall')
            
            # Use the same leaderboard data but with additional details
            users = User.query.all()
            leaderboard_data = []
            
            for user in users:
                stats = user.get_stats()
                
                base_rating = 1200
                wins = stats['wins']
                total_games = stats['total_games']
                win_rate = stats['win_rate']
                
                if user.username.lower() == "normbeezy":
                    rating = 999999
                else:
                    rating = base_rating + (wins * 50) + int(win_rate * 5)
                
                rank_title = get_rank_title(rating, total_games, user.username)
                
                leaderboard_data.append({
                    'username': user.username,
                    'rating': rating,
                    'rank_title': rank_title,
                    'games_played': total_games,
                    'win_rate': round(win_rate, 1),
                    'college': user.college_name or 'Unknown',
                    'recent_games': random.randint(0, 5),
                    'streak': random.randint(0, 8),
                    'average_time': f"{random.randint(8, 15)}:{random.randint(10, 59)}"
                })
            
            leaderboard_data.sort(key=lambda x: x['rating'], reverse=True)
            
            return jsonify({
                'success': True,
                'leaderboard': leaderboard_data,
                'period': period,
                'type': type_filter
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/admin/add-creator', methods=['POST'])
    def add_creator():
        try:
            # Check if Normbeezy already exists
            existing_user = User.query.filter_by(username='Normbeezy').first()
            if existing_user:
                return jsonify({
                    'success': False,
                    'message': 'Creator user already exists'
                }), 400
            
            # Create Creator user
            creator = User(
                username='Normbeezy',
                email='normbeezy@ohiostate.edu',
                college_name='Ohio State'
            )
            creator.set_password('Norm4356')
            db.session.add(creator)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Creator user added successfully',
                'user': {
                    'username': 'Normbeezy',
                    'rank': 'Creator',
                    'rating': '∞ (999999)',
                    'college': 'Ohio State'
                }
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    # Enhanced socket events for chat and game functionality
    @socketio.on('connect')
    def handle_connect():
        print(f"Client connected: {request.sid} at {datetime.utcnow()}")
        socketio.emit('connected', {
            'status': 'connected',
            'message': 'Welcome to CS Gauntlet!',
            'timestamp': datetime.utcnow().isoformat(),
            'client_id': request.sid
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"Client disconnected: {request.sid} at {datetime.utcnow()}")
    
    @socketio.on('join_room')
    def handle_join_room(data):
        room = data.get('room')
        if room:
            print(f"Client {request.sid} joining room: {room}")
            socketio.join_room(room)
            socketio.emit('room_joined', {
                'room': room,
                'message': f'Joined room {room}',
                'timestamp': datetime.utcnow().isoformat()
            })
    
    @socketio.on('leave_room')
    def handle_leave_room(data):
        room = data.get('room')
        if room:
            print(f"Client {request.sid} leaving room: {room}")
            socketio.leave_room(room)
            socketio.emit('room_left', {
                'room': room,
                'message': f'Left room {room}',
                'timestamp': datetime.utcnow().isoformat()
            })
    
    @socketio.on('send_message')
    def handle_send_message(data):
        room = data.get('room', 'general')
        message = data.get('message', '')
        username = data.get('username', 'Anonymous')
        
        if message.strip():
            message_data = {
                'id': f"msg_{random.randint(1000, 9999)}",
                'username': username,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'room': room
            }
            
            print(f"Broadcasting message to room {room}: {message}")
            socketio.emit('new_message', message_data, room=room)
    
    @socketio.on('start_game')
    def handle_start_game(data):
        game_id = data.get('game_id', f"game_{random.randint(1000, 9999)}")
        game_mode = data.get('game_mode', 'classic')
        
        print(f"Starting game {game_id} with mode {game_mode}")
        socketio.emit('game_started', {
            'game_id': game_id,
            'game_mode': game_mode,
            'message': f'Game {game_id} started!',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('submit_solution')
    def handle_submit_solution(data):
        game_id = data.get('game_id')
        solution = data.get('solution', '')
        username = data.get('username', 'Anonymous')
        
        print(f"Solution submitted for game {game_id} by {username}")
        
        # Mock solution evaluation
        is_correct = random.choice([True, False])
        points = random.randint(50, 200) if is_correct else 0
        
        socketio.emit('solution_result', {
            'game_id': game_id,
            'username': username,
            'is_correct': is_correct,
            'points': points,
            'message': 'Solution correct!' if is_correct else 'Try again!',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('game_action')
    def handle_game_action(data):
        action = data.get('action')
        game_id = data.get('game_id')
        username = data.get('username', 'Anonymous')
        
        print(f"Game action '{action}' in game {game_id} by {username}")
        
        socketio.emit('game_update', {
            'action': action,
            'game_id': game_id,
            'username': username,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    @socketio.on('test_event')
    def handle_test_event(data):
        print(f"Received test event: {data}")
        socketio.emit('test_response', {
            'message': 'Test event received successfully',
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    return app, socketio

def main():
    """Main application entry point"""
    
    print("CS Gauntlet - Development Server")
    print("=" * 40)
    
    try:
        # Create application
        app, socketio = create_app()
        
        print("Application created successfully")
        print("Backend Server: http://localhost:5010")
        print("Frontend Server: http://localhost:3003") 
        print("WebSocket: ws://localhost:5010")
        print("")
        print("Available endpoints:")
        print("  GET  /           - Server status")
        print("  GET  /health     - Health check") 
        print("  GET  /api/status - API status")
        print("  WS   /socket.io/ - WebSocket connection")
        print("")
        print("Starting development server...")
        
        # Run the application
        socketio.run(
            app,
            debug=True,
            host='0.0.0.0',
            port=5010,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"\nServer error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()