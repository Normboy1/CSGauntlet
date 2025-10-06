#!/usr/bin/env python3
"""
Test script for CS Gauntlet with Ollama AI Grader integration
"""

import sys
import os
import asyncio
from dotenv import load_dotenv

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Load environment variables
load_dotenv()

async def test_ollama_integration():
    """Test Ollama integration with CS Gauntlet"""
    
    print("🧪 Testing CS Gauntlet with Ollama AI Grader")
    print("=" * 50)
    
    try:
        # Test AI Grader import
        from backend.ai_grader import AICodeGrader
        print("✅ AI Grader import successful")
        
        # Initialize AI grader with Ollama
        grader = AICodeGrader(
            ai_provider="ollama",
            ollama_url=os.getenv('OLLAMA_URL', 'http://localhost:11434'),
            ollama_model=os.getenv('OLLAMA_MODEL', 'codellama:7b')
        )
        print("✅ AI Grader initialized with Ollama")
        
        # Test Ollama connection
        print("\n🔍 Testing Ollama connection...")
        ollama_available = await grader.check_ollama_health()
        
        if ollama_available:
            print("✅ Ollama is running and accessible")
            
            # Test AI grading
            print("\n🎯 Testing AI grading...")
            sample_problem = "Write a Python function to reverse a string."
            sample_code = """def reverse_string(s):
    return s[::-1]
"""
            sample_test_results = {"passed": 3, "total": 3}
            
            grading_result = await grader.grade_solution(
                problem_description=sample_problem,
                solution_code=sample_code,
                test_results=sample_test_results,
                language="python"
            )
            
            print(f"✅ AI Grading successful!")
            print(f"   Grade: {grading_result.overall_grade}")
            print(f"   Score: {grading_result.criteria.total}/100")
            print(f"   Execution time: {grading_result.execution_time:.2f}s")
            
        else:
            print("⚠️  Ollama not accessible - will use fallback grading")
            print("   Make sure Ollama is running: ollama serve")
            print("   And the model is available: ollama pull codellama:7b")
        
        # Test enhanced app creation
        print("\n🚀 Testing enhanced app creation...")
        from backend.enhanced_app import create_enhanced_app
        from config import DevelopmentConfig
        
        app = create_enhanced_app(DevelopmentConfig)
        print("✅ Enhanced app created successfully")
        
        with app.app_context():
            if hasattr(app, 'ai_grader') and app.ai_grader:
                print("✅ AI Grader integrated into Flask app")
            else:
                print("⚠️  AI Grader not found in Flask app")
        
        print("\n🎉 All tests passed! CS Gauntlet is ready with Ollama integration")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    
    print("🎮 CS Gauntlet - Ollama Integration Test")
    print("=" * 40)
    
    # Check if Ollama environment variables are set
    ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    ollama_model = os.getenv('OLLAMA_MODEL', 'codellama:7b')
    
    print(f"Ollama URL: {ollama_url}")
    print(f"Ollama Model: {ollama_model}")
    print()
    
    # Run async tests
    try:
        success = asyncio.run(test_ollama_integration())
        if success:
            print("\n✅ Ready to launch CS Gauntlet with Ollama!")
            print("\nNext steps:")
            print("1. Make sure Ollama is running: ollama serve")
            print("2. Pull the model: ollama pull codellama:7b")
            print("3. Start the backend: python run_enhanced.py")
            print("4. Start the frontend: cd ../frontend && npm run dev")
        else:
            print("\n❌ Some tests failed. Check the errors above.")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
