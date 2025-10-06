from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from flask_login import current_user
from . import socketio, db
from .models import Score, GameMode
import random
import json
from datetime import datetime

# Track connected users and matchmaking status
connected_users = set()
matchmaking_users = set()

# Track game chat rooms and users
game_chat_rooms = {}  # {game_id: {users: [], messages: []}}
user_typing_status = {}  # {user_id: {game_id: game_id, is_typing: bool}}

class Problem:
    def __init__(self, title, description, solution):
        self.title = title
        self.description = description
        self.solution = solution

# Sample problems (in a real app, these would come from a database)
PROBLEMS = [
    Problem(
        "Reverse String",
        "Write a function that takes a string and returns it reversed.",
        "def reverse_string(s):\n    return s[::-1]"
    ),
    Problem(
        "Fibonacci",
        "Write a function that returns the nth Fibonacci number.",
        "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)"
    ),
    Problem(
        "Palindrome Checker",
        "Write a function that checks if a word is a palindrome.",
        "def is_palindrome(word):\n    return word == word[::-1]"
    )
]

class Match:
    def __init__(self, match_id, player1, game_mode, language):
        self.id = match_id
        self.player1 = player1
        self.player2 = None
        self.game_mode = game_mode
        self.language = language
        self.created_at = datetime.utcnow()
        self.timeout = 300  # 5 minutes timeout

matches = {}
match_queue = []
games = {}

