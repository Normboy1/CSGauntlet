from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import jwt
import datetime
import asyncio
import json
from typing import Dict, Any

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
CORS(app, origins=["http://localhost:3000", "http://localhost:3002"])

# Simple in-memory user storage (for demo purposes)
users_db = {
    'demo@example.com': {
        'id': 1,
        'email': 'demo@example.com',
        'username': 'demo',
        'password': 'password123',  # In real app, this would be hashed
        'college': 'Demo University',
        'rank': 'Student'
    },
    'admin': {
        'id': 2,
        'email': 'admin@example.com',
        'username': 'admin',
        'password': 'admin123',
        'college': 'Admin College',
        'rank': 'Admin'
    },
    'normbeezy@creator.com': {
        'id': 9999,
        'email': 'normbeezy@creator.com',
        'username': 'Normbeezy',
        'password': 'Norm4356',
        'college': 'Creator University',
        'rank': 'Creator'
    }
}

@app.route('/')
def hello():
    return jsonify({'message': 'CS Gauntlet Backend is running!', 'status': 'success'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'port': 8000})

@app.route('/api/users')
def users():
    return jsonify({'users': ['demo_user'], 'message': 'Simple user list'})

@app.route('/api/leaderboard')
def leaderboard():
    # Sample leaderboard data that matches the expected format
    sample_data = [
        {
            "username": "Normbeezy",
            "rating": 9999,
            "games_played": 100,
            "win_rate": 100.0,
            "college": "Creator University"
        },
        {
            "username": "CodeMaster",
            "rating": 2150,
            "games_played": 47,
            "win_rate": 78.5,
            "college": "MIT"
        },
        {
            "username": "AlgoWizard", 
            "rating": 2089,
            "games_played": 52,
            "win_rate": 71.2,
            "college": "Stanford"
        },
        {
            "username": "DataNinja",
            "rating": 1987,
            "games_played": 34,
            "win_rate": 68.9,
            "college": "UC Berkeley"
        },
        {
            "username": "PythonPro",
            "rating": 1856,
            "games_played": 29,
            "win_rate": 62.1,
            "college": "Carnegie Mellon"
        },
        {
            "username": "JavaJedi",
            "rating": 1743,
            "games_played": 38,
            "win_rate": 57.9,
            "college": "Harvard"
        }
    ]
    return jsonify(sample_data)

@app.route('/api/leaderboard/detailed')
def leaderboard_detailed():
    # Enhanced leaderboard data for the EnhancedLeaderboard component
    detailed_data = [
        {
            "user_id": 9999,
            "username": "Normbeezy",
            "total_points": 99999,
            "problems_solved": 500,
            "average_grade": "A++",
            "avg_score": 100.0,
            "best_categories": ["Creator", "All Categories", "Supreme"],
            "streak": 999,
            "efficiency_rating": 5.0,
            "style_rating": 5.0
        },
        {
            "user_id": 1,
            "username": "CodeMaster",
            "total_points": 15420,
            "problems_solved": 87,
            "average_grade": "A+",
            "avg_score": 94.2,
            "best_categories": ["Algorithms", "Dynamic Programming"],
            "streak": 12,
            "efficiency_rating": 4.8,
            "style_rating": 4.6
        },
        {
            "user_id": 2,
            "username": "AlgoWizard",
            "total_points": 13750,
            "problems_solved": 76,
            "average_grade": "A",
            "avg_score": 89.7,
            "best_categories": ["Graphs", "Trees"],
            "streak": 8,
            "efficiency_rating": 4.5,
            "style_rating": 4.3
        },
        {
            "user_id": 3,
            "username": "DataNinja",
            "total_points": 12300,
            "problems_solved": 69,
            "average_grade": "A-",
            "avg_score": 85.1,
            "best_categories": ["Data Structures", "Arrays"],
            "streak": 15,
            "efficiency_rating": 4.2,
            "style_rating": 4.7
        },
        {
            "user_id": 4,
            "username": "PythonPro",
            "total_points": 10850,
            "problems_solved": 58,
            "average_grade": "B+",
            "avg_score": 81.6,
            "best_categories": ["String Processing", "Math"],
            "streak": 5,
            "efficiency_rating": 4.0,
            "style_rating": 4.1
        },
        {
            "user_id": 5,
            "username": "JavaJedi",
            "total_points": 9420,
            "problems_solved": 52,
            "average_grade": "B",
            "avg_score": 78.3,
            "best_categories": ["Object-Oriented", "Recursion"],
            "streak": 3,
            "efficiency_rating": 3.8,
            "style_rating": 4.4
        }
    ]
    return jsonify({"success": True, "leaderboard": detailed_data})

