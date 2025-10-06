print("[DEBUG] Starting run.py...")
import os
print("[DEBUG] Importing backend...")
from backend.backend import create_app, socketio

print("[DEBUG] Creating app...")
app = create_app()
print("[DEBUG] App created successfully!")

if __name__ == '__main__':
    print("[DEBUG] Entering main block...")
    port = int(os.environ.get('PORT', 5001))
    print(f"[DEBUG] Using port: {port}")
    if os.environ.get('FLASK_ENV') == 'production':
        # In production, use gunicorn with socketio
        import eventlet
        eventlet.monkey_patch()
        socketio.run(app, host='0.0.0.0', port=port, debug=False)
    else:
        # In development, use Flask's built-in server
        print(f"[DEBUG] Starting development server on port {port}...")
        socketio.run(app, host='0.0.0.0', port=port, debug=True)
