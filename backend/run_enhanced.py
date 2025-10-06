"""
Run script for enhanced CS Gauntlet application
Tests game functionality before adding security features
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from backend.enhanced_app import create_enhanced_app, socketio
from backend.models import db, User, Problem
from config import DevelopmentConfig, ProductionConfig

def create_sample_data(app):
    """Create sample data for testing"""
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if we already have data
        if User.query.first() and Problem.query.first():
            print("📊 Sample data already exists")
            return
        
        print("📊 Creating sample data...")
        
        # Create sample users
        users = [
            {
                'username': 'alice',
                'email': 'alice@example.com',
                'college_name': 'MIT',
                'password': 'password123'
            },
            {
                'username': 'bob',
                'email': 'bob@example.com', 
                'college_name': 'Stanford',
                'password': 'password123'
            },
            {
                'username': 'charlie',
                'email': 'charlie@example.com',
                'college_name': 'Berkeley',
                'password': 'password123'
            }
        ]
        
        for user_data in users:
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    college_name=user_data['college_name']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
        
        # Create sample problems
        problems = [
            {
                'title': 'Two Sum',
                'description': 'Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.',
                'example': 'Input: nums = [2,7,11,15], target = 9\nOutput: [0,1]\nExplanation: Because nums[0] + nums[1] == 9, we return [0, 1].',
                'solution': 'def twoSum(nums, target):\n    num_map = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in num_map:\n            return [num_map[complement], i]\n        num_map[num] = i\n    return []',
                'difficulty': 'easy'
            },
            {
                'title': 'Reverse String',
                'description': 'Write a function that reverses a string. The input string is given as an array of characters s.',
                'example': 'Input: s = ["h","e","l","l","o"]\nOutput: ["o","l","l","e","h"]',
                'solution': 'def reverseString(s):\n    left, right = 0, len(s) - 1\n    while left < right:\n        s[left], s[right] = s[right], s[left]\n        left += 1\n        right -= 1',
                'difficulty': 'easy'
            },
            {
                'title': 'Valid Parentheses',
                'description': 'Given a string s containing just the characters "(", ")", "{", "}", "[" and "]", determine if the input string is valid.',
                'example': 'Input: s = "()"\nOutput: true\n\nInput: s = "()[]{}"\nOutput: true\n\nInput: s = "(]"\nOutput: false',
                'solution': 'def isValid(s):\n    stack = []\n    mapping = {")": "(", "}": "{", "]": "["}\n    for char in s:\n        if char in mapping:\n            if not stack or stack.pop() != mapping[char]:\n                return False\n        else:\n            stack.append(char)\n    return not stack',
                'difficulty': 'easy'
            },
            {
                'title': 'Binary Search',
                'description': 'Given an array of integers nums which is sorted in ascending order, and an integer target, write a function to search target in nums.',
                'example': 'Input: nums = [-1,0,3,5,9,12], target = 9\nOutput: 4\nExplanation: 9 exists in nums and its index is 4',
                'solution': 'def search(nums, target):\n    left, right = 0, len(nums) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        if nums[mid] == target:\n            return mid\n        elif nums[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    return -1',
                'difficulty': 'medium'
            },
            {
                'title': 'Fibonacci Number',
                'description': 'The Fibonacci numbers, commonly denoted F(n) form a sequence, called the Fibonacci sequence, such that each number is the sum of the two preceding ones.',
                'example': 'Input: n = 2\nOutput: 1\nExplanation: F(2) = F(1) + F(0) = 1 + 0 = 1.',
                'solution': 'def fib(n):\n    if n <= 1:\n        return n\n    a, b = 0, 1\n    for i in range(2, n + 1):\n        a, b = b, a + b\n    return b',
                'difficulty': 'easy'
            }
        ]
        
        for problem_data in problems:
            if not Problem.query.filter_by(title=problem_data['title']).first():
                problem = Problem(**problem_data)
                db.session.add(problem)
        
        try:
            db.session.commit()
            print("✅ Sample data created successfully")
            print(f"👥 Users: {User.query.count()}")
            print(f"📚 Problems: {Problem.query.count()}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating sample data: {e}")

def main():
    """Main application entry point"""
    
    print("🎮 CS Gauntlet - Enhanced Game Server")
    print("=" * 40)
    
    # Determine environment
    env = os.getenv('FLASK_ENV', 'development')
    
    if env == 'production':
        config = ProductionConfig
        print("🌍 Running in PRODUCTION mode")
    else:
        config = DevelopmentConfig
        print("🔧 Running in DEVELOPMENT mode")
    
    # Create application
    print("🚀 Creating application...")
    app = create_enhanced_app(config)
    
    # Create sample data
    create_sample_data(app)
    
    # Print configuration info
    print(f"📡 Socket.IO enabled: {socketio is not None}")
    print(f"🗄️  Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    print(f"🔄 Redis: {app.config.get('REDIS_URL', 'Not configured')}")
    
    # Print available routes
    print("\n🛣️  Available routes:")
    with app.app_context():
        for rule in app.url_map.iter_rules():
            if not rule.rule.startswith('/static'):
                methods = ','.join(rule.methods - {'OPTIONS', 'HEAD'})
                print(f"   {rule.rule} [{methods}]")
    
    # Print test credentials
    print("\n🔑 Test Credentials:")
    print("   Username: alice    Password: password123")
    print("   Username: bob      Password: password123")
    print("   Username: charlie  Password: password123")
    
    print("\n🌐 Starting server...")
    print("   Frontend: http://localhost:3000")
    print("   Backend:  http://localhost:5001")
    print("   Game Socket: ws://localhost:5001")
    
    try:
        # Run the application
        if socketio:
            # Run with SocketIO
            socketio.run(
                app,
                debug=(env == 'development'),
                host='0.0.0.0',
                port=5001,
                use_reloader=False  # Disable reloader to prevent duplicate processes
            )
        else:
            # Fallback to regular Flask
            app.run(
                debug=(env == 'development'),
                host='0.0.0.0',
                port=5001
            )
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n💥 Server error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()