@app.route('/api/game/trivia/questions')
def trivia_questions():
    """Get trivia questions for trivia game mode"""
    questions = [
        {
            "id": "1",
            "question": "What is the time complexity of binary search?",
            "options": ["O(n)", "O(log n)", "O(n log n)", "O(n²)"],
            "correctAnswer": 1,
            "difficulty": "easy",
            "category": "algorithms",
            "explanation": "Binary search eliminates half of the search space in each iteration, resulting in O(log n) time complexity.",
            "points": 10
        },
        {
            "id": "2",
            "question": "Which data structure uses LIFO (Last In, First Out) principle?",
            "options": ["Queue", "Stack", "Array", "Linked List"],
            "correctAnswer": 1,
            "difficulty": "easy",
            "category": "data-structures",
            "explanation": "Stack follows LIFO principle where the last element added is the first to be removed.",
            "points": 10
        },
        {
            "id": "3",
            "question": "What is the worst-case time complexity of QuickSort?",
            "options": ["O(n)", "O(n log n)", "O(n²)", "O(2^n)"],
            "correctAnswer": 2,
            "difficulty": "medium",
            "category": "algorithms",
            "explanation": "QuickSort has O(n²) worst-case complexity when the pivot is always the smallest or largest element.",
            "points": 20
        },
        {
            "id": "4",
            "question": "Which of these is NOT a valid JavaScript variable declaration?",
            "options": ["var x = 5;", "let x = 5;", "const x = 5;", "int x = 5;"],
            "correctAnswer": 3,
            "difficulty": "easy",
            "category": "programming-concepts",
            "explanation": "JavaScript doesn't have an 'int' keyword for variable declaration.",
            "points": 10
        },
        {
            "id": "5",
            "question": "What does 'Big O' notation describe?",
            "options": ["Best case performance", "Average case performance", "Worst case performance", "Memory usage only"],
            "correctAnswer": 2,
            "difficulty": "medium",
            "category": "cs-theory",
            "explanation": "Big O notation describes the worst-case time or space complexity of an algorithm.",
            "points": 20
        }
    ]
    return jsonify({"success": True, "questions": questions})

@app.route('/api/game/debug/challenges')
def debug_challenges():
    """Get debug challenges for debug game mode"""
    challenges = [
        {
            "id": "1",
            "title": "Array Sum Function",
            "description": "This function should calculate the sum of all elements in an array, but it has bugs.",
            "buggyCode": "function arraySum(arr) {\n    let sum = 0;\n    for (let i = 0; i <= arr.length; i++) {\n        sum += arr[i];\n    }\n    return sum;\n}",
            "expectedOutput": "15",
            "actualOutput": "NaN",
            "language": "javascript",
            "difficulty": "easy",
            "bugs": [
                {
                    "id": "bug1",
                    "line": 3,
                    "type": "logical",
                    "description": "Loop condition should be < instead of <=",
                    "fix": "for (let i = 0; i < arr.length; i++)",
                    "points": 15
                }
            ],
            "hints": [
                "Check the loop condition - are you accessing array elements correctly?",
                "What happens when i equals arr.length?"
            ],
            "totalPoints": 15
        },
        {
            "id": "2",
            "title": "Binary Search Implementation",
            "description": "Binary search with logical and boundary errors.",
            "buggyCode": "function binarySearch(arr, target) {\n    let left = 0;\n    let right = arr.length;\n    \n    while (left < right) {\n        let mid = Math.floor((left + right) / 2);\n        \n        if (arr[mid] == target) {\n            return mid;\n        } else if (arr[mid] < target) {\n            left = mid;\n        } else {\n            right = mid - 1;\n        }\n    }\n    \n    return -1;\n}",
            "expectedOutput": "2",
            "actualOutput": "Infinite loop or incorrect result",
            "language": "javascript",
            "difficulty": "medium",
            "bugs": [
                {
                    "id": "bug1",
                    "line": 3,
                    "type": "logical",
                    "description": "Right boundary should be arr.length - 1",
                    "fix": "let right = arr.length - 1;",
                    "points": 20
                },
                {
                    "id": "bug2",
                    "line": 5,
                    "type": "logical",
                    "description": "Condition should be left <= right",
                    "fix": "while (left <= right) {",
                    "points": 15
                }
            ],
            "hints": [
                "Check the initial right boundary value",
                "What happens when left equals right?"
            ],
            "totalPoints": 35
        }
    ]
    return jsonify({"success": True, "challenges": challenges})

