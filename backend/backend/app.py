from . import create_app, redis_client
from .models import User, Score, LanguageEnum, GameMode, db
from flask_login import login_required, current_user
from flask_socketio import SocketIO, emit
from flask import request, render_template
import hashlib
import random
import json
import time
import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

app = create_app()
socketio = SocketIO(app)

# Initialize OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

class Game:
    REDIS_KEY = "cs_gauntlet_game_state"

    def __init__(self):
        self._load_state()

    def _load_state(self):
        state = redis_client.get(self.REDIS_KEY)
        if state:
            state = json.loads(state)
            self.current_round = state.get('current_round', 0)
            self.max_rounds = state.get('max_rounds', 3)
            self.players = state.get('players', {})  # {player_id: {solutions: [], times: [], rounds: []}}
            self.spectators = set(state.get('spectators', []))  # Set of spectator socket IDs
            self.current_problem = state.get('current_problem', None)
            self.round_start_time = state.get('round_start_time', None)
            self.winner = state.get('winner', None)
            self.game_mode = GameMode(state['game_mode']) if state.get('game_mode') else None
        else:
            self.current_round = 0
            self.max_rounds = 3
            self.players = {}
            self.spectators = set()
            self.current_problem = None
            self.round_start_time = None
            self.winner = None
            self.game_mode = None
        self._save_state()

    def _save_state(self):
        state = {
            'current_round': self.current_round,
            'max_rounds': self.max_rounds,
            'players': self.players,
            'spectators': list(self.spectators),
            'current_problem': self.current_problem,
            'round_start_time': self.round_start_time,
            'winner': self.winner,
            'game_mode': self.game_mode.value if self.game_mode else None
        }
        redis_client.set(self.REDIS_KEY, json.dumps(state))

    def set_game_mode(self, mode):
        self.game_mode = GameMode(mode)
        self._save_state()

    def add_spectator(self, sid):
        self.spectators.add(sid)
        self._save_state()

    def remove_spectator(self, sid):
        self.spectators.discard(sid)
        self._save_state()

    def start_new_round(self):
        if self.current_round >= self.max_rounds:
            return False
            
        # Fetch a random programming problem from the database
        problems = Problem.query.all()
        if not problems:
            print("No problems found in the database. Please add some.")
            return False
        
        self.current_problem = random.choice(problems).to_dict()
        self.current_round += 1
        self.round_start_time = time.time()
        self._save_state()
        return True

    async def evaluate_solutions(self, solutions):
        """
        Dispatches an asynchronous task to evaluate solutions using AI.
        """
        # For now, we'll just use the first solution for grading against the problem
        # In a real scenario, you might compare both solutions using the AI grader's compare_solutions method
        
        # Store a temporary submission to get an ID for the task
        # This is a simplified approach; a more robust solution might involve
        # a dedicated task queue for game state updates or a more complex
        # submission tracking mechanism.
        temp_submission = Submission(
            user_id=request.sid, # Using sid as a placeholder user_id for now
            problem_id=self.current_problem['id'],
            code=solutions[0],
            grading_result={},
            points_earned=0
        )
        db.session.add(temp_submission)
        db.session.commit()
        
        # Dispatch the grading task to Celery
        from tasks import grade_solution_task
        grade_solution_task.delay(temp_submission.id)
        
        # Return a placeholder or task ID immediately
        # The actual result will be handled by the Celery worker and updated in the DB
        return -1 # Indicate that the result is pending


@app.route('/game')
@login_required
def game_route():
    return render_template('game.html')

@socketio.on('connect')
def handle_connect():
    app.logger.info('Client connected')
    game = Game()
    emit('game_state', {
        'round': game.current_round,
        'problem': game.current_problem,
        'game_mode': game.game_mode.value if game.game_mode else None,
        'is_spectator': False
    })

@socketio.on('disconnect')
def handle_disconnect():
    game = Game()
    if request.sid in game.players:
        del game.players[request.sid]
    game.remove_spectator(request.sid)

@socketio.on('start_game')
def handle_start_game(data):
    game = Game()
    game_mode = data.get('game_mode', 'casual')
    game.set_game_mode(game_mode)
    
    if game.start_new_round():
        emit('new_round', {
            'problem': game.current_problem,
            'game_mode': game.game_mode.value
        }, broadcast=True)

@socketio.on('submit_solution')
async def handle_submit_solution(data):
    game = Game()
    player_id = request.sid
    solution = data['solution']
    
    # Store the solution
    if player_id not in game.players:
        game.players[player_id] = {
            'solutions': [],
            'times': [],
            'rounds': []
        }
    
    game.players[player_id]['solutions'].append(solution)
    game.players[player_id]['times'].append(time.time() - game.round_start_time)
    game.players[player_id]['rounds'].append(game.current_round)
    game._save_state()
    
    # Check if both players have submitted solutions
    if len(game.players) >= 2 and all(len(p['solutions']) == game.current_round for p in game.players.values()):
        # Get solutions from both players
        solutions = [p['solutions'][-1] for p in game.players.values()]
        
        # Evaluate solutions using AI (dispatches Celery task)
        await game.evaluate_solutions(solutions)
        
        # TODO: Implement logic to wait for Celery task result and determine winner
        # For now, we'll assume the Celery task will update the game state and notify players
        # once grading is complete.
        pass

@socketio.on('spectate')
def handle_spectate():
    """Handle when a user wants to spectate a game"""
    game = Game()
    game.add_spectator(request.sid)
    emit('game_state', {
        'round': game.current_round,
        'problem': game.current_problem,
        'game_mode': game.game_mode.value if game.game_mode else None,
        'is_spectator': True,
        'players': len(game.players)
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, port=5001, host='0.0.0.0')
