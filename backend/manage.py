from flask.cli import FlaskGroup
from backend import create_app, db
from backend.models import User, Score, LanguageEnum, GameMode, Problem, GameModeDetails, TriviaQuestion, DebugChallenge, Submission
from config import DevelopmentConfig

app = create_app(DevelopmentConfig)
cli = FlaskGroup(app)

@cli.command("create_db")
def create_db():
    """Creates the database tables."""
    db.drop_all()
    db.create_all()
    db.session.commit()
    print("Database tables created successfully!")

@cli.command("seed_problems")
def seed_problems():
    """Seeds the database with initial programming problems."""
    if not Problem.query.first():
        print("Adding initial problems to the database...")
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
        print("Initial problems added successfully!")
    else:
        print("Problems already exist in the database. Skipping seeding.")

@cli.command("seed_game_modes")
def seed_game_modes():
    """Seeds the database with initial game mode details."""
    if not GameModeDetails.query.first():
        print("Adding initial game modes to the database...")
        initial_game_modes = [
            {
                'name': 'Classic',
                'description': 'Traditional 1v1 competitive matches with standard rules.',
                'time_limit': 900,
                'max_players': 2
            },
            {
                'name': 'Custom',
                'description': 'Create or join custom games with your own rules and settings.',
                'time_limit': 1800,
                'max_players': 4
            },
            {
                'name': 'Blitz',
                'description': 'Fast-paced matches with shorter time limits and quick rounds.',
                'time_limit': 300,
                'max_players': 2
            },
            {
                'name': 'Practice',
                'description': 'Train against AI or practice specific skills without ranking changes.',
                'time_limit': 600,
                'max_players': 1
            },
            {
                'name': 'Ranked',
                'description': 'Competitive matches that affect your skill rating and ranking.',
                'time_limit': 900,
                'max_players': 2
            },
            {
                'name': 'Casual',
                'description': 'Relaxed matches for fun without any ranking implications.',
                'time_limit': 900,
                'max_players': 2
            },
            {
                'name': 'Trivia',
                'description': 'Test your knowledge with programming trivia questions and challenges.',
                'time_limit': 600,
                'max_players': 4
            },
            {
                'name': 'Debug',
                'description': 'Find and fix bugs in code snippets as fast as possible.',
                'time_limit': 480,
                'max_players': 2
            },
            {
                'name': 'Electrical',
                'description': 'Build and test electrical circuits in a competitive environment.',
                'time_limit': 720,
                'max_players': 2
            }
        ]
        for gm_data in initial_game_modes:
            game_mode = GameModeDetails(name=gm_data['name'], description=gm_data['description'], time_limit=gm_data['time_limit'], max_players=gm_data['max_players'])
            db.session.add(game_mode)
        db.session.commit()
        print("Initial game modes added successfully!")
    else:
        print("Game modes already exist in the database. Skipping seeding.")