@app.route('/api/game/coding/problems')
def coding_problems():
    """Get coding problems for classic/coding game modes"""
    problems = [
        {
            "id": "1",
            "title": "Two Sum",
            "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
            "difficulty": "easy",
            "tags": ["array", "hash-table"],
            "examples": [
                {
                    "input": "nums = [2,7,11,15], target = 9",
                    "output": "[0,1]",
                    "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."
                }
            ],
            "constraints": [
                "2 <= nums.length <= 10^4",
                "-10^9 <= nums[i] <= 10^9",
                "-10^9 <= target <= 10^9",
                "Only one valid answer exists"
            ],
            "templateCode": {
                "python": "def twoSum(nums, target):\n    # Your solution here\n    pass",
                "javascript": "function twoSum(nums, target) {\n    // Your solution here\n}",
                "java": "public int[] twoSum(int[] nums, int target) {\n    // Your solution here\n}"
            },
            "testCases": [
                {"input": {"nums": [2,7,11,15], "target": 9}, "expected": [0,1]},
                {"input": {"nums": [3,2,4], "target": 6}, "expected": [1,2]},
                {"input": {"nums": [3,3], "target": 6}, "expected": [0,1]}
            ]
        },
        {
            "id": "2",
            "title": "Reverse Integer",
            "description": "Given a signed 32-bit integer x, return x with its digits reversed.",
            "difficulty": "medium",
            "tags": ["math"],
            "examples": [
                {
                    "input": "x = 123",
                    "output": "321"
                },
                {
                    "input": "x = -123",
                    "output": "-321"
                }
            ],
            "constraints": [
                "-2^31 <= x <= 2^31 - 1"
            ],
            "templateCode": {
                "python": "def reverse(x):\n    # Your solution here\n    pass",
                "javascript": "function reverse(x) {\n    // Your solution here\n}",
                "java": "public int reverse(int x) {\n    // Your solution here\n}"
            },
            "testCases": [
                {"input": {"x": 123}, "expected": 321},
                {"input": {"x": -123}, "expected": -321},
                {"input": {"x": 120}, "expected": 21}
            ]
        }
    ]
    return jsonify({"success": True, "problems": problems})

