import pytest
from backend import create_app, db
from backend.models import Problem

@pytest.fixture(scope='module')
def test_app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'REDIS_URL': 'redis://localhost:6379/1'  # Use a different Redis DB for tests
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='function')
def client(test_app):
    return test_app.test_client()

@pytest.fixture(scope='function')
def init_database(test_app):
    with test_app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
        # Add initial problems as done in __init__.py
        initial_problems = [
            {
                "title": "String Reversal",
                "description": "Write a function that takes a string as input and returns the reversed string.",
                "example": "reverse_string('hello') should return 'olleh'",
                "solution": "def reverse_string(s):\n    return s[::-1]"
            },
            {
                "title": "Array Sum",
                "description": "Write a function that takes a list of numbers and returns their sum.",
                "example": "array_sum([1, 2, 3, 4]) should return 10",
                "solution": "def array_sum(arr):\n    return sum(arr)"
            },
            {
                "title": "Factorial",
                "description": "Write a function that calculates the factorial of a given number.",
                "example": "factorial(5) should return 120",
                "solution": "def factorial(n):\n    if n == 0: return 1\n    return n * factorial(n-1)"
            }
        ]
        for p_data in initial_problems:
            problem = Problem(title=p_data['title'], description=p_data['description'], example=p_data['example'], solution=p_data['solution'])
            db.session.add(problem)
        db.session.commit()
        yield test_app

def test_initial_problems_added(init_database):
    with init_database.app_context():
        problems = Problem.query.all()
        assert len(problems) == 3
        assert problems[0].title == "String Reversal"
        assert problems[1].title == "Array Sum"
        assert problems[2].title == "Factorial"

def test_problem_to_dict(init_database):
    with init_database.app_context():
        problem = Problem.query.filter_by(title="String Reversal").first()
        problem_dict = problem.to_dict()
        assert problem_dict['title'] == "String Reversal"
        assert "solution" in problem_dict
        assert "id" in problem_dict
