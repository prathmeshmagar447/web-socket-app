import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from web.app import app, socketio

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