@app.route('/api/game/electrical/components')
def electrical_components():
    """Get electrical components for electrical engineering game mode"""
    components = {
        "power": [
            {
                "type": "vcc",
                "label": "VCC (+5V)",
                "symbol": "+",
                "description": "Power supply - provides +5V for circuits",
                "tier": 0,
                "color": "#FF0000"
            },
            {
                "type": "gnd",
                "label": "Ground",
                "symbol": "⏚",
                "description": "Ground reference point",
                "tier": 0,
                "color": "#000000"
            }
        ],
        "basic": [
            {
                "type": "resistor",
                "label": "Resistor",
                "symbol": "R",
                "description": "Basic resistor component",
                "tier": 0,
                "color": "#8B4513"
            },
            {
                "type": "capacitor",
                "label": "Capacitor", 
                "symbol": "C",
                "description": "Basic capacitor component",
                "tier": 0,
                "color": "#4169E1"
            },
            {
                "type": "led",
                "label": "LED",
                "symbol": "D",
                "description": "Light emitting diode",
                "tier": 0,
                "color": "#FFD700"
            }
        ],
        "logic": [
            {
                "type": "and_gate",
                "label": "AND Gate",
                "symbol": "&",
                "description": "Logic AND gate",
                "tier": 1,
                "color": "#32CD32",
                "prerequisites": ["vcc", "gnd"]
            },
            {
                "type": "or_gate",
                "label": "OR Gate",
                "symbol": "≥1",
                "description": "Logic OR gate",
                "tier": 1,
                "color": "#32CD32",
                "prerequisites": ["vcc", "gnd"]
            }
        ]
    }
    return jsonify({"success": True, "components": components})

