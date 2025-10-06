#!/usr/bin/env python3
print("Starting test server...")

try:
    print("Testing Flask import...")
    from flask import Flask
    print("Flask imported successfully")
    
    print("Testing backend import...")
    from backend import create_app, socketio
    print("Backend imported successfully")
    
    print("Creating app...")
    app = create_app()
    print("App created successfully")
    
    print("Starting server on port 8000...")
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
