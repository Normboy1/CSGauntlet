#!/usr/bin/env python3
"""
Minimal test to check if the backend can start
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_imports():
    """Test if we can import the main modules"""
    try:
        print("Testing imports...")
        
        # Test basic Flask import
        from flask import Flask
        print("✅ Flask import successful")
        
        # Test config import
        from backend.config import Config
        print("✅ Config import successful")
        
        # Test models import
        from backend.backend.models import User, Problem
        print("✅ Models import successful")
        
        # Test enhanced app import
        from backend.backend.enhanced_app import create_enhanced_app
        print("✅ Enhanced app import successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_app_creation():
    """Test if we can create the Flask app"""
    try:
        print("\nTesting app creation...")
        
        from backend.backend.enhanced_app import create_enhanced_app
        from backend.config import DevelopmentConfig
        
        app = create_enhanced_app(DevelopmentConfig)
        print("✅ App creation successful")
        
        # Test app context
        with app.app_context():
            print("✅ App context working")
            
        return True
        
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 CS Gauntlet Backend Test")
    print("=" * 30)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed")
        return False
    
    # Test app creation
    if not test_app_creation():
        print("\n❌ App creation tests failed")
        return False
    
    print("\n✅ All tests passed! Backend should be able to start.")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