@cli.command("seed_trivia_questions")
def seed_trivia_questions():
    """Seeds the database with initial trivia questions."""
    if not TriviaQuestion.query.first():
        print("Adding initial trivia questions to the database...")
        initial_trivia_questions = [
            {
                'question': 'What is the time complexity of binary search?',
                'options': ['O(n)', 'O(log n)', 'O(n log n)', 'O(n²)'],
                'correct_answer_index': 1,
                'difficulty': 'easy',
                'category': 'algorithms',
                'explanation': 'Binary search eliminates half of the search space in each iteration, resulting in O(log n) time complexity.',
                'points': 10
            },
            {
                'question': 'Which data structure uses LIFO (Last In, First Out) principle?',
                'options': ['Queue', 'Stack', 'Array', 'Linked List'],
                'correct_answer_index': 1,
                'difficulty': 'easy',
                'category': 'data-structures',
                'explanation': 'Stack follows LIFO principle where the last element added is the first to be removed.',
                'points': 10
            },
            {
                'question': 'What is the worst-case time complexity of QuickSort?',
                'options': ['O(n)', 'O(n log n)', 'O(n²)', 'O(2^n)'],
                'correct_answer_index': 2,
                'difficulty': 'medium',
                'category': 'algorithms',
                'explanation': 'QuickSort has O(n²) worst-case complexity when the pivot is always the smallest or largest element.',
                'points': 20
            },
            {
                'question': 'Which of these is NOT a valid JavaScript variable declaration?',
                'options': ['var x = 5;', 'let x = 5;', 'const x = 5;', 'int x = 5;'],
                'correct_answer_index': 3,
                'difficulty': 'easy',
                'category': 'programming-concepts',
                'explanation': 'JavaScript doesn\'t have an "int" keyword for variable declaration.',
                'points': 10
            },
            {
                'question': 'What does "Big O" notation describe?',
                'options': ['Best case performance', 'Average case performance', 'Worst case performance', 'Memory usage only'],
                'correct_answer_index': 2,
                'difficulty': 'medium',
                'category': 'cs-theory',
                'explanation': 'Big O notation describes the worst-case time or space complexity of an algorithm.',
                'points': 20
            },
            {
                'question': 'Which traversal method would you use to copy a binary tree?',
                'options': ['In-order', 'Pre-order', 'Post-order', 'Level-order'],
                'correct_answer_index': 1,
                'difficulty': 'hard',
                'category': 'algorithms',
                'explanation': 'Pre-order traversal (root, left, right) allows you to create nodes in the correct order when copying a tree.',
                'points': 30
            },
            {
                'question': 'What is the space complexity of merge sort?',
                'options': ['O(1)', 'O(log n)', 'O(n)', 'O(n log n)'],
                'correct_answer_index': 2,
                'difficulty': 'medium',
                'category': 'algorithms',
                'explanation': 'Merge sort requires O(n) additional space for the temporary arrays used during merging.',
                'points': 20
            },
            {
                'question': 'Which principle states that software entities should be open for extension but closed for modification?',
                'options': ['Single Responsibility', 'Open/Closed', 'Liskov Substitution', 'Interface Segregation'],
                'correct_answer_index': 1,
                'difficulty': 'hard',
                'category': 'cs-theory',
                'explanation': 'The Open/Closed Principle is one of the SOLID principles of object-oriented design.',
                'points': 30
            },
            {
                'question': 'What would be the output of: console.log(0.1 + 0.2 === 0.3)?',
                'options': ['true', 'false', 'undefined', 'Error'],
                'correct_answer_index': 1,
                'difficulty': 'medium',
                'category': 'debugging',
                'explanation': 'Due to floating-point precision issues, 0.1 + 0.2 equals 0.30000000000000004, not 0.3.',
                'points': 20
            },
            {
                'question': 'Which sorting algorithm is stable and has O(n) best case time complexity?',
                'options': ['Quick Sort', 'Heap Sort', 'Insertion Sort', 'Selection Sort'],
                'correct_answer_index': 2,
                'difficulty': 'hard',
                'category': 'algorithms',
                'explanation': 'Insertion sort is stable and has O(n) best case when the array is already sorted.',
                'points': 30
            },
            {
                'question': 'What is the maximum number of nodes in a binary tree of height h?',
                'options': ['2^h', '2^(h+1)', '2^(h+1) - 1', '2^h - 1'],
                'correct_answer_index': 2,
                'difficulty': 'medium',
                'category': 'data-structures',
                'explanation': 'A binary tree of height h can have at most 2^(h+1) - 1 nodes.',
                'points': 20
            },
            {
                'question': 'Which design pattern ensures a class has only one instance?',
                'options': ['Factory', 'Singleton', 'Observer', 'Strategy'],
                'correct_answer_index': 1,
                'difficulty': 'easy',
                'category': 'programming-concepts',
                'explanation': 'The Singleton pattern ensures a class has only one instance and provides global access to it.',
                'points': 10
            }
        ]
        for tq_data in initial_trivia_questions:
            trivia_question = TriviaQuestion(
                question=tq_data['question'],
                options=tq_data['options'],
                correct_answer_index=tq_data['correct_answer_index'],
                difficulty=tq_data['difficulty'],
                category=tq_data['category'],
                explanation=tq_data['explanation'],
                points=tq_data['points']
            )
            db.session.add(trivia_question)
        db.session.commit()
        print("Initial trivia questions added successfully!")
    else:
        print("Trivia questions already exist in the database. Skipping seeding.")