# AI Grading Endpoints
@app.route('/api/grade/coding', methods=['POST'])
def grade_coding_solution():
    """Grade a coding solution using AI"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        problem_id = data.get('problem_id')
        code = data.get('code', '')
        language = data.get('language', 'python')
        test_results = data.get('test_results', {})
        
        if not code.strip():
            return jsonify({'success': False, 'message': 'No code provided'}), 400

        # Simulate AI grading (in production, this would call the actual AI grader)
        grade_result = simulate_coding_grade(code, language, test_results)
        
        return jsonify({
            'success': True,
            'grade': grade_result
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Grading failed: {str(e)}'}), 500

@app.route('/api/grade/trivia', methods=['POST'])
def grade_trivia_answer():
    """Grade a trivia answer"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        question_id = data.get('question_id')
        selected_answer = data.get('selected_answer')
        correct_answer = data.get('correct_answer')
        time_taken = data.get('time_taken', 30)
        
        # Calculate trivia score
        is_correct = selected_answer == correct_answer
        base_points = 10 if is_correct else 0
        time_bonus = max(0, (30 - time_taken) / 5) if is_correct else 0
        total_points = base_points + time_bonus
        
        grade_result = {
            'correct': is_correct,
            'points_earned': round(total_points, 1),
            'time_bonus': round(time_bonus, 1),
            'feedback': 'Correct!' if is_correct else f'Incorrect. The correct answer was option {correct_answer + 1}.',
            'accuracy': 100 if is_correct else 0
        }
        
        return jsonify({
            'success': True,
            'grade': grade_result
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Grading failed: {str(e)}'}), 500

@app.route('/api/grade/debug', methods=['POST'])
def grade_debug_solution():
    """Grade a debug challenge solution"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        challenge_id = data.get('challenge_id')
        bug_fixes = data.get('bug_fixes', [])  # List of bug fixes attempted
        time_taken = data.get('time_taken', 0)
        hints_used = data.get('hints_used', 0)
        
        # Calculate debug score
        bugs_found = len([fix for fix in bug_fixes if fix.get('correct', False)])
        total_bugs = len(bug_fixes)
        
        base_points = bugs_found * 15  # 15 points per bug found
        time_bonus = max(0, (300 - time_taken) / 60 * 2) if bugs_found > 0 else 0  # Time bonus
        hint_penalty = hints_used * 5  # 5 point penalty per hint
        
        total_points = max(0, base_points + time_bonus - hint_penalty)
        accuracy = (bugs_found / max(1, total_bugs)) * 100
        
        grade_result = {
            'bugs_found': bugs_found,
            'total_bugs': total_bugs,
            'points_earned': round(total_points, 1),
            'time_bonus': round(time_bonus, 1),
            'hint_penalty': hint_penalty,
            'accuracy': round(accuracy, 1),
            'feedback': f'Found {bugs_found}/{total_bugs} bugs. {"Excellent debugging!" if bugs_found == total_bugs else "Good effort! Keep practicing your debugging skills."}',
            'efficiency_rating': calculate_debug_efficiency(time_taken, bugs_found, hints_used)
        }
        
        return jsonify({
            'success': True,
            'grade': grade_result
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Grading failed: {str(e)}'}), 500

@app.route('/api/grade/electrical', methods=['POST'])
def grade_electrical_circuit():
    """Grade an electrical engineering circuit"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        circuit_data = data.get('circuit', {})
        components = circuit_data.get('components', [])
        connections = circuit_data.get('connections', [])
        target_functionality = data.get('target_functionality', '')
        
        # Analyze circuit
        circuit_analysis = analyze_electrical_circuit(components, connections, target_functionality)
        
        grade_result = {
            'functionality_score': circuit_analysis['functionality'],
            'design_score': circuit_analysis['design'],
            'efficiency_score': circuit_analysis['efficiency'],
            'total_points': circuit_analysis['total_points'],
            'feedback': circuit_analysis['feedback'],
            'circuit_valid': circuit_analysis['valid'],
            'power_consumption': circuit_analysis['power_consumption'],
            'component_count': len(components),
            'suggestions': circuit_analysis['suggestions']
        }
        
        return jsonify({
            'success': True,
            'grade': grade_result
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Grading failed: {str(e)}'}), 500

# Helper functions for AI grading simulation
def simulate_coding_grade(code: str, language: str, test_results: Dict) -> Dict[str, Any]:
    """Simulate AI grading for coding solutions"""
    # Basic analysis
    lines = code.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    
    # Calculate scores based on code analysis
    correctness = calculate_correctness_score(test_results)
    efficiency = analyze_code_efficiency(code, language)
    readability = analyze_code_readability(code)
    style = analyze_code_style(code, language)
    
    total_score = correctness + efficiency + readability + style
    grade_letter = calculate_letter_grade(total_score)
    
    return {
        'correctness': correctness,
        'efficiency': efficiency,
        'readability': readability,
        'style': style,
        'total_score': round(total_score, 1),
        'grade_letter': grade_letter,
        'feedback': {
            'correctness': generate_correctness_feedback(correctness, test_results),
            'efficiency': generate_efficiency_feedback(efficiency),
            'readability': generate_readability_feedback(readability),
            'style': generate_style_feedback(style, language)
        },
        'suggestions': generate_code_suggestions(code, language),
        'complexity_analysis': analyze_time_complexity(code),
        'line_count': len(non_empty_lines),
        'character_count': len(code)
    }

def calculate_correctness_score(test_results: Dict) -> float:
    """Calculate correctness score from test results"""
    if not test_results:
        return 0.0
    
    passed = test_results.get('passed', 0)
    total = test_results.get('total', 1)
    
    if total == 0:
        return 0.0
    
    pass_rate = passed / total
    return pass_rate * 40  # Max 40 points for correctness

def analyze_code_efficiency(code: str, language: str) -> float:
    """Analyze code efficiency"""
    score = 20  # Base score
    
    # Penalize nested loops
    nested_loop_count = code.count('for') + code.count('while')
    if nested_loop_count > 2:
        score -= (nested_loop_count - 2) * 5
    
    # Bonus for efficient patterns
    if 'dict' in code or 'set' in code:
        score += 3  # Bonus for using efficient data structures
    
    return max(5, min(25, score))

def analyze_code_readability(code: str) -> float:
    """Analyze code readability"""
    score = 15  # Base score
    
    lines = code.split('\n')
    
    # Check for comments
    comment_lines = [line for line in lines if '#' in line]
    if comment_lines:
        score += 3
    
    # Check for meaningful variable names (heuristic)
    if len([word for word in code.split() if len(word) > 3]) > 5:
        score += 2
    
    return min(20, score)

def analyze_code_style(code: str, language: str) -> float:
    """Analyze code style"""
    score = 8  # Base score
    
    if language.lower() == 'python':
        # Check for snake_case
        if '_' in code and not any(c.isupper() for c in code.split('def')[0]):
            score += 2
        
        # Check for proper function definitions
        if 'def ' in code:
            score += 1
    
    return min(10, score)

def calculate_letter_grade(total_score: float) -> str:
    """Calculate letter grade from total score"""
    if total_score >= 90: return 'A+'
    elif total_score >= 85: return 'A'
    elif total_score >= 80: return 'B+'
    elif total_score >= 75: return 'B'
    elif total_score >= 70: return 'C+'
    elif total_score >= 65: return 'C'
    elif total_score >= 60: return 'D'
    else: return 'F'

def generate_correctness_feedback(score: float, test_results: Dict) -> str:
    """Generate feedback for correctness"""
    if score >= 35:
        return "Excellent! Your solution passes all test cases correctly."
    elif score >= 25:
        return "Good work! Your solution handles most cases with minor issues."
    elif score >= 15:
        return "Your solution has the right approach but fails some test cases."
    else:
        return "Your solution needs significant improvement to handle the test cases."

def generate_efficiency_feedback(score: float) -> str:
    """Generate feedback for efficiency"""
    if score >= 20:
        return "Great efficiency! Your algorithm runs optimally."
    elif score >= 15:
        return "Good efficiency with room for minor optimizations."
    else:
        return "Consider optimizing your algorithm for better performance."

def generate_readability_feedback(score: float) -> str:
    """Generate feedback for readability"""
    if score >= 16:
        return "Excellent readability! Code is clear and well-structured."
    elif score >= 12:
        return "Good readability with minor areas for improvement."
    else:
        return "Consider improving variable names and adding comments."

def generate_style_feedback(score: float, language: str) -> str:
    """Generate feedback for style"""
    if score >= 8:
        return f"Great adherence to {language} style conventions!"
    elif score >= 6:
        return f"Good style with minor {language} convention issues."
    else:
        return f"Review {language} style guidelines for improvement."

def generate_code_suggestions(code: str, language: str) -> list:
    """Generate improvement suggestions"""
    suggestions = []
    
    if '#' not in code:
        suggestions.append("Add comments to explain your logic")
    
    if language.lower() == 'python':
        if 'def ' not in code and len(code.split('\n')) > 5:
            suggestions.append("Consider breaking code into functions")
        
        if any(c.isupper() for c in code.replace('def', '').replace('class', '')):
            suggestions.append("Use snake_case for variable names in Python")
    
    if 'for' in code and 'while' in code:
        suggestions.append("Review if nested loops are necessary")
    
    return suggestions

def analyze_time_complexity(code: str) -> str:
    """Analyze time complexity of code"""
    nested_loops = code.count('for') + code.count('while')
    
    if nested_loops >= 3:
        return f"O(n^{nested_loops})"
    elif nested_loops == 2:
        return "O(n²)"
    elif nested_loops == 1:
        return "O(n)"
    else:
        return "O(1)"

def calculate_debug_efficiency(time_taken: int, bugs_found: int, hints_used: int) -> str:
    """Calculate debugging efficiency rating"""
    if bugs_found == 0:
        return "Needs Improvement"
    
    efficiency_score = (bugs_found * 60) - (time_taken / 10) - (hints_used * 10)
    
    if efficiency_score >= 80:
        return "Excellent"
    elif efficiency_score >= 60:
        return "Good"
    elif efficiency_score >= 40:
        return "Average"
    else:
        return "Needs Improvement"

def analyze_electrical_circuit(components: list, connections: list, target: str) -> Dict:
    """Analyze electrical circuit design"""
    # Basic circuit analysis
    has_power = any(comp.get('type') == 'vcc' for comp in components)
    has_ground = any(comp.get('type') == 'gnd' for comp in components)
    has_output = any(comp.get('type') == 'led' for comp in components)
    
    functionality_score = 0
    if has_power: functionality_score += 30
    if has_ground: functionality_score += 30
    if has_output: functionality_score += 20
    if len(connections) > 0: functionality_score += 20
    
    design_score = min(25, len(components) * 5)  # Points for component variety
    efficiency_score = max(5, 20 - len(components))  # Fewer components = more efficient
    
    total_points = functionality_score + design_score + efficiency_score
    
    feedback = "Circuit analysis: "
    if not has_power:
        feedback += "Missing power source. "
    if not has_ground:
        feedback += "Missing ground connection. "
    if len(connections) == 0:
        feedback += "No connections found. "
    if has_power and has_ground and has_output:
        feedback += "Good basic circuit structure!"
    
    suggestions = []
    if not has_power:
        suggestions.append("Add a VCC power source")
    if not has_ground:
        suggestions.append("Add a ground connection")
    if len(connections) < 2:
        suggestions.append("Connect your components with wires")
    
    return {
        'functionality': functionality_score,
        'design': design_score,
        'efficiency': efficiency_score,
        'total_points': total_points,
        'feedback': feedback,
        'valid': has_power and has_ground,
        'power_consumption': estimate_power_consumption(components),
        'suggestions': suggestions
    }

def estimate_power_consumption(components: list) -> str:
    """Estimate circuit power consumption"""
    power = 0
    for comp in components:
        comp_type = comp.get('type', '')
        if comp_type == 'led':
            power += 20  # 20mA for LED
        elif comp_type in ['and_gate', 'or_gate']:
            power += 5   # 5mA for logic gates
    
    return f"{power}mA" if power > 0 else "Unknown"

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400

        # Handle both email and username login
        identifier = data.get('email') or data.get('username')
        password = data.get('password')
        
        if not identifier or not password:
            return jsonify({'message': 'Email/username and password required'}), 400

        # Find user by email or username
        user = None
        for key, user_data in users_db.items():
            if key == identifier or user_data.get('username') == identifier:
                user = user_data
                break
        
        if not user or user['password'] != password:
            return jsonify({'message': 'Invalid credentials'}), 401

        # Create JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'college': user['college'],
                'rank': user.get('rank', 'Student')
            }
        })
    except Exception as e:
        return jsonify({'message': 'Login failed', 'error': str(e)}), 500

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400

        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        
        if not email or not username or not password:
            return jsonify({'message': 'Email, username, and password required'}), 400

        # Check if user already exists
        if email in users_db:
            return jsonify({'message': 'Email already registered'}), 400
        
        for user_data in users_db.values():
            if user_data.get('username') == username:
                return jsonify({'message': 'Username already taken'}), 400

        # Create new user
        new_user_id = len(users_db) + 1
        users_db[email] = {
            'id': new_user_id,
            'email': email,
            'username': username,
            'password': password,  # In real app, this would be hashed
            'college': 'Default College',
            'rank': 'Student'
        }

        return jsonify({
            'message': 'Registration successful',
            'user': {
                'id': new_user_id,
                'username': username,
                'email': email,
                'college': 'Default College',
                'rank': 'Student'
            }
        })
    except Exception as e:
        return jsonify({'message': 'Registration failed', 'error': str(e)}), 500

@app.route('/api/profile', methods=['GET'])
def profile():
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'message': 'No token provided'}), 401

        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
            
            # Find user by ID
            user = None
            for user_data in users_db.values():
                if user_data['id'] == user_id:
                    user = user_data
                    break
            
            if not user:
                return jsonify({'message': 'User not found'}), 404

            # Generate statistics based on user
            if user['username'] == 'Normbeezy':
                stats = {
                    'totalScore': 99999,
                    'gamesPlayed': 100,
                    'winRate': 100.0,
                    'rank': 1  # Leaderboard position
                }
            elif user['username'] == 'admin':
                stats = {
                    'totalScore': 5000,
                    'gamesPlayed': 25,
                    'winRate': 80.0,
                    'rank': 7
                }
            else:
                stats = {
                    'totalScore': 1200,
                    'gamesPlayed': 15,
                    'winRate': 60.0,
                    'rank': 15
                }

            return jsonify({
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'college': user['college'],
                'userRank': user.get('rank', 'Student'),  # User role/status
                'totalScore': stats['totalScore'],
                'gamesPlayed': stats['gamesPlayed'],
                'winRate': stats['winRate'],
                'rank': stats['rank']  # Leaderboard position
            })
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'message': 'Profile fetch failed', 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting CS Gauntlet Backend on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)