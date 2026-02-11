"""
WSGI entry point for production deployment (Gunicorn / Render / Railway)
"""
from app import app, socketio

if __name__ == '__main__':
    socketio.run(app)
