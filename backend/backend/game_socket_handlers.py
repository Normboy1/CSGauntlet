"""
Socket event handlers for CS Gauntlet game functionality
Properly integrated with GameManager and security features
"""

from flask_socketio import emit, join_room, leave_room, rooms
from flask_login import current_user
from flask import request
from datetime import datetime
import json

from . import socketio, db
from .models import User, GameMode
from .game_manager import game_manager, GameConfig, GameState


# Track connected users
connected_users = set()
user_games = {}  # socket_id -> game_id mapping


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    connected_users.add(client_id)
    
    emit('connected', {
        'status': 'connected',
        'client_id': client_id,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Send current stats
    emit('server_stats', {
        'online_users': len(connected_users),
        'active_games': game_manager.get_active_games_count(),
        'matchmaking_queue': game_manager.get_matchmaking_stats()
    })
    
    print(f"Client {client_id} connected. Total: {len(connected_users)}")


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    
    # Remove from connected users
    connected_users.discard(client_id)
    
    # Handle game disconnection
    if client_id in user_games:
        game_id = user_games[client_id]
        game = game_manager.get_game(game_id)
        
        if game:
            game.remove_player(client_id)
            
            # Notify other players
            emit('player_disconnected', {
                'player_id': client_id,
                'timestamp': datetime.utcnow().isoformat()
            }, room=f"game_{game_id}")
        
        del user_games[client_id]
    
    # Cancel any pending matchmaking
    if current_user.is_authenticated:
        game_manager.cancel_matchmaking(current_user.id, client_id)
    
    print(f"Client {client_id} disconnected. Total: {len(connected_users)}")


@socketio.on('join_home')
def handle_join_home():
    """Handle joining home page"""
    emit('server_stats', {
        'online_users': len(connected_users),
        'active_games': game_manager.get_active_games_count(),
        'matchmaking_queue': game_manager.get_matchmaking_stats()
    })


@socketio.on('find_match')
def handle_find_match(data):
    """Handle matchmaking request"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    game_mode = data.get('game_mode', 'casual')
    language = data.get('language', 'python')
    
    # Validate game mode
    try:
        GameMode(game_mode)
    except ValueError:
        emit('error', {'message': 'Invalid game mode'})
        return
    
    # Validate language
    valid_languages = ['python', 'javascript', 'java', 'cpp', 'c']
    if language not in valid_languages:
        emit('error', {'message': 'Invalid language'})
        return
    
    client_id = request.sid
    
    # Find or create match
    found_match, message, game_id = game_manager.find_or_create_match(
        user_id=current_user.id,
        socket_id=client_id,
        username=current_user.username,
        game_mode=game_mode,
        language=language,
        avatar_url=getattr(current_user, 'avatar_url', None),
        college=getattr(current_user, 'college_name', None)
    )
    
    if found_match and game_id:
        # Match found, join game
        user_games[client_id] = game_id
        join_room(f"game_{game_id}")
        
        game = game_manager.get_game(game_id)
        
        emit('match_found', {
            'game_id': game_id,
            'message': message,
            'game_state': game.get_state()
        })
        
        # Notify all players in the game
        emit('game_updated', {
            'game_state': game.get_state()
        }, room=f"game_{game_id}")
        
    else:
        # Added to queue
        emit('matchmaking_status', {
            'status': 'searching',
            'message': message,
            'position_in_queue': len(game_manager.matchmaking_queue.get(game_mode, []))
        })


@socketio.on('cancel_matchmaking')
def handle_cancel_matchmaking():
    """Handle canceling matchmaking"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    client_id = request.sid
    success = game_manager.cancel_matchmaking(current_user.id, client_id)
    
    if success:
        emit('matchmaking_cancelled', {'message': 'Matchmaking cancelled'})
    else:
        emit('error', {'message': 'No active matchmaking found'})


@socketio.on('create_custom_game')
def handle_create_custom_game(data):
    """Handle creating a custom game"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    try:
        # Parse game configuration
        game_mode = data.get('game_mode', 'custom')
        max_players = min(int(data.get('max_players', 2)), 8)  # Limit to 8 players
        max_rounds = min(int(data.get('max_rounds', 3)), 10)  # Limit to 10 rounds
        time_limit = min(int(data.get('time_limit', 1800)), 7200)  # Max 2 hours
        language = data.get('language', 'python')
        difficulty = data.get('difficulty', 'medium')
        allow_spectators = bool(data.get('allow_spectators', True))
        
        config = GameConfig(
            mode=GameMode(game_mode),
            max_players=max_players,
            max_rounds=max_rounds,
            time_limit=time_limit,
            language=language,
            difficulty=difficulty,
            allow_spectators=allow_spectators,
            auto_start=False  # Custom games require manual start
        )
        
        game_id = game_manager.create_game(current_user.id, config)
        
        emit('game_created', {
            'game_id': game_id,
            'config': data,
            'message': 'Custom game created successfully'
        })
        
    except ValueError as e:
        emit('error', {'message': f'Invalid configuration: {str(e)}'})
    except Exception as e:
        emit('error', {'message': 'Failed to create game'})


@socketio.on('join_game')
def handle_join_game(data):
    """Handle joining a specific game"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    game_id = data.get('game_id')
    if not game_id:
        emit('error', {'message': 'Game ID required'})
        return
    
    client_id = request.sid
    
    success, message = game_manager.join_game(
        game_id=game_id,
        user_id=current_user.id,
        socket_id=client_id,
        username=current_user.username,
        avatar_url=getattr(current_user, 'avatar_url', None),
        college=getattr(current_user, 'college_name', None)
    )
    
    if success:
        user_games[client_id] = game_id
        join_room(f"game_{game_id}")
        
        game = game_manager.get_game(game_id)
        
        emit('game_joined', {
            'game_id': game_id,
            'message': message,
            'game_state': game.get_state()
        })
        
        # Notify all players
        emit('player_joined', {
            'player': {
                'user_id': current_user.id,
                'username': current_user.username,
                'avatar_url': getattr(current_user, 'avatar_url', None)
            },
            'game_state': game.get_state()
        }, room=f"game_{game_id}")
        
    else:
        emit('error', {'message': message})


@socketio.on('leave_game')
def handle_leave_game(data):
    """Handle leaving a game"""
    client_id = request.sid
    
    if client_id not in user_games:
        emit('error', {'message': 'Not in a game'})
        return
    
    game_id = user_games[client_id]
    success = game_manager.leave_game(game_id, client_id)
    
    if success:
        leave_room(f"game_{game_id}")
        del user_games[client_id]
        
        emit('game_left', {'message': 'Left game successfully'})
        
        # Notify other players
        emit('player_left', {
            'player_id': client_id,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"game_{game_id}")
    else:
        emit('error', {'message': 'Failed to leave game'})


@socketio.on('start_game')
def handle_start_game(data):
    """Handle manually starting a game"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    client_id = request.sid
    
    if client_id not in user_games:
        emit('error', {'message': 'Not in a game'})
        return
    
    game_id = user_games[client_id]
    game = game_manager.get_game(game_id)
    
    if not game:
        emit('error', {'message': 'Game not found'})
        return
    
    # Check if user is the creator
    if game.creator_user_id != current_user.id:
        emit('error', {'message': 'Only game creator can start the game'})
        return
    
    success = game.start_game()
    
    if success:
        # Notify all players that game has started
        emit('game_started', {
            'game_state': game.get_state(),
            'message': 'Game started!'
        }, room=f"game_{game_id}")
        
        # Start first round
        if game.rounds:
            emit('new_round', {
                'round_number': game.current_round,
                'problem': game.rounds[-1].problem,
                'time_limit': game.config.round_time_limit
            }, room=f"game_{game_id}")
    else:
        emit('error', {'message': 'Unable to start game'})


@socketio.on('submit_solution')
def handle_submit_solution(data):
    """Handle solution submission"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    client_id = request.sid
    
    if client_id not in user_games:
        emit('error', {'message': 'Not in a game'})
        return
    
    code = data.get('code', '').strip()
    language = data.get('language', 'python')
    
    if not code:
        emit('error', {'message': 'Code cannot be empty'})
        return
    
    if len(code) > 50000:  # 50KB limit
        emit('error', {'message': 'Code too large'})
        return
    
    game_id = user_games[client_id]
    game = game_manager.get_game(game_id)
    
    if not game:
        emit('error', {'message': 'Game not found'})
        return
    
    success, message = game.submit_solution(client_id, code, language)
    
    if success:
        emit('solution_submitted', {
            'message': message,
            'round': game.current_round,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Notify other players (without showing the code)
        emit('player_submitted', {
            'player_id': client_id,
            'username': current_user.username,
            'round': game.current_round,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"game_{game_id}", include_self=False)
        
        # Check if round is complete
        current_round = game.rounds[-1] if game.rounds else None
        if current_round and len(current_round.submissions) >= len(game.players):
            # Emit round complete with AI grading results
            round_data = {
                'round': game.current_round,
                'game_state': game.get_state(),
                'submissions': {}
            }
            
            # Include AI grading results for each submission
            for socket_id, submission in current_round.submissions.items():
                if 'ai_grading' in submission:
                    player = game.players.get(socket_id)
                    if player:
                        round_data['submissions'][socket_id] = {
                            'username': player.username,
                            'ai_grading': submission['ai_grading'],
                            'score': player.score
                        }
            
            emit('round_complete', round_data, room=f"game_{game_id}")
            
            # Also emit individual AI grading results to each player
            for socket_id, submission in current_round.submissions.items():
                if 'ai_grading' in submission:
                    emit('ai_grading_result', {
                        'round': game.current_round,
                        'grading': submission['ai_grading'],
                        'your_score': game.players[socket_id].score if socket_id in game.players else 0
                    }, room=socket_id)
    else:
        emit('error', {'message': message})


@socketio.on('spectate_game')
def handle_spectate_game(data):
    """Handle spectating a game"""
    game_id = data.get('game_id')
    
    if not game_id:
        emit('error', {'message': 'Game ID required'})
        return
    
    game = game_manager.get_game(game_id)
    
    if not game:
        emit('error', {'message': 'Game not found'})
        return
    
    client_id = request.sid
    username = current_user.username if current_user.is_authenticated else 'Anonymous'
    user_id = current_user.id if current_user.is_authenticated else None
    
    success = game.add_spectator(client_id, user_id, username)
    
    if success:
        join_room(f"game_{game_id}")
        
        emit('spectating_started', {
            'game_id': game_id,
            'game_state': game.get_state(),
            'message': 'Now spectating game'
        })
        
        # Notify players of new spectator
        emit('spectator_joined', {
            'username': username,
            'spectators_count': len(game.spectators)
        }, room=f"game_{game_id}", include_self=False)
    else:
        emit('error', {'message': 'Cannot spectate this game'})


@socketio.on('stop_spectating')
def handle_stop_spectating(data):
    """Handle stopping spectating"""
    game_id = data.get('game_id')
    
    if not game_id:
        emit('error', {'message': 'Game ID required'})
        return
    
    game = game_manager.get_game(game_id)
    client_id = request.sid
    
    if game and game.remove_spectator(client_id):
        leave_room(f"game_{game_id}")
        
        emit('spectating_stopped', {'message': 'Stopped spectating'})
        
        # Notify players
        emit('spectator_left', {
            'spectators_count': len(game.spectators)
        }, room=f"game_{game_id}")
    else:
        emit('error', {'message': 'Not spectating this game'})


@socketio.on('get_game_state')
def handle_get_game_state(data):
    """Handle getting current game state"""
    game_id = data.get('game_id')
    
    if not game_id:
        emit('error', {'message': 'Game ID required'})
        return
    
    game = game_manager.get_game(game_id)
    
    if game:
        emit('game_state', game.get_state())
    else:
        emit('error', {'message': 'Game not found'})


@socketio.on('send_chat_message')
def handle_chat_message(data):
    """Handle in-game chat messages"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    client_id = request.sid
    
    if client_id not in user_games:
        emit('error', {'message': 'Not in a game'})
        return
    
    message = data.get('message', '').strip()
    
    if not message:
        emit('error', {'message': 'Message cannot be empty'})
        return
    
    if len(message) > 200:
        emit('error', {'message': 'Message too long'})
        return
    
    game_id = user_games[client_id]
    
    # Basic profanity filter (expand as needed)
    banned_words = ['spam', 'cheat', 'hack']  # Add more as needed
    if any(word in message.lower() for word in banned_words):
        emit('error', {'message': 'Message contains inappropriate content'})
        return
    
    chat_message = {
        'id': f"msg_{datetime.utcnow().timestamp()}",
        'user_id': current_user.id,
        'username': current_user.username,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'avatar_url': getattr(current_user, 'avatar_url', None)
    }
    
    # Broadcast to game room
    emit('chat_message', chat_message, room=f"game_{game_id}")


@socketio.on('request_hint')
def handle_request_hint(data):
    """Handle hint requests during game"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Authentication required'})
        return
    
    client_id = request.sid
    
    if client_id not in user_games:
        emit('error', {'message': 'Not in a game'})
        return
    
    game_id = user_games[client_id]
    game = game_manager.get_game(game_id)
    
    if not game or game.state != GameState.IN_PROGRESS:
        emit('error', {'message': 'No active game'})
        return
    
    # For now, provide a generic hint
    # In production, this would be based on the current problem
    hints = [
        "Think about the time complexity of your solution",
        "Consider edge cases like empty inputs",
        "Break the problem down into smaller steps",
        "Look for patterns in the examples",
        "Consider using built-in data structures"
    ]
    
    import random
    hint = random.choice(hints)
    
    emit('hint_provided', {
        'hint': hint,
        'timestamp': datetime.utcnow().isoformat()
    })


# Periodic cleanup task (would be better as a background job)
def cleanup_games():
    """Clean up inactive games periodically"""
    game_manager.cleanup_inactive_games()


# Helper function to broadcast server stats
def broadcast_server_stats():
    """Broadcast current server statistics"""
    socketio.emit('server_stats', {
        'online_users': len(connected_users),
        'active_games': game_manager.get_active_games_count(),
        'matchmaking_queue': game_manager.get_matchmaking_stats(),
        'timestamp': datetime.utcnow().isoformat()
    })


# Error handler for socket events
@socketio.on_error_default
def default_error_handler(e):
    """Handle socket errors"""
    print(f"Socket error: {e}")
    emit('error', {'message': 'An unexpected error occurred'})