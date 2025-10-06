from datetime import datetime
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db
import re
import os

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

class LanguageEnum(str, Enum):
    PYTHON = 'python'
    JAVA = 'java'
    JAVASCRIPT = 'javascript'
    C = 'c'
    CPP = 'cpp'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    university = db.Column(db.String(120))
    github_username = db.Column(db.String(80))
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(200))
    profile_photo = db.Column(db.String(255), default='default-avatar.png')
    college_logo = db.Column(db.String(255), default='default-college.png')
    college_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scores = db.relationship('Score', backref='user', lazy=True)
    oauth_tokens = db.relationship('OAuth', backref='oauth_user', lazy=True)

    @staticmethod
    def is_valid_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_stats(self, game_mode=None):
        """Get statistics for a specific game mode or all games"""
        if game_mode:
            scores = Score.query.filter_by(user_id=self.id, game_mode=game_mode).all()
        else:
            scores = Score.query.filter_by(user_id=self.id).all()

        total_games = len(scores)
        wins = sum(1 for score in scores if score.is_win)
        losses = total_games - wins

        win_rate = (wins / total_games) * 100 if total_games > 0 else 0
        return {
            'total_games': total_games,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate
        }

class OAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    token = db.Column(db.Text, nullable=False)
    provider_user_id = db.Column(db.String(256), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    language = db.Column(db.String(20), nullable=False)
    is_win = db.Column(db.Boolean, default=False)
    game_mode = db.Column(db.Enum(GameMode), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def update_stats(self, is_win):
        self.is_win = is_win
        db.session.commit()

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    example = db.Column(db.Text, nullable=False)
    solution = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.String(20), default='easy')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'example': self.example,
            'solution': self.solution, # Note: Solution should not be sent to frontend in production
            'difficulty': self.difficulty,
            'created_at': self.created_at.isoformat()
        }

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    code = db.Column(db.Text, nullable=False)
    grading_result = db.Column(db.JSON) # Store JSON directly
    points_earned = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'problem_id': self.problem_id,
            'code': self.code,
            'grading_result': self.grading_result,
            'points_earned': self.points_earned,
            'timestamp': self.timestamp.isoformat()
        }

class GameModeDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    time_limit = db.Column(db.Integer) # in seconds
    max_players = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'time_limit': self.time_limit,
            'max_players': self.max_players
        }

class TriviaQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)  # List of strings
    correct_answer_index = db.Column(db.Integer, nullable=False) # 0-indexed
    difficulty = db.Column(db.String(20), default='easy')
    category = db.Column(db.String(50))
    explanation = db.Column(db.Text)
    points = db.Column(db.Integer, default=10)

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'options': self.options,
            'correct_answer': self.correct_answer_index, # Frontend might not need this
            'difficulty': self.difficulty,
            'category': self.category,
            'explanation': self.explanation,
            'points': self.points
        }

class DebugChallenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    buggy_code = db.Column(db.Text, nullable=False)
    expected_output = db.Column(db.Text)
    language = db.Column(db.String(20), default='python')
    difficulty = db.Column(db.String(20), default='easy')
    bugs = db.Column(db.JSON) # List of bug dicts
    hints = db.Column(db.JSON) # List of strings
    total_points = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'buggy_code': self.buggy_code,
            'expected_output': self.expected_output,
            'language': self.language,
            'difficulty': self.difficulty,
            'bugs': self.bugs,
            'hints': self.hints,
            'total_points': self.total_points
        }
