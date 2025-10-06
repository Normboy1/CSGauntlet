import pytest
from backend import create_app, db, redis_client
from backend.models import GameMode, Problem
from config import TestingConfig
import json
import time

@pytest.fixture(scope='module')
def test_app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        # Seed a problem for testing Game class
        if not Problem.query.first():
            problem = Problem(
                title="Test Problem",
                description="A simple test problem.",
                example="test_func(1) == 1",
                solution="def test_func(x): return x"
            )
            db.session.add(problem)
            db.session.commit()
        yield app
        db.drop_all()

@pytest.fixture(scope='function')
def game_instance(test_app):
    with test_app.app_context():
        # Clear Redis before each test
        redis_client.delete("cs_gauntlet_game_state")
        from backend.app import Game
        game = Game()
        yield game

def test_game_initialization(game_instance):
    assert game_instance.current_round == 0
    assert game_instance.max_rounds == 3
    assert game_instance.players == {}
    assert game_instance.spectators == set()
    assert game_instance.current_problem is None
    assert game_instance.round_start_time is None
    assert game_instance.winner is None
    assert game_instance.game_mode is None

def test_game_state_persistence(game_instance):
    game_instance.current_round = 1
    game_instance.players = {"player1": {"solutions": [], "times": [], "rounds": []}}
    game_instance.game_mode = GameMode.CASUAL
    game_instance._save_state()

    # Create a new game instance to load the saved state
    from backend.app import Game
    new_game_instance = Game()

    assert new_game_instance.current_round == 1
    assert "player1" in new_game_instance.players
    assert new_game_instance.game_mode == GameMode.CASUAL

def test_set_game_mode(game_instance):
    game_instance.set_game_mode(GameMode.BLITZ.value)
    assert game_instance.game_mode == GameMode.BLITZ
    # Verify state is saved
    from backend.app import Game
    new_game_instance = Game()
    assert new_game_instance.game_mode == GameMode.BLITZ

def test_add_remove_spectator(game_instance):
    game_instance.add_spectator("spec1")
    assert "spec1" in game_instance.spectators
    game_instance.remove_spectator("spec1")
    assert "spec1" not in game_instance.spectators
    # Verify state is saved
    from backend.app import Game
    new_game_instance = Game()
    assert "spec1" not in new_game_instance.spectators

def test_start_new_round(game_instance):
    assert game_instance.current_problem is None
    assert game_instance.current_round == 0
    assert game_instance.start_new_round()
    assert game_instance.current_problem is not None
    assert game_instance.current_round == 1
    # Verify state is saved
    from backend.app import Game
    new_game_instance = Game()
    assert new_game_instance.current_round == 1
    assert new_game_instance.current_problem is not None

def test_start_new_round_max_rounds(game_instance):
    game_instance.current_round = game_instance.max_rounds
    assert not game_instance.start_new_round()

def test_evaluate_solutions_dispatches_task(game_instance, mocker):
    # Mock the Celery task to prevent actual task execution during unit test
    mock_delay = mocker.patch('tasks.grade_solution_task.delay')

    game_instance.current_problem = {'id': 1, 'description': 'Test Problem'}
    game_instance.players = {
        "player1": {"solutions": ["sol1"], "times": [10], "rounds": [1]},
        "player2": {"solutions": ["sol2"], "times": [12], "rounds": [1]}
    }
    
    # Simulate a submission that triggers evaluation
    with test_app.app_context():
        # Need to mock request.sid for the temp_submission
        mocker.patch('flask.request.sid', "player1")
        # Need to mock db.session.add and db.session.commit
        mocker.patch('backend.db.session.add')
        mocker.patch('backend.db.session.commit')
        
        # Call the async method
        asyncio.run(game_instance.evaluate_solutions(["sol1", "sol2"]))

    mock_delay.assert_called_once_with(mocker.ANY) # Check if called with any submission_id

