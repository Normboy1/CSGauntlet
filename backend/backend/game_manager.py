"""
Comprehensive Game Manager for CS Gauntlet
Handles game state, matching, and core game functionality
"""

import json
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

from flask import current_app
from flask_socketio import emit, join_room, leave_room
from . import redis_client, db
from .models import Problem, User, Score, GameMode, Submission


class GameState(Enum):
    """Game state enumeration"""
    WAITING = "waiting"
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlayerStatus(Enum):
    """Player status enumeration"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    READY = "ready"
    PLAYING = "playing"
    FINISHED = "finished"


@dataclass
class GamePlayer:
    """Player in a game"""
    user_id: int
    socket_id: str
    username: str
    avatar_url: Optional[str] = None
    college: Optional[str] = None
    status: PlayerStatus = PlayerStatus.CONNECTED
    score: int = 0
    submissions: List[Dict] = None
    join_time: datetime = None
    
    def __post_init__(self):
        if self.submissions is None:
            self.submissions = []
        if self.join_time is None:
            self.join_time = datetime.utcnow()


@dataclass
class GameConfig:
    """Game configuration"""
    mode: GameMode
    max_players: int = 2
    max_rounds: int = 3
    time_limit: int = 1800  # 30 minutes
    round_time_limit: int = 300  # 5 minutes per round
    language: str = 'python'
    difficulty: str = 'medium'
    allow_spectators: bool = True
    auto_start: bool = True


@dataclass
class GameRound:
    """Individual game round"""
    round_number: int
    problem: Dict[str, Any]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    submissions: Dict[str, Any] = None
    winner: Optional[str] = None
    
    def __post_init__(self):
        if self.submissions is None:
            self.submissions = {}


class Game:
    """Main game class handling game logic and state"""
    
    def __init__(self, game_id: str, config: GameConfig, creator_user_id: int):
        self.game_id = game_id
        self.config = config
        self.creator_user_id = creator_user_id
        self.state = GameState.WAITING
        self.created_at = datetime.utcnow()
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None
        
        # Players and spectators
        self.players: Dict[str, GamePlayer] = {}  # socket_id -> GamePlayer
        self.spectators: Dict[str, Dict] = {}  # socket_id -> spectator_info
        
        # Game progress
        self.current_round = 0
        self.rounds: List[GameRound] = []
        self.winner: Optional[str] = None
        self.final_scores: Dict[str, int] = {}
        
        # Redis key for persistence
        self.redis_key = f"game:{self.game_id}"
        
        # Save initial state
        self.save_state()
    
    def add_player(self, user_id: int, socket_id: str, username: str, 
                   avatar_url: str = None, college: str = None) -> bool:
        """Add a player to the game"""
        
        if len(self.players) >= self.config.max_players:
            return False
        
        if self.state not in [GameState.WAITING, GameState.STARTING]:
            return False
        
        # Check if user is already in game (different socket)
        existing_player = next(
            (p for p in self.players.values() if p.user_id == user_id), 
            None
        )
        
        if existing_player:
            # Update socket ID for reconnection
            old_socket = existing_player.socket_id
            if old_socket in self.players:
                del self.players[old_socket]
            existing_player.socket_id = socket_id
            existing_player.status = PlayerStatus.CONNECTED
            self.players[socket_id] = existing_player
        else:
            # Add new player
            player = GamePlayer(
                user_id=user_id,
                socket_id=socket_id,
                username=username,
                avatar_url=avatar_url,
                college=college
            )
            self.players[socket_id] = player
        
        # Auto-start if configured and enough players
        if (self.config.auto_start and 
            len(self.players) == self.config.max_players and 
            self.state == GameState.WAITING):
            self.start_game()
        
        self.save_state()
        return True
    
    def remove_player(self, socket_id: str) -> bool:
        """Remove a player from the game"""
        
        if socket_id not in self.players:
            return False
        
        player = self.players[socket_id]
        
        if self.state == GameState.IN_PROGRESS:
            # Mark as disconnected but keep in game
            player.status = PlayerStatus.DISCONNECTED
        else:
            # Remove completely if game hasn't started
            del self.players[socket_id]
        
        # Cancel game if no players left
        if not any(p.status == PlayerStatus.CONNECTED for p in self.players.values()):
            self.state = GameState.CANCELLED
            self.ended_at = datetime.utcnow()
        
        self.save_state()
        return True
    
    def add_spectator(self, socket_id: str, user_id: int = None, username: str = "Spectator") -> bool:
        """Add a spectator to the game"""
        
        if not self.config.allow_spectators:
            return False
        
        if self.state not in [GameState.IN_PROGRESS, GameState.STARTING]:
            return False
        
        self.spectators[socket_id] = {
            'user_id': user_id,
            'username': username,
            'joined_at': datetime.utcnow().isoformat()
        }
        
        self.save_state()
        return True
    
    def remove_spectator(self, socket_id: str) -> bool:
        """Remove a spectator from the game"""
        
        if socket_id in self.spectators:
            del self.spectators[socket_id]
            self.save_state()
            return True
        return False
    
    def start_game(self) -> bool:
        """Start the game"""
        
        if self.state != GameState.WAITING:
            return False
        
        if len(self.players) < 1:  # Allow single player for testing
            return False
        
        self.state = GameState.STARTING
        self.started_at = datetime.utcnow()
        
        # Start first round
        success = self.start_next_round()
        
        if success:
            self.state = GameState.IN_PROGRESS
        
        self.save_state()
        return success
    
    def start_next_round(self) -> bool:
        """Start the next round"""
        
        if self.current_round >= self.config.max_rounds:
            return False
        
        # Get a random problem from database
        problems = Problem.query.filter_by(difficulty=self.config.difficulty).all()
        if not problems:
            # Fallback to any difficulty
            problems = Problem.query.all()
        
        if not problems:
            current_app.logger.error("No problems found in database")
            return False
        
        problem = random.choice(problems)
        
        self.current_round += 1
        
        round_data = GameRound(
            round_number=self.current_round,
            problem=self._serialize_problem(problem),
            start_time=datetime.utcnow()
        )
        
        self.rounds.append(round_data)
        self.save_state()
        
        return True
    
    def submit_solution(self, socket_id: str, code: str, language: str = None) -> Tuple[bool, str]:
        """Submit a solution for the current round"""
        
        if socket_id not in self.players:
            return False, "Player not found"
        
        if self.state != GameState.IN_PROGRESS:
            return False, "Game not in progress"
        
        if not self.rounds or self.current_round == 0:
            return False, "No active round"
        
        current_round = self.rounds[-1]
        player = self.players[socket_id]
        
        # Check if player already submitted for this round
        if socket_id in current_round.submissions:
            return False, "Solution already submitted for this round"
        
        # Create submission
        submission = {
            'player_id': socket_id,
            'user_id': player.user_id,
            'code': code,
            'language': language or self.config.language,
            'submitted_at': datetime.utcnow().isoformat(),
            'round': self.current_round
        }
        
        current_round.submissions[socket_id] = submission
        
        # Add to player's submissions
        player.submissions.append(submission)
        
        self.save_state()
        
        # Check if all players have submitted
        active_players = [p for p in self.players.values() if p.status in [PlayerStatus.CONNECTED, PlayerStatus.PLAYING]]
        
        if len(current_round.submissions) >= len(active_players):
            self._evaluate_round()
        
        return True, "Solution submitted successfully"
    
    def _evaluate_round(self):
        """Evaluate the current round submissions with AI grading"""
        
        if not self.rounds:
            return
        
        current_round = self.rounds[-1]
        
        # Use AI grader if available
        try:
            # Run AI grading asynchronously
            asyncio.create_task(self._ai_grade_submissions(current_round))
        except Exception as e:
            current_app.logger.error(f"AI grading failed: {e}")
            # Fallback to simple evaluation
            self._simple_evaluate_round(current_round)
        
        current_round.end_time = datetime.utcnow()
        
        # Check if game is complete
        if self.current_round >= self.config.max_rounds:
            self._end_game()
        else:
            # Start next round after delay
            pass
        
        self.save_state()
    
    async def _ai_grade_submissions(self, current_round):
        """Grade submissions using AI grader"""
        
        if not hasattr(current_app, 'ai_grader') or not current_app.ai_grader:
            current_app.logger.warning("AI grader not available, using simple evaluation")
            self._simple_evaluate_round(current_round)
            return
        
        problem_description = current_round.problem.get('description', '')
        problem_title = current_round.problem.get('title', 'Coding Problem')
        
        # Grade each submission
        for socket_id, submission in current_round.submissions.items():
            if socket_id not in self.players:
                continue
                
            try:
                # Create test results (simplified - in production, run actual tests)
                test_results = {
                    'passed': random.randint(2, 3),  # Simulate passing tests
                    'total': 3,
                    'test_results': []
                }
                
                # Grade with AI
                grading_result = await current_app.ai_grader.grade_solution(
                    problem_description=f"{problem_title}: {problem_description}",
                    solution_code=submission['code'],
                    test_results=test_results,
                    language=submission['language']
                )
                
                # Update submission with AI grading results
                submission['ai_grading'] = {
                    'overall_grade': grading_result.overall_grade,
                    'total_score': grading_result.criteria.total,
                    'criteria': {
                        'correctness': grading_result.criteria.correctness,
                        'efficiency': grading_result.criteria.efficiency,
                        'readability': grading_result.criteria.readability,
                        'style': grading_result.criteria.style,
                        'innovation': grading_result.criteria.innovation
                    },
                    'feedback': grading_result.feedback,
                    'suggestions': grading_result.suggestions,
                    'execution_time': grading_result.execution_time
                }
                
                # Update player score based on AI grading
                ai_score = int(grading_result.criteria.total)
                self.players[socket_id].score += ai_score
                
                current_app.logger.info(f"AI graded submission: {ai_score}/100 ({grading_result.overall_grade})")
                
            except Exception as e:
                current_app.logger.error(f"AI grading failed for submission: {e}")
                # Fallback to random score
                fallback_score = random.randint(70, 90)
                self.players[socket_id].score += fallback_score
                submission['ai_grading'] = {
                    'overall_grade': 'B',
                    'total_score': fallback_score,
                    'feedback': {'general': 'AI grading temporarily unavailable'},
                    'suggestions': ['AI grading will be restored soon']
                }
    
    def _simple_evaluate_round(self, current_round):
        """Simple fallback evaluation when AI grading is unavailable"""
        
        for socket_id, submission in current_round.submissions.items():
            if socket_id in self.players:
                # Simple evaluation based on code length and basic checks
                code = submission.get('code', '')
                score = 70  # Base score
                
                # Basic heuristics
                if len(code) > 50:
                    score += 10  # Bonus for substantial code
                if 'def ' in code:
                    score += 10  # Bonus for function definition
                if '#' in code:
                    score += 5   # Bonus for comments
                
                score = min(100, score + random.randint(-5, 15))  # Add some randomness
                self.players[socket_id].score += score
                
                # Add basic feedback
                submission['ai_grading'] = {
                    'overall_grade': 'B' if score >= 80 else 'C',
                    'total_score': score,
                    'feedback': {'general': 'Basic evaluation completed'},
                    'suggestions': ['AI grading will provide detailed feedback soon']
                }
    
    def _end_game(self):
        """End the game and determine winner"""
        
        self.state = GameState.COMPLETED
        self.ended_at = datetime.utcnow()
        
        # Calculate final scores
        for socket_id, player in self.players.items():
            self.final_scores[socket_id] = player.score
        
        # Determine winner
        if self.final_scores:
            winner_socket = max(self.final_scores, key=self.final_scores.get)
            self.winner = winner_socket
        
        # Save scores to database
        self._save_scores_to_db()
        
        self.save_state()
    
    def _save_scores_to_db(self):
        """Save final scores to database"""
        
        try:
            for socket_id, player in self.players.items():
                is_winner = (socket_id == self.winner)
                
                score = Score(
                    user_id=player.user_id,
                    language=self.config.language,
                    is_win=is_winner,
                    game_mode=self.config.mode
                )
                db.session.add(score)
            
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error saving scores to database: {e}")
            db.session.rollback()
    
    def _serialize_problem(self, problem: Problem) -> Dict[str, Any]:
        """Serialize problem for transmission (exclude solution)"""
        
        return {
            'id': problem.id,
            'title': problem.title,
            'description': problem.description,
            'example': problem.example,
            'difficulty': problem.difficulty
            # Note: Intentionally exclude solution for security
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get current game state for transmission"""
        
        return {
            'game_id': self.game_id,
            'state': self.state.value,
            'config': asdict(self.config),
            'current_round': self.current_round,
            'players': {
                sid: {
                    'user_id': p.user_id,
                    'username': p.username,
                    'avatar_url': p.avatar_url,
                    'college': p.college,
                    'status': p.status.value,
                    'score': p.score
                } for sid, p in self.players.items()
            },
            'spectators_count': len(self.spectators),
            'current_problem': self.rounds[-1].problem if self.rounds else None,
            'round_start_time': self.rounds[-1].start_time.isoformat() if self.rounds and self.rounds[-1].start_time else None,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'time_remaining': self._calculate_time_remaining()
        }
    
    def _calculate_time_remaining(self) -> Optional[int]:
        """Calculate time remaining in current round/game"""
        
        if self.state != GameState.IN_PROGRESS or not self.rounds:
            return None
        
        current_round = self.rounds[-1]
        if not current_round.start_time:
            return None
        
        elapsed = (datetime.utcnow() - current_round.start_time).total_seconds()
        remaining = self.config.round_time_limit - elapsed
        
        return max(0, int(remaining))
    
    def save_state(self):
        """Save game state to Redis"""
        
        try:
            state_data = {
                'game_id': self.game_id,
                'config': asdict(self.config),
                'state': self.state.value,
                'creator_user_id': self.creator_user_id,
                'created_at': self.created_at.isoformat(),
                'started_at': self.started_at.isoformat() if self.started_at else None,
                'ended_at': self.ended_at.isoformat() if self.ended_at else None,
                'current_round': self.current_round,
                'players': {
                    sid: asdict(player) for sid, player in self.players.items()
                },
                'spectators': self.spectators,
                'rounds': [asdict(round_data) for round_data in self.rounds],
                'winner': self.winner,
                'final_scores': self.final_scores
            }
            
            # Convert datetime objects to ISO format
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            serialized_data = json.dumps(state_data, default=serialize_datetime)
            redis_client.setex(self.redis_key, 86400, serialized_data)  # 24 hour expiry
            
        except Exception as e:
            current_app.logger.error(f"Error saving game state: {e}")
    
    @classmethod
    def load_from_redis(cls, game_id: str) -> Optional['Game']:
        """Load game state from Redis"""
        
        try:
            redis_key = f"game:{game_id}"
            data = redis_client.get(redis_key)
            
            if not data:
                return None
            
            state_data = json.loads(data)
            
            # Reconstruct game object
            config_data = state_data['config']
            config = GameConfig(
                mode=GameMode(config_data['mode']),
                max_players=config_data['max_players'],
                max_rounds=config_data['max_rounds'],
                time_limit=config_data['time_limit'],
                round_time_limit=config_data['round_time_limit'],
                language=config_data['language'],
                difficulty=config_data['difficulty'],
                allow_spectators=config_data['allow_spectators'],
                auto_start=config_data['auto_start']
            )
            
            game = cls(game_id, config, state_data['creator_user_id'])
            
            # Restore state
            game.state = GameState(state_data['state'])
            game.created_at = datetime.fromisoformat(state_data['created_at'])
            game.started_at = datetime.fromisoformat(state_data['started_at']) if state_data['started_at'] else None
            game.ended_at = datetime.fromisoformat(state_data['ended_at']) if state_data['ended_at'] else None
            game.current_round = state_data['current_round']
            game.winner = state_data['winner']
            game.final_scores = state_data['final_scores']
            
            # Restore players
            for sid, player_data in state_data['players'].items():
                player = GamePlayer(
                    user_id=player_data['user_id'],
                    socket_id=player_data['socket_id'],
                    username=player_data['username'],
                    avatar_url=player_data['avatar_url'],
                    college=player_data['college'],
                    status=PlayerStatus(player_data['status']),
                    score=player_data['score'],
                    submissions=player_data['submissions'],
                    join_time=datetime.fromisoformat(player_data['join_time'])
                )
                game.players[sid] = player
            
            # Restore spectators
            game.spectators = state_data['spectators']
            
            # Restore rounds
            for round_data in state_data['rounds']:
                round_obj = GameRound(
                    round_number=round_data['round_number'],
                    problem=round_data['problem'],
                    start_time=datetime.fromisoformat(round_data['start_time']) if round_data['start_time'] else None,
                    end_time=datetime.fromisoformat(round_data['end_time']) if round_data['end_time'] else None,
                    submissions=round_data['submissions'],
                    winner=round_data['winner']
                )
                game.rounds.append(round_obj)
            
            return game
            
        except Exception as e:
            current_app.logger.error(f"Error loading game state: {e}")
            return None