@cli.command("seed_debug_challenges")
def seed_debug_challenges():
    """Seeds the database with initial debug challenges."""
    if not DebugChallenge.query.first():
        print("Adding initial debug challenges to the database...")
        initial_debug_challenges = [
            {
                'title': 'Array Sum Function',
                'description': 'This function should calculate the sum of all elements in an array, but it has bugs.',
                'buggy_code': '''function arraySum(arr) {
    let sum = 0;
    for (let i = 0; i <= arr.length; i++) {
        sum += arr[i];
    }
    return sum;
}

// Test case
console.log(arraySum([1, 2, 3, 4, 5])); // Expected: 15''',
                'expected_output': '15',
                'language': 'javascript',
                'difficulty': 'easy',
                'bugs': [
                    {
                        'id': 'bug1',
                        'line': 3,
                        'type': 'logical',
                        'description': 'Loop condition should be < instead of <=',
                        'fix': 'for (let i = 0; i < arr.length; i++)',
                        'points': 15
                    }
                ],
                'hints': [
                    'Check the loop condition - are you accessing array elements correctly?',
                    'What happens when i equals arr.length?'
                ],
                'total_points': 15
            },
            {
                'title': 'String Reversal',
                'description': 'This function should reverse a string, but it contains multiple bugs.',
                'buggy_code': '''def reverse_string(s):
    if s == None:
        return ""
    
    reversed = ""
    for i in range(len(s)):
        reversed = s[i] + reversed
    
    return reversed

# Test case
print(reverse_string("hello"))  # Expected: "olleh"''',
                'expected_output': 'olleh',
                'language': 'python',
                'difficulty': 'easy',
                'bugs': [
                    {
                        'id': 'bug1',
                        'line': 2,
                        'type': 'logical',
                        'description': 'Should check for None with "is" operator',
                        'fix': 'if s is None:',
                        'points': 10
                    }
                ],
                'hints': [
                    'In Python, None should be checked with "is" operator',
                    'The algorithm is correct but the None check has a style issue'
                ],
                'total_points': 10
            },
            {
                'title': 'Binary Search Implementation',
                'description': 'Binary search with logical and boundary errors.',
                'buggy_code': '''function binarySearch(arr, target) {
    let left = 0;
    let right = arr.length;
    
    while (left < right) {
        let mid = Math.floor((left + right) / 2);
        
        if (arr[mid] == target) {
            return mid;
        } else if (arr[mid] < target) {
            left = mid;
        } else {
            right = mid - 1;
        }
    }
    
    return -1;
}

// Test case
console.log(binarySearch([1, 2, 3, 4, 5], 3)); // Expected: 2''',
                'expected_output': '2',
                'language': 'javascript',
                'difficulty': 'medium',
                'bugs': [
                    {
                        'id': 'bug1',
                        'line': 3,
                        'type': 'logical',
                        'description': 'Right boundary should be arr.length - 1',
                        'fix': 'let right = arr.length - 1;',
                        'points': 20
                    },
                    {
                        'id': 'bug2',
                        'line': 5,
                        'type': 'logical',
                        'description': 'Condition should be left <= right',
                        'fix': 'while (left <= right) {',
                        'points': 15
                    },
                    {
                        'id': 'bug3',
                        'line': 11,
                        'type': 'logical',
                        'description': 'Left should be mid + 1',
                        'fix': 'left = mid + 1;',
                        'points': 15
                    }
                ],
                'hints': [
                    'Check the initial right boundary value',
                    'What happens when left equals right?',
                    'Are you updating the search boundaries correctly?'
                ],
                'total_points': 50
            },
            {
                'title': 'Factorial Function',
                'description': 'Recursive factorial with base case and overflow issues.',
                'buggy_code': '''def factorial(n):
    if n == 1:
        return 1
    else:
        return n * factorial(n - 1)

# Test cases
print(factorial(5))  # Expected: 120
print(factorial(0))  # Expected: 1''',
                'expected_output': '120, 1',
                'language': 'python',
                'difficulty': 'easy',
                'bugs': [
                    {
                        'id': 'bug1',
                        'line': 2,
                        'type': 'logical',
                        'description': 'Base case should include n == 0',
                        'fix': 'if n == 0 or n == 1:',
                        'points': 20
                    }
                ],
                'hints': [
                    'What should factorial(0) return?',
                    'Check the base case condition'
                ],
                'total_points': 20
            },
            {
                'title': 'List Filtering',
                'description': 'Filter even numbers from a list.',
                'buggy_code': '''def filter_even(numbers):
    result = []
    for num in numbers:
        if num % 2 == 1:
            result.append(num)
    return result

# Test case
print(filter_even([1, 2, 3, 4, 5, 6]))  # Expected: [2, 4, 6]''',
                'expected_output': '[2, 4, 6]',
                'language': 'python',
                'difficulty': 'easy',
                'bugs': [
                    {
                        'id': 'bug1',
                        'line': 4,
                        'type': 'logical',
                        'description': 'Should check for even numbers (% 2 == 0)',
                        'fix': 'if num % 2 == 0:',
                        'points': 15
                    }
                ],
                'hints': [
                    'What does % 2 == 1 check for?',
                    'Do you want even or odd numbers?'
                ],
                'total_points': 15
            },
            {
                'title': 'Palindrome Check',
                'description': 'Check if a string is a palindrome.',
                'buggy_code': '''def is_palindrome(s):
    s = s.lower()
    left = 0
    right = len(s) - 1
    
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    
    return True

# Test case
print(is_palindrome("A man a plan a canal Panama"))  # Expected: True''',
                'expected_output': 'True',
                'language': 'python',
                'difficulty': 'medium',
                'bugs': [
                    {
                        'id': 'bug1',
                        'line': 2,
                        'type': 'logical',
                        'description': 'Should remove spaces and non-alphanumeric characters',
                        'fix': 's = "".join(char.lower() for char in s if char.isalnum())',
                        'points': 25
                    }
                ],
                'hints': [
                    'The palindrome check should ignore spaces and punctuation',
                    'Consider what characters should be included in the comparison'
                ],
                'total_points': 25
            }
        ]
        for dc_data in initial_debug_challenges:
            debug_challenge = DebugChallenge(
                title=dc_data['title'],
                description=dc_data['description'],
                buggy_code=dc_data['buggy_code'],
                expected_output=dc_data['expected_output'],
                language=dc_data['language'],
                difficulty=dc_data['difficulty'],
                bugs=dc_data['bugs'],
                hints=dc_data['hints'],
                total_points=dc_data['total_points']
            )
            db.session.add(debug_challenge)
        db.session.commit()
        print("Initial debug challenges added successfully!")
    else:
        print("Debug challenges already exist in the database. Skipping seeding.")

if __name__ == '__main__':
    cli()