# Chat-related socket events
@socketio.on('join_game_chat')
def handle_join_game_chat(data):
    """Handle user joining a game chat room"""
    game_id = data.get('gameId')
    user_id = data.get('userId')
    username = data.get('username')
    game_mode = data.get('gameMode', 'unknown')
    
    if not game_id or not user_id or not username:
        emit('error', {'message': 'Missing required chat data'})
        return
    
    # Join the socket room
    join_room(f"game_chat_{game_id}")
    
    # Initialize game chat room if it doesn't exist
    if game_id not in game_chat_rooms:
        game_chat_rooms[game_id] = {
            'users': [],
            'messages': [],
            'created_at': datetime.utcnow().isoformat(),
            'game_mode': game_mode
        }
    
    # Add user to the game chat room
    user_info = {
        'userId': user_id,
        'username': username,
        'socketId': request.sid,
        'joinedAt': datetime.utcnow().isoformat()
    }
    
    # Check if user is already in the room
    existing_user = next((u for u in game_chat_rooms[game_id]['users'] if u['userId'] == user_id), None)
    
    if not existing_user:
        game_chat_rooms[game_id]['users'].append(user_info)
        
        # Notify other users in the room
        emit('user_joined', {
            'userId': user_id,
            'username': username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"game_chat_{game_id}", include_self=False)
        
        print(f"User {username} joined game chat {game_id}")
    else:
        # Update socket ID for existing user
        existing_user['socketId'] = request.sid
        print(f"User {username} reconnected to game chat {game_id}")
    
    # Send chat history to the joining user
    emit('chat_history', {
        'messages': game_chat_rooms[game_id]['messages'][-50:],  # Last 50 messages
        'users': [{'userId': u['userId'], 'username': u['username']} for u in game_chat_rooms[game_id]['users']]
    })

@socketio.on('leave_game_chat')
def handle_leave_game_chat(data):
    """Handle user leaving a game chat room"""
    game_id = data.get('gameId')
    user_id = data.get('userId')
    username = data.get('username')
    
    if not game_id or not user_id:
        return
    
    # Leave the socket room
    leave_room(f"game_chat_{game_id}")
    
    # Remove user from the game chat room
    if game_id in game_chat_rooms:
        game_chat_rooms[game_id]['users'] = [
            u for u in game_chat_rooms[game_id]['users'] 
            if u['userId'] != user_id
        ]
        
        # Notify other users in the room
        emit('user_left', {
            'userId': user_id,
            'username': username,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"game_chat_{game_id}", include_self=False)
        
        print(f"User {username} left game chat {game_id}")
        
        # Clean up empty rooms
        if not game_chat_rooms[game_id]['users']:
            del game_chat_rooms[game_id]
            print(f"Game chat room {game_id} cleaned up")
    
    # Clean up typing status
    if user_id in user_typing_status:
        del user_typing_status[user_id]

@socketio.on('send_chat_message')
def handle_send_chat_message(data):
    """Handle sending a chat message"""
    game_id = data.get('gameId')
    message = data.get('message')
    user_id = data.get('userId')
    username = data.get('username')
    
    if not all([game_id, message, user_id, username]):
        emit('error', {'message': 'Missing required message data'})
        return
    
    # Validate message length and content
    if len(message.strip()) == 0:
        emit('error', {'message': 'Message cannot be empty'})
        return
    
    if len(message) > 200:
        emit('error', {'message': 'Message too long'})
        return
    
    # Create message object
    chat_message = {
        'id': f"msg_{game_id}_{datetime.utcnow().timestamp()}",
        'userId': user_id,
        'username': username,
        'message': message.strip(),
        'timestamp': datetime.utcnow().isoformat(),
        'type': 'message'
    }
    
    # Store message in game chat room
    if game_id in game_chat_rooms:
        game_chat_rooms[game_id]['messages'].append(chat_message)
        
        # Keep only last 100 messages to prevent memory issues
        if len(game_chat_rooms[game_id]['messages']) > 100:
            game_chat_rooms[game_id]['messages'] = game_chat_rooms[game_id]['messages'][-100:]
    
    # Broadcast message to all users in the room
    emit('chat_message', chat_message, room=f"game_chat_{game_id}")
    
    print(f"Chat message from {username} in game {game_id}: {message}")

@socketio.on('user_typing')
def handle_user_typing(data):
    """Handle user typing indicators"""
    game_id = data.get('gameId')
    user_id = data.get('userId')
    username = data.get('username')
    is_typing = data.get('isTyping', False)
    
    if not all([game_id, user_id, username]):
        return
    
    # Update typing status
    if is_typing:
        user_typing_status[user_id] = {
            'game_id': game_id,
            'is_typing': True,
            'timestamp': datetime.utcnow().isoformat()
        }
    else:
        if user_id in user_typing_status:
            del user_typing_status[user_id]
    
    # Broadcast typing status to other users in the room
    emit('user_typing', {
        'userId': user_id,
        'username': username,
        'isTyping': is_typing,
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"game_chat_{game_id}", include_self=False)

@socketio.on('get_chat_users')
def handle_get_chat_users(data):
    """Get list of users in a chat room"""
    game_id = data.get('gameId')
    
    if not game_id:
        emit('error', {'message': 'Missing game ID'})
        return
    
    if game_id in game_chat_rooms:
        users = [
            {'userId': u['userId'], 'username': u['username']} 
            for u in game_chat_rooms[game_id]['users']
        ]
        emit('chat_users', {'users': users})
    else:
        emit('chat_users', {'users': []})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection"""
    user_socket_id = request.sid
    
    # Find and remove user from all game chat rooms
    for game_id, room_data in list(game_chat_rooms.items()):
        for user in room_data['users']:
            if user['socketId'] == user_socket_id:
                # Remove user from room
                room_data['users'] = [u for u in room_data['users'] if u['socketId'] != user_socket_id]
                
                # Notify other users
                emit('user_left', {
                    'userId': user['userId'],
                    'username': user['username'],
                    'timestamp': datetime.utcnow().isoformat()
                }, room=f"game_chat_{game_id}")
                
                # Clean up typing status
                if user['userId'] in user_typing_status:
                    del user_typing_status[user['userId']]
                
                print(f"User {user['username']} disconnected from game chat {game_id}")
                break
        
        # Clean up empty rooms
        if not room_data['users']:
            del game_chat_rooms[game_id]
            print(f"Game chat room {game_id} cleaned up after disconnect")
    
    # Remove from connected users
    if user_socket_id in connected_users:
        connected_users.remove(user_socket_id)
    
    print(f"User with socket {user_socket_id} disconnected")

def update_player_counts():
    """Update the player count for all connected users"""
    emit('player_count', {
        'online': len(connected_users),
        'matchmaking': len(matchmaking_users)
    }, broadcast=True)

def find_match_for_player(player_id, game_mode, language):
    """Find a suitable match for the player"""
    # Check if there's a waiting match with matching criteria
    for match in match_queue[:]:
        if match.game_mode == game_mode and match.language == language:
            match.player2 = player_id
            matches[match.id] = match
            match_queue.remove(match)
            return match.id
    
    # No match found, create a new one and add to queue
    match_id = str(random.randint(100000, 999999))
    new_match = Match(match_id, player_id, game_mode, language)
    match_queue.append(new_match)
    return None

@socketio.on('connect')
def handle_connect():
    connected_users.add(request.sid)
    update_player_counts()
    emit('connected', {'data': 'Connected to server'})

@socketio.on('join_home')
def handle_join_home():
    update_player_counts()

@socketio.on('find_match')
def handle_find_match(data):
    game_mode = data.get('game_mode', 'casual')
    language = data.get('language', 'python')
    
    matchmaking_users.add(request.sid)
    update_player_counts()
    
    match_id = find_match_for_player(request.sid, game_mode, language)
    
    if match_id:
        emit('match_found', {'match_id': match_id})
    else:
        emit('match_status', {'status': 'searching'})

@socketio.on('start_match')
def handle_start_match(data):
    match_id = data.get('match_id')
    
    if match_id not in matches:
        emit('error', {'message': 'Invalid match ID'})
        return
    
    match = matches[match_id]
    
    # Create game for both players
    game_id = str(random.randint(100000, 999999))
    games[game_id] = {
        'players': {
            match.player1: {
                'username': current_user.username,
                'score': 0
            },
            match.player2: {
                'username': current_user.username,
                'score': 0
            }
        },
        'round': 1,
        'max_rounds': 3,
        'game_mode': match.game_mode,
        'scores': {},
        'current_problem': None, # Initialize current_problem
        'submissions': {} # Initialize submissions
    }
    
    # Send game state to both players
    emit('game_state', {
        'is_spectator': False,
        'players': 2
    }, room=match.player1)
    
    emit('game_state', {
        'is_spectator': False,
        'players': 2
    }, room=match.player2)
    
    # Start first round
    start_new_round(game_id)

@socketio.on('cancel_match')
def handle_cancel_match():
    # Remove player from any waiting matches
    matchmaking_users.discard(request.sid)
    update_player_counts()
    
    for match in match_queue[:]:
        if match.player1 == request.sid:
            match_queue.remove(match)
            emit('match_canceled')
            break

@socketio.on('spectate')
def handle_spectate():
    # Find an active game to spectate
    for game_id, game in games.items():
        if len(game['players']) == 2:  # Only allow spectating when there are 2 players
            game['players'][request.sid] = {
                'username': 'spectator',
                'score': 0
            }
            
            emit('game_state', {
                'is_spectator': True,
                'players': len(game['players'])
            })
            
            # Send spectator the current game state
            emit('new_round', {
                'round': game['round'],
                'problem': {
                    'title': game['current_problem'].title,
                    'description': game['current_problem'].description
                }
            })
            return
    
    emit('spectate_error', {'message': 'No active games to spectate'})

@socketio.on('submit_solution')
def handle_submit_solution(data):
    solution = data.get('solution', '')
    game_id = find_game_id(request.sid)
    
    if not game_id:
        emit('error', {'message': 'Not in a game'})
        return
    
    game = games[game_id]
    current_problem = game.get('current_problem')
    
    if not current_problem:
        emit('error', {'message': 'No current problem'})
        return
    
    # Check if solution is correct
    try:
        exec(solution)
        exec(current_problem.solution)
        
        # Compare function implementations
        if solution.strip() == current_problem.solution.strip():
            emit('correct_solution', {
                'player_id': request.sid,
                'solution': solution
            })
            
            # Update score
            game['players'][request.sid]['score'] += 1
            
            # Check if game is over
            if game['round'] >= game['max_rounds']:
                end_game(game_id)
            else:
                # Start next round
                game['round'] += 1
                start_new_round(game_id)
        else:
            emit('incorrect_solution', {
                'player_id': request.sid
            })
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('join_game')
def join_game(data):
    game_id = data.get('game_id')
    if game_id:
        join_room(game_id)
        emit('game_joined', {'game_id': game_id})

@socketio.on('send_message')
def send_message(data):
    game_id = data.get('game_id')
    message = data.get('message')
    sender = data.get('sender')
    
    if game_id and message and sender:
        emit('receive_message', {
            'game_id': game_id,
            'message': message,
            'sender': sender,
            'timestamp': datetime.now().strftime('%H:%M')
        }, room=game_id)

def find_game_id(sid):
    for game_id, game in games.items():
        if sid in game['players']:
            return game_id
    return None

def start_new_round(game_id):
    """Start a new round with a random problem"""
    if game_id not in games:
        return
    
    game = games[game_id]
    problem = random.choice(PROBLEMS)
    
    game['current_problem'] = {
        'title': problem.title,
        'description': problem.description,
        'solution': problem.solution
    }
    
    # Reset submissions for this round
    game['submissions'] = {}
    
    emit('new_round', {
        'round': game['round'],
        'problem': {
            'title': problem.title,
            'description': problem.description
        }
    }, room=game_id)

def end_game(game_id):
    if game_id not in games:
        return
    
    game = games[game_id]
    
    # Calculate winner
    players = list(game['players'].items())
    players.sort(key=lambda x: x[1]['score'], reverse=True)
    
    winner_id = players[0][0]
    
    # Send game over message to all players
    emit('game_over', {
        'winner': winner_id,
        'final_scores': {
            sid: player['score'] for sid, player in game['players'].items()
        }
    }, room=game_id)
    
    # Clean up game
    del games[game_id]