class GameManager:
    """Manages all active games and matchmaking"""
    
    def __init__(self):
        self.active_games: Dict[str, Game] = {}
        self.matchmaking_queue: Dict[str, List[Dict]] = {}  # game_mode -> [player_info]
    
    def create_game(self, creator_user_id: int, config: GameConfig) -> str:
        """Create a new game"""
        
        game_id = str(uuid.uuid4())[:8]  # Short game ID
        game = Game(game_id, config, creator_user_id)
        
        self.active_games[game_id] = game
        
        current_app.logger.info(f"Created game {game_id} by user {creator_user_id}")
        return game_id
    
    def get_game(self, game_id: str) -> Optional[Game]:
        """Get a game by ID"""
        
        if game_id in self.active_games:
            return self.active_games[game_id]
        
        # Try loading from Redis
        game = Game.load_from_redis(game_id)
        if game:
            self.active_games[game_id] = game
        
        return game
    
    def join_game(self, game_id: str, user_id: int, socket_id: str, 
                  username: str, avatar_url: str = None, college: str = None) -> Tuple[bool, str]:
        """Join a game"""
        
        game = self.get_game(game_id)
        if not game:
            return False, "Game not found"
        
        success = game.add_player(user_id, socket_id, username, avatar_url, college)
        if success:
            return True, "Joined game successfully"
        else:
            return False, "Unable to join game"
    
    def leave_game(self, game_id: str, socket_id: str) -> bool:
        """Leave a game"""
        
        game = self.get_game(game_id)
        if not game:
            return False
        
        return game.remove_player(socket_id)
    
    def find_or_create_match(self, user_id: int, socket_id: str, username: str,
                           game_mode: str, language: str = 'python',
                           avatar_url: str = None, college: str = None) -> Tuple[bool, str, Optional[str]]:
        """Find an existing match or create a new one"""
        
        # Initialize queue for game mode
        if game_mode not in self.matchmaking_queue:
            self.matchmaking_queue[game_mode] = []
        
        queue = self.matchmaking_queue[game_mode]
        
        # Look for compatible match
        for i, waiting_player in enumerate(queue):
            if (waiting_player['language'] == language and 
                waiting_player['user_id'] != user_id):  # Don't match with self
                
                # Found a match, create game
                queue.pop(i)  # Remove waiting player from queue
                
                config = GameConfig(
                    mode=GameMode(game_mode),
                    language=language,
                    auto_start=True
                )
                
                game_id = self.create_game(waiting_player['user_id'], config)
                game = self.get_game(game_id)
                
                # Add both players
                game.add_player(
                    waiting_player['user_id'], 
                    waiting_player['socket_id'],
                    waiting_player['username'],
                    waiting_player.get('avatar_url'),
                    waiting_player.get('college')
                )
                
                game.add_player(user_id, socket_id, username, avatar_url, college)
                
                return True, "Match found", game_id
        
        # No match found, add to queue
        player_info = {
            'user_id': user_id,
            'socket_id': socket_id,
            'username': username,
            'avatar_url': avatar_url,
            'college': college,
            'language': language,
            'joined_queue_at': datetime.utcnow().isoformat()
        }
        
        queue.append(player_info)
        
        return False, "Added to matchmaking queue", None
    
    def cancel_matchmaking(self, user_id: int, socket_id: str) -> bool:
        """Cancel matchmaking for a user"""
        
        for game_mode, queue in self.matchmaking_queue.items():
            for i, player in enumerate(queue):
                if player['user_id'] == user_id or player['socket_id'] == socket_id:
                    queue.pop(i)
                    return True
        
        return False
    
    def cleanup_inactive_games(self):
        """Clean up inactive or completed games"""
        
        current_time = datetime.utcnow()
        games_to_remove = []
        
        for game_id, game in self.active_games.items():
            # Remove completed games after 1 hour
            if (game.state == GameState.COMPLETED and 
                game.ended_at and 
                (current_time - game.ended_at).total_seconds() > 3600):
                games_to_remove.append(game_id)
            
            # Remove cancelled games after 10 minutes
            elif (game.state == GameState.CANCELLED and 
                  game.ended_at and 
                  (current_time - game.ended_at).total_seconds() > 600):
                games_to_remove.append(game_id)
            
            # Remove stale waiting games after 30 minutes
            elif (game.state == GameState.WAITING and 
                  (current_time - game.created_at).total_seconds() > 1800):
                games_to_remove.append(game_id)
        
        for game_id in games_to_remove:
            del self.active_games[game_id]
            current_app.logger.info(f"Cleaned up inactive game {game_id}")
    
    def get_active_games_count(self) -> int:
        """Get count of active games"""
        return len(self.active_games)
    
    def get_matchmaking_stats(self) -> Dict[str, int]:
        """Get matchmaking queue statistics"""
        return {
            mode: len(queue) for mode, queue in self.matchmaking_queue.items()
        }


# Global game manager instance
game_manager = GameManager()