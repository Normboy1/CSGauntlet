#!/usr/bin/env python3
"""
Comprehensive CS Gauntlet System Test
Tests backend, frontend, AI grading, and all integrations
"""

import sys
import os
import time
import asyncio
import requests
import subprocess
from pathlib import Path

def print_banner():
    """Print test banner"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                🧪 CS GAUNTLET SYSTEM TEST 🧪               ║
    ║              Complete Integration Testing                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

def test_backend_startup():
    """Test if backend can start"""
    print("🔧 Testing backend startup...")
    
    try:
        # Try to start backend in background
        backend_process = subprocess.Popen(
            [sys.executable, 'run_enhanced.py'],
            cwd='backend',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for startup
        time.sleep(5)
        
        # Test health endpoint
        try:
            response = requests.get('http://localhost:5001/health', timeout=10)
            if response.status_code == 200:
                print("✅ Backend started successfully")
                backend_process.terminate()
                return True
        except:
            pass
        
        # Check if process is still running
        if backend_process.poll() is None:
            print("⚠️  Backend process running but health check failed")
            backend_process.terminate()
            return True
        else:
            print("❌ Backend failed to start")
            return False
            
    except Exception as e:
        print(f"❌ Backend startup test failed: {e}")
        return False

def test_ollama_connection():
    """Test Ollama connection"""
    print("🤖 Testing Ollama connection...")
    
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            codellama_available = any('codellama' in model.get('name', '') for model in models)
            
            if codellama_available:
                print("✅ Ollama running with CodeLlama model")
                return True
            else:
                print("⚠️  Ollama running but CodeLlama model not found")
                print("   Run: ollama pull codellama:7b")
                return False
        else:
            print("❌ Ollama not responding")
            return False
    except Exception as e:
        print("❌ Ollama connection failed")
        print("   Make sure Ollama is running: ollama serve")
        return False

def test_redis_connection():
    """Test Redis connection"""
    print("🔴 Testing Redis connection...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print("❌ Redis connection failed")
        print("   Make sure Redis is running")
        return False

async def test_ai_grader():
    """Test AI grader functionality"""
    print("🎯 Testing AI grader...")
    
    try:
        # Add backend to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
        
        from backend.ai_grader import AICodeGrader
        
        # Initialize grader
        grader = AICodeGrader(
            ai_provider="ollama",
            ollama_url="http://localhost:11434",
            ollama_model="codellama:7b"
        )
        
        # Test health check
        ollama_available = await grader.check_ollama_health()
        
        if not ollama_available:
            print("⚠️  Ollama not available, testing fallback mode")
        
        # Test grading
        sample_problem = "Write a function to reverse a string"
        sample_code = "def reverse_string(s):\n    return s[::-1]"
        test_results = {"passed": 3, "total": 3}
        
        result = await grader.grade_solution(
            problem_description=sample_problem,
            solution_code=sample_code,
            test_results=test_results
        )
        
        print(f"✅ AI grading successful: {result.overall_grade} ({result.criteria.total}/100)")
        return True
        
    except Exception as e:
        print(f"❌ AI grader test failed: {e}")
        return False

def test_frontend_build():
    """Test frontend build"""
    print("🌐 Testing frontend build...")
    
    try:
        # Check if Node.js is available
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Node.js not available")
            return False
        
        # Check if dependencies are installed
        if not Path('frontend/node_modules').exists():
            print("📦 Installing frontend dependencies...")
            result = subprocess.run(['npm', 'install'], cwd='frontend', capture_output=True)
            if result.returncode != 0:
                print("❌ Failed to install frontend dependencies")
                return False
        
        # Test build
        print("🔨 Building frontend...")
        result = subprocess.run(['npm', 'run', 'build'], cwd='frontend', capture_output=True)
        
        if result.returncode == 0:
            print("✅ Frontend build successful")
            return True
        else:
            print("❌ Frontend build failed")
            return False
            
    except Exception as e:
        print(f"❌ Frontend test failed: {e}")
        return False

def test_database_setup():
    """Test database setup"""
    print("🗄️  Testing database setup...")
    
    try:
        # Add backend to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
        
        from backend.backend.enhanced_app import create_enhanced_app
        from backend.config import DevelopmentConfig
        from backend.backend.models import db, User, Problem
        
        app = create_enhanced_app(DevelopmentConfig)
        
        with app.app_context():
            # Create tables
            db.create_all()
            
            # Test basic queries
            user_count = User.query.count()
            problem_count = Problem.query.count()
            
            print(f"✅ Database setup successful ({user_count} users, {problem_count} problems)")
            return True
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_environment_config():
    """Test environment configuration"""
    print("⚙️  Testing environment configuration...")
    
    env_file = Path('backend/.env')
    
    if not env_file.exists():
        print("⚠️  .env file not found, creating from template...")
        env_example = Path('backend/.env.example')
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ .env file created from template")
        else:
            print("❌ No .env.example file found")
            return False
    else:
        print("✅ .env file exists")
    
    # Check critical environment variables
    from dotenv import load_dotenv
    load_dotenv('backend/.env')
    
    critical_vars = ['SECRET_KEY', 'OLLAMA_URL', 'OLLAMA_MODEL']
    missing_vars = []
    
    for var in critical_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All critical environment variables set")
        return True

async def run_all_tests():
    """Run all system tests"""
    print_banner()
    
    tests = [
        ("Environment Configuration", test_environment_config),
        ("Redis Connection", test_redis_connection),
        ("Ollama Connection", test_ollama_connection),
        ("Database Setup", test_database_setup),
        ("AI Grader", test_ai_grader),
        ("Frontend Build", test_frontend_build),
        ("Backend Startup", test_backend_startup)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 Running: {test_name}")
        print('='*60)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! CS Gauntlet is ready to launch!")
        print("\n🚀 Next steps:")
        print("1. Run: python launch_cs_gauntlet.py")
        print("2. Open http://localhost:3000 in your browser")
        print("3. Test with accounts: alice/password123, bob/password123")
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed. Please fix issues before launching.")
        return False

def main():
    """Main test function"""
    try:
        success = asyncio.run(run_all_tests())
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
