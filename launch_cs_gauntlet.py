#!/usr/bin/env python3
"""
CS Gauntlet Launch Script with Ollama AI Grader
This script helps you launch CS Gauntlet with all components
"""

import os
import sys
import subprocess
import time
import asyncio
import requests
from pathlib import Path

def print_banner():
    """Print CS Gauntlet banner"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                    🎮 CS GAUNTLET 🎮                      ║
    ║              Competitive Programming Platform             ║
    ║                  with Ollama AI Grader                   ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

def check_ollama():
    """Check if Ollama is running"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        return response.status_code == 200
    except:
        return False

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        return True
    except:
        return False

def check_node():
    """Check if Node.js is available"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def setup_environment():
    """Setup environment variables"""
    env_file = Path('backend/.env')
    env_example = Path('backend/.env.example')
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from template...")
        import shutil
        shutil.copy(env_example, env_file)
        print("✅ .env file created. Please edit it with your configuration.")
        return False
    
    return True

def install_dependencies():
    """Install Python and Node.js dependencies"""
    print("📦 Installing dependencies...")
    
    # Install Python dependencies
    print("Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'backend/requirements.txt'], 
                      check=True, cwd=os.getcwd())
        print("✅ Python dependencies installed")
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python dependencies")
        return False
    
    # Install Node.js dependencies
    if check_node():
        print("Installing Node.js dependencies...")
        try:
            subprocess.run(['npm', 'install'], check=True, cwd='frontend')
            print("✅ Node.js dependencies installed")
        except subprocess.CalledProcessError:
            print("❌ Failed to install Node.js dependencies")
            return False
    else:
        print("⚠️  Node.js not found. Please install Node.js for the frontend.")
        return False
    
    return True

def start_ollama():
    """Start Ollama if not running"""
    if not check_ollama():
        print("🤖 Starting Ollama...")
        print("Please run in another terminal: ollama serve")
        print("Then run: ollama pull codellama:7b")
        input("Press Enter when Ollama is running...")
        
        if not check_ollama():
            print("⚠️  Ollama still not accessible. AI grading will use fallback mode.")
            return False
    else:
        print("✅ Ollama is running")
    
    return True

def start_redis():
    """Start Redis if not running"""
    if not check_redis():
        print("🔴 Redis not running. Please start Redis:")
        print("Windows: Download and run Redis from https://redis.io/download")
        print("Linux/Mac: sudo systemctl start redis")
        input("Press Enter when Redis is running...")
        
        if not check_redis():
            print("❌ Redis still not accessible")
            return False
    else:
        print("✅ Redis is running")
    
    return True

def test_system():
    """Test the system components"""
    print("\n🧪 Testing system components...")
    
    try:
        # Test Ollama integration
        result = subprocess.run([sys.executable, 'backend/test_ollama_integration.py'], 
                              capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode == 0:
            print("✅ System tests passed")
            return True
        else:
            print("⚠️  Some tests failed, but system may still work")
            print(result.stdout)
            return True  # Continue anyway
    except Exception as e:
        print(f"⚠️  Test execution failed: {e}")
        return True  # Continue anyway

def start_backend():
    """Start the backend server"""
    print("\n🚀 Starting backend server...")
    
    try:
        # Change to backend directory and start server
        backend_process = subprocess.Popen(
            [sys.executable, 'run_enhanced.py'],
            cwd='backend'
        )
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if server is running
        try:
            response = requests.get('http://localhost:5001/health', timeout=5)
            if response.status_code == 200:
                print("✅ Backend server started successfully")
                return backend_process
        except:
            pass
        
        print("⚠️  Backend server may be starting...")
        return backend_process
        
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the frontend development server"""
    print("\n🌐 Starting frontend server...")
    
    if not check_node():
        print("❌ Node.js not available. Cannot start frontend.")
        return None
    
    try:
        frontend_process = subprocess.Popen(
            ['npm', 'run', 'dev'],
            cwd='frontend'
        )
        
        print("✅ Frontend server starting...")
        return frontend_process
        
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return None

def main():
    """Main launch function"""
    print_banner()
    
    print("🔍 Checking system requirements...")
    
    # Check and setup environment
    if not setup_environment():
        print("Please configure your .env file and run again.")
        return 1
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed")
        return 1
    
    # Start required services
    if not start_redis():
        print("❌ Redis is required for CS Gauntlet")
        return 1
    
    start_ollama()  # Ollama is optional
    
    # Test system
    test_system()
    
    # Start servers
    backend_process = start_backend()
    if not backend_process:
        print("❌ Cannot start without backend server")
        return 1
    
    frontend_process = start_frontend()
    
    # Print launch information
    print("\n" + "="*60)
    print("🎉 CS GAUNTLET LAUNCHED SUCCESSFULLY!")
    print("="*60)
    print("🌐 Frontend: http://localhost:3000")
    print("🔧 Backend:  http://localhost:5001")
    print("🤖 AI Grader: Ollama (codellama:7b)")
    print("🔴 Redis:    localhost:6379")
    print()
    print("📋 Test Accounts:")
    print("   Username: alice    Password: password123")
    print("   Username: bob      Password: password123")
    print("   Username: charlie  Password: password123")
    print()
    print("🎮 Ready to compete! Open http://localhost:3000 in your browser")
    print("="*60)
    
    try:
        print("\nPress Ctrl+C to stop all servers...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        
        print("👋 CS Gauntlet stopped. Thanks for playing!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
