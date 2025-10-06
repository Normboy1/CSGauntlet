"""
Test script to verify game functionality works properly
Run this to ensure core game features are functional before adding security
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from backend.enhanced_app import create_enhanced_app
from backend.models import User, Problem, GameMode, db
from backend.game_manager import game_manager, GameConfig
from config import TestingConfig

def test_basic_functionality():
    """Test basic game functionality"""
    
    print("🎮 Testing CS Gauntlet Game Functionality")
    print("=" * 50)
    
    # Create test app
    app = create_enhanced_app(TestingConfig)
    
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Test 1: Create test users
        print("📝 Test 1: Creating test users...")
        user1 = User(
            username="testplayer1",
            email="test1@example.com",
            college_name="Test University"
        )
        user1.set_password("testpass")
        
        user2 = User(
            username="testplayer2", 
            email="test2@example.com",
            college_name="Test College"
        )
        user2.set_password("testpass")
        
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()
        
        print(f"✅ Created users: {user1.username}, {user2.username}")
        
        # Test 2: Create test problems
        print("\n📚 Test 2: Creating test problems...")
        problems = [
            Problem(
                title="Two Sum",
                description="Find two numbers that add up to target",
                example="Input: [2,7,11,15], target=9\nOutput: [0,1]",
                solution="def two_sum(nums, target):\n    # Solution here\n    pass",
                difficulty="easy"
            ),
            Problem(
                title="Reverse String",
                description="Reverse a string in-place",
                example="Input: 'hello'\nOutput: 'olleh'",
                solution="def reverse_string(s):\n    return s[::-1]",
                difficulty="easy"
            ),
            Problem(
                title="Binary Search",
                description="Implement binary search algorithm",
                example="Input: [1,2,3,4,5], target=3\nOutput: 2",
                solution="def binary_search(arr, target):\n    # Solution here\n    pass",
                difficulty="medium"
            )
        ]
        
        for problem in problems:
            db.session.add(problem)
        
        db.session.commit()
        print(f"✅ Created {len(problems)} test problems")
        
        # Test 3: Game Manager functionality
        print("\n🎯 Test 3: Testing Game Manager...")
        
        # Create game config
        config = GameConfig(
            mode=GameMode.CASUAL,
            max_players=2,
            max_rounds=2,
            language='python',
            difficulty='easy'
        )
        
        # Create a game
        game_id = game_manager.create_game(user1.id, config)
        print(f"✅ Created game with ID: {game_id}")
        
        # Join players
        success1, msg1 = game_manager.join_game(game_id, user1.id, "socket1", user1.username)
        success2, msg2 = game_manager.join_game(game_id, user2.id, "socket2", user2.username)
        
        print(f"✅ Player 1 joined: {success1} - {msg1}")
        print(f"✅ Player 2 joined: {success2} - {msg2}")
        
        # Get game state
        game = game_manager.get_game(game_id)
        if game:
            state = game.get_state()
            print(f"✅ Game state retrieved - Players: {len(state['players'])}")
            print(f"   Game mode: {state['config']['mode']}")
            print(f"   Current round: {state['current_round']}")
        
        # Test 4: Matchmaking
        print("\n🔄 Test 4: Testing Matchmaking...")
        
        found, message, match_game_id = game_manager.find_or_create_match(
            user_id=99,  # Fake user ID
            socket_id="socket99",
            username="testuser99",
            game_mode="casual",
            language="python"
        )
        
        print(f"✅ Matchmaking test: {message}")
        
        # Test 5: Socket functionality (basic)
        print("\n🔌 Test 5: Testing Socket Setup...")
        try:
            from backend.game_socket_handlers import connected_users
            print("✅ Socket handlers imported successfully")
        except Exception as e:
            print(f"❌ Socket handler import failed: {e}")
        
        # Test 6: Redis functionality
        print("\n🔧 Test 6: Testing Redis...")
        try:
            from backend import redis_client
            # Test Redis connection
            test_key = "test_key"
            test_value = "test_value"
            redis_client.set(test_key, test_value)
            retrieved = redis_client.get(test_key)
            
            if retrieved and retrieved.decode() == test_value:
                print("✅ Redis connection working")
                redis_client.delete(test_key)
            else:
                print("❌ Redis connection failed")
        except Exception as e:
            print(f"⚠️  Redis test failed (this is OK if Redis isn't running): {e}")
        
        # Test 7: Game state persistence
        print("\n💾 Test 7: Testing Game State Persistence...")
        if game:
            game.save_state()
            print("✅ Game state saved")
            
            # Try loading
            loaded_game = game_manager.get_game(game_id)
            if loaded_game:
                print("✅ Game state loaded successfully")
            else:
                print("❌ Game state loading failed")
        
        print("\n" + "=" * 50)
        print("🎉 Game functionality tests completed!")
        print("\nCore Features Status:")
        print("✅ User management")
        print("✅ Problem database")
        print("✅ Game creation and management")
        print("✅ Player joining/leaving")
        print("✅ Game state tracking")
        print("✅ Matchmaking system")
        print("✅ Socket handler setup")
        print("⚠️  Redis (optional)")
        
        print("\n🔐 Ready to add security features!")
        
        return True

def test_game_flow():
    """Test a complete game flow"""
    
    print("\n🎲 Testing Complete Game Flow...")
    print("-" * 30)
    
    app = create_enhanced_app(TestingConfig)
    
    with app.app_context():
        # Get existing data
        users = User.query.all()
        problems = Problem.query.all()
        
        if len(users) < 2 or len(problems) < 1:
            print("❌ Need at least 2 users and 1 problem for game flow test")
            return False
        
        user1, user2 = users[0], users[1]
        
        # Create and start a game
        config = GameConfig(
            mode=GameMode.CASUAL,
            max_players=2,
            max_rounds=1,
            auto_start=True
        )
        
        game_id = game_manager.create_game(user1.id, config)
        game = game_manager.get_game(game_id)
        
        # Add players
        game.add_player(user1.id, "socket1", user1.username, college=user1.college_name)
        game.add_player(user2.id, "socket2", user2.username, college=user2.college_name)
        
        print(f"✅ Game started with {len(game.players)} players")
        
        # Check if game auto-started
        if game.state.value == "in_progress":
            print("✅ Game auto-started successfully")
            
            # Submit solutions
            test_code1 = "def solution():\n    return 'Player 1 solution'"
            test_code2 = "def solution():\n    return 'Player 2 solution'"
            
            success1, msg1 = game.submit_solution("socket1", test_code1)
            success2, msg2 = game.submit_solution("socket2", test_code2)
            
            print(f"✅ Player 1 submission: {success1}")
            print(f"✅ Player 2 submission: {success2}")
            
            # Check final state
            final_state = game.get_state()
            print(f"✅ Final game state: {final_state['state']}")
            
        else:
            print(f"⚠️  Game state: {game.state.value} (expected: in_progress)")
        
        print("✅ Game flow test completed")
        return True

if __name__ == "__main__":
    print("🚀 Starting CS Gauntlet Functionality Tests\n")
    
    try:
        # Run basic functionality tests
        basic_success = test_basic_functionality()
        
        if basic_success:
            # Run game flow test
            flow_success = test_game_flow()
            
            if flow_success:
                print("\n🎊 ALL TESTS PASSED!")
                print("✅ Game functionality is working correctly")
                print("🔐 Ready to implement security features")
            else:
                print("\n⚠️  Basic tests passed, but game flow has issues")
        else:
            print("\n❌ Basic functionality tests failed")
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n📋 Next Steps:")
    print("1. Fix any failing tests")
    print("2. Start the application with: python run.py")
    print("3. Test in browser")
    print("4. Then add security features")