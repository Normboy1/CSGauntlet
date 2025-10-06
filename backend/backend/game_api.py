"""
Comprehensive Game API Routes for CS Gauntlet
Handles all game-related API endpoints including matchmaking, game management, and AI grading
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from .auth import jwt_required
from .models import User, Problem, Submission, Score, GameMode, db
from .game_manager import GameManager, GameConfig, GameState
from .code_executor import CodeExecutor
from . import redis_client, ai_grader
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

game_api = Blueprint('game_api', __name__, url_prefix='/api/game')

# Initialize game manager
game_manager = GameManager(redis_client)

@game_api.route('/health', methods=['GET'])
def game_health():
    """Check game system health"""
    return jsonify({
        'status': 'ok',
        'redis_connected': redis_client.ping() if redis_client else False,
        'ai_grader_available': ai_grader is not None,
        'active_games': len(game_manager.get_active_games()) if game_manager else 0
    })

@game_api.route('/matchmaking/find', methods=['POST'])
@jwt_required
def find_match():
    """Find a match for the current user"""
    try:
        data = request.json or {}
        game_mode = data.get('mode', 'casual')
        difficulty = data.get('difficulty', 'medium')
        language = data.get('language', 'python')
        max_players = data.get('max_players', 2)
        
        # Validate input
        valid_modes = ['casual', 'ranked', 'blitz', 'practice', 'trivia', 'debug']
        if game_mode not in valid_modes:
            return jsonify({'error': f'Invalid game mode. Must be one of: {valid_modes}'}), 400
        
        # Create game config
        config = GameConfig(
            mode=GameMode.query.filter_by(name=game_mode).first() or GameMode(name=game_mode),
            max_players=max_players,
            difficulty=difficulty,
            language=language,
            time_limit=1800,  # 30 minutes
            round_time_limit=300  # 5 minutes per round
        )
        
        # Try to find existing game or create new one
        game_id = game_manager.find_or_create_game(
            user_id=current_user.id,
            socket_id=request.headers.get('X-Socket-ID', str(uuid.uuid4())),
            username=current_user.username,
            config=config
        )
        
        if game_id:
            game = game_manager.get_game(game_id)
            return jsonify({
                'success': True,
                'game_id': game_id,
                'game_state': game.state.value,
                'players': len(game.players),
                'max_players': game.config.max_players,
                'message': 'Match found!' if len(game.players) >= 2 else 'Waiting for more players...'
            })
        else:
            return jsonify({'error': 'Failed to find or create game'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in find_match: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/create_custom', methods=['POST'])
@jwt_required
def create_custom_game():
    """Create a custom game with specific settings"""
    try:
        data = request.json or {}
        settings = data.get('settings', {})
        
        # Create game config from settings
        config = GameConfig(
            mode=GameMode.query.filter_by(name='custom').first() or GameMode(name='custom'),
            max_players=settings.get('maxPlayers', 2),
            time_limit=settings.get('timeLimit', 900),
            difficulty=settings.get('difficulty', 'medium'),
            language=settings.get('language', 'python'),
            allow_spectators=True,
            auto_start=False
        )
        
        # Create the game
        game_id = game_manager.create_game(
            creator_user_id=current_user.id,
            config=config
        )
        
        # Add creator as first player
        game = game_manager.get_game(game_id)
        success = game.add_player(
            user_id=current_user.id,
            socket_id=request.headers.get('X-Socket-ID', str(uuid.uuid4())),
            username=current_user.username,
            avatar_url=getattr(current_user, 'avatar_url', None),
            college=getattr(current_user, 'college_name', None)
        )
        
        if success:
            game.save_state()
            return jsonify({
                'success': True,
                'game': {
                    'id': game_id,
                    'state': game.state.value,
                    'players': len(game.players),
                    'max_players': game.config.max_players,
                    'settings': settings
                }
            })
        else:
            return jsonify({'error': 'Failed to add creator to game'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error creating custom game: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/join_custom', methods=['POST'])
@jwt_required
def join_custom_game():
    """Join a custom game by ID"""
    try:
        data = request.json or {}
        game_id = data.get('game_id')
        
        if not game_id:
            return jsonify({'error': 'Game ID is required'}), 400
        
        game = game_manager.get_game(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        # Try to add player to game
        success = game.add_player(
            user_id=current_user.id,
            socket_id=request.headers.get('X-Socket-ID', str(uuid.uuid4())),
            username=current_user.username,
            avatar_url=getattr(current_user, 'avatar_url', None),
            college=getattr(current_user, 'college_name', None)
        )
        
        if success:
            game.save_state()
            return jsonify({
                'success': True,
                'game_id': game_id,
                'message': 'Successfully joined game'
            })
        else:
            return jsonify({'error': 'Failed to join game (may be full or already started)'}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error joining custom game: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/<game_id>/state', methods=['GET'])
@jwt_required
def get_game_state(game_id):
    """Get current game state"""
    try:
        game = game_manager.get_game(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        # Check if user is participant or spectator
        user_socket = request.headers.get('X-Socket-ID')
        is_player = any(p.user_id == current_user.id for p in game.players.values())
        is_spectator = user_socket in game.spectators
        
        if not (is_player or is_spectator):
            return jsonify({'error': 'Not authorized to view this game'}), 403
        
        return jsonify({
            'success': True,
            'game': {
                'id': game.game_id,
                'state': game.state.value,
                'current_round': game.current_round,
                'max_rounds': game.config.max_rounds,
                'players': [
                    {
                        'user_id': p.user_id,
                        'username': p.username,
                        'score': p.score,
                        'status': p.status.value,
                        'avatar_url': p.avatar_url,
                        'college': p.college
                    } for p in game.players.values()
                ],
                'spectators': len(game.spectators),
                'time_remaining': game.get_time_remaining() if hasattr(game, 'get_time_remaining') else None,
                'current_problem': game.get_current_problem() if hasattr(game, 'get_current_problem') else None
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting game state: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/<game_id>/submit_solution', methods=['POST'])
@jwt_required
def submit_solution(game_id):
    """Submit a code solution for the current round"""
    try:
        data = request.json or {}
        code = data.get('code', '').strip()
        language = data.get('language', 'python')
        
        if not code:
            return jsonify({'error': 'Code is required'}), 400
        
        game = game_manager.get_game(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        # Check if user is a player in this game
        player = next((p for p in game.players.values() if p.user_id == current_user.id), None)
        if not player:
            return jsonify({'error': 'You are not a player in this game'}), 403
        
        if game.state != GameState.IN_PROGRESS:
            return jsonify({'error': 'Game is not in progress'}), 400
        
        # Get current problem
        current_problem = game.get_current_problem() if hasattr(game, 'get_current_problem') else None
        if not current_problem:
            return jsonify({'error': 'No active problem'}), 400
        
        # Execute and grade the code
        executor = CodeExecutor()
        
        # Run in async context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success, message, test_results, grading_result = loop.run_until_complete(
                executor.validate_and_grade_solution(code, current_problem)
            )
        finally:
            loop.close()
        
        # Calculate points based on grading
        base_points = 100
        time_bonus = game.calculate_time_bonus() if hasattr(game, 'calculate_time_bonus') else 1.0
        quality_multiplier = grading_result.criteria.total / 100
        final_points = int(base_points * quality_multiplier * time_bonus)
        
        # Update player score
        player.score += final_points
        player.submissions.append({
            'code': code,
            'language': language,
            'timestamp': datetime.utcnow().isoformat(),
            'points': final_points,
            'grading_result': {
                'total_score': grading_result.criteria.total,
                'grade': grading_result.overall_grade,
                'feedback': grading_result.feedback
            }
        })
        
        # Save submission to database
        submission = Submission(
            user_id=current_user.id,
            problem_id=current_problem.get('id'),
            code=code,
            language=language,
            points_earned=final_points,
            grading_result=json.dumps({
                'criteria': {
                    'correctness': grading_result.criteria.correctness,
                    'efficiency': grading_result.criteria.efficiency,
                    'readability': grading_result.criteria.readability,
                    'style': grading_result.criteria.style,
                    'innovation': grading_result.criteria.innovation,
                    'total': grading_result.criteria.total
                },
                'feedback': grading_result.feedback,
                'overall_grade': grading_result.overall_grade
            }),
            submitted_at=datetime.utcnow()
        )
        db.session.add(submission)
        db.session.commit()
        
        # Update game state
        game.save_state()
        
        return jsonify({
            'success': True,
            'submission_id': submission.id,
            'points_earned': final_points,
            'test_results': test_results,
            'grading': {
                'criteria': {
                    'correctness': grading_result.criteria.correctness,
                    'efficiency': grading_result.criteria.efficiency,
                    'readability': grading_result.criteria.readability,
                    'style': grading_result.criteria.style,
                    'innovation': grading_result.criteria.innovation,
                    'total': grading_result.criteria.total
                },
                'feedback': grading_result.feedback,
                'suggestions': grading_result.suggestions,
                'overall_grade': grading_result.overall_grade,
                'rank_percentile': grading_result.rank_percentile
            },
            'message': message,
            'player_score': player.score
        })
        
    except Exception as e:
        current_app.logger.error(f"Error submitting solution: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/<game_id>/spectate', methods=['POST'])
@jwt_required
def spectate_game(game_id):
    """Join a game as a spectator"""
    try:
        game = game_manager.get_game(game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        if not game.config.allow_spectators:
            return jsonify({'error': 'Spectating not allowed for this game'}), 403
        
        socket_id = request.headers.get('X-Socket-ID', str(uuid.uuid4()))
        
        # Add as spectator
        game.spectators[socket_id] = {
            'user_id': current_user.id,
            'username': current_user.username,
            'joined_at': datetime.utcnow().isoformat()
        }
        
        game.save_state()
        
        return jsonify({
            'success': True,
            'message': 'Successfully joined as spectator',
            'game_state': game.state.value,
            'players': len(game.players),
            'spectators': len(game.spectators)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error joining as spectator: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/active', methods=['GET'])
@jwt_required
def get_active_games():
    """Get list of active games"""
    try:
        active_games = game_manager.get_active_games()
        
        games_list = []
        for game in active_games:
            games_list.append({
                'id': game.game_id,
                'state': game.state.value,
                'mode': game.config.mode.name if hasattr(game.config.mode, 'name') else 'unknown',
                'players': len(game.players),
                'max_players': game.config.max_players,
                'spectators': len(game.spectators),
                'allow_spectators': game.config.allow_spectators,
                'difficulty': game.config.difficulty,
                'language': game.config.language,
                'created_at': game.created_at.isoformat() if game.created_at else None
            })
        
        return jsonify({
            'success': True,
            'games': games_list,
            'total_count': len(games_list)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting active games: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/problems', methods=['GET'])
def get_problems():
    """Get available coding problems"""
    try:
        difficulty = request.args.get('difficulty', 'all')
        topic = request.args.get('topic', 'all')
        limit = int(request.args.get('limit', 50))
        
        query = Problem.query
        
        if difficulty != 'all':
            query = query.filter_by(difficulty=difficulty)
        
        if topic != 'all':
            # Assuming there's a topic field in Problem model
            query = query.filter_by(topic=topic)
        
        problems = query.limit(limit).all()
        
        return jsonify({
            'success': True,
            'problems': [
                {
                    'id': p.id,
                    'title': p.title,
                    'description': p.description,
                    'difficulty': p.difficulty,
                    'topic': getattr(p, 'topic', 'general'),
                    'test_cases': json.loads(p.test_cases) if hasattr(p, 'test_cases') else [],
                    'constraints': getattr(p, 'constraints', ''),
                    'examples': json.loads(p.examples) if hasattr(p, 'examples') else []
                } for p in problems
            ],
            'total_count': len(problems)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting problems: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/leaderboard', methods=['GET'])
def get_game_leaderboard():
    """Get game leaderboard with rankings"""
    try:
        time_period = request.args.get('period', 'all')  # all, week, month
        game_mode = request.args.get('mode', 'all')      # all, casual, ranked, etc.
        limit = int(request.args.get('limit', 50))
        
        # Base query for user scores
        query = db.session.query(
            User.id,
            User.username,
            User.college_name,
            db.func.sum(Score.points).label('total_points'),
            db.func.count(Score.id).label('games_played'),
            db.func.sum(db.case([(Score.is_win == True, 1)], else_=0)).label('wins'),
            db.func.avg(Score.points).label('avg_points')
        ).join(Score, User.id == Score.user_id)
        
        # Apply filters
        if time_period == 'week':
            week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.filter(Score.created_at >= week_ago)
        elif time_period == 'month':
            month_ago = datetime.utcnow() - timedelta(days=30)
            query = query.filter(Score.created_at >= month_ago)
        
        if game_mode != 'all':
            # Assuming Score has a game_mode field
            query = query.filter(Score.game_mode == game_mode)
        
        # Group and order
        leaderboard_data = query.group_by(User.id, User.username, User.college_name)\
                               .order_by(db.desc('total_points'))\
                               .limit(limit)\
                               .all()
        
        # Format results
        leaderboard = []
        for i, (user_id, username, college, total_points, games_played, wins, avg_points) in enumerate(leaderboard_data):
            win_rate = (wins / games_played * 100) if games_played > 0 else 0
            
            leaderboard.append({
                'rank': i + 1,
                'user_id': user_id,
                'username': username,
                'college': college or 'Unknown',
                'total_points': int(total_points) if total_points else 0,
                'games_played': int(games_played) if games_played else 0,
                'wins': int(wins) if wins else 0,
                'win_rate': round(win_rate, 1),
                'avg_points': round(float(avg_points), 1) if avg_points else 0.0
            })
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'period': time_period,
            'mode': game_mode,
            'total_count': len(leaderboard)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting leaderboard: {e}")
        return jsonify({'error': str(e)}), 500

@game_api.route('/stats/user', methods=['GET'])
@jwt_required
def get_user_stats():
    """Get detailed statistics for the current user"""
    try:
        user_id = current_user.id
        
        # Get basic stats
        total_games = Score.query.filter_by(user_id=user_id).count()
        total_wins = Score.query.filter_by(user_id=user_id, is_win=True).count()
        total_points = db.session.query(db.func.sum(Score.points)).filter_by(user_id=user_id).scalar() or 0
        
        # Get recent submissions
        recent_submissions = Submission.query.filter_by(user_id=user_id)\
                                           .order_by(Submission.submitted_at.desc())\
                                           .limit(10)\
                                           .all()
        
        # Calculate win rate
        win_rate = (total_wins / total_games * 100) if total_games > 0 else 0
        
        # Get favorite language
        language_stats = db.session.query(
            Submission.language,
            db.func.count(Submission.id).label('count')
        ).filter_by(user_id=user_id)\
         .group_by(Submission.language)\
         .order_by(db.desc('count'))\
         .first()
        
        favorite_language = language_stats[0] if language_stats else 'python'
        
        return jsonify({
            'success': True,
            'stats': {
                'total_games': total_games,
                'total_wins': total_wins,
                'total_points': int(total_points),
                'win_rate': round(win_rate, 1),
                'favorite_language': favorite_language,
                'recent_submissions': [
                    {
                        'id': s.id,
                        'problem_id': s.problem_id,
                        'language': s.language,
                        'points_earned': s.points_earned,
                        'submitted_at': s.submitted_at.isoformat() if s.submitted_at else None
                    } for s in recent_submissions
                ]
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user stats: {e}")
        return jsonify({'error': str(e)}), 500

# Error handlers
@game_api.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@game_api.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
