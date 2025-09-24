from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
import sys
import os
import json
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.enhanced_db_manager import enhanced_db
from security.auth_manager import auth_manager
from features.file_transfer import file_transfer_manager
from notifications.email_notifier import email_notifier

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", max_size=100*1024*1024)

# Store active users and their socket IDs
active_users = {}  # user_id -> socket_id
socket_users = {}  # socket_id -> user_info

@app.route('/')
def index():
    """Main chat interface"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html', username=session.get('username'))

@app.route('/login')
def login():
    """Login page"""
    return render_template('login.html')

@app.route('/register')
def register():
    """Registration page"""
    return render_template('register.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """Handle login API request"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'})
    
    # Check rate limiting
    rate_check = auth_manager.check_rate_limit(request.remote_addr, 'login')
    if not rate_check['allowed']:
        return jsonify({
            'success': False, 
            'message': f'Too many login attempts. Try again in {rate_check["reset_time"] - int(datetime.now().timestamp())} seconds'
        })
    
    # Authenticate user
    user = enhanced_db.authenticate_user(username, password)
    if user:
        # Generate JWT token
        token = auth_manager.generate_jwt_token(user['id'], user['username'], user['role'])
        
        # Set session
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['token'] = token
        
        # Update user status
        enhanced_db.update_user_status(user['id'], 'online')
        enhanced_db.log_connection(user['id'], 'web_login', request.remote_addr)
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            },
            'token': token
        })
    else:
        auth_manager.record_failed_attempt(request.remote_addr, username)
        return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """Handle registration API request"""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    # Check rate limiting
    rate_check = auth_manager.check_rate_limit(request.remote_addr, 'register')
    if not rate_check['allowed']:
        return jsonify({
            'success': False,
            'message': f'Registration rate limit exceeded. Try again later.'
        })
    
    # Validate password strength
    password_check = auth_manager.validate_password_strength(password)
    if not password_check['valid']:
        return jsonify({
            'success': False,
            'message': 'Password does not meet requirements',
            'issues': password_check['issues']
        })
    
    # Create user
    user_id = enhanced_db.create_user(username, email, password)
    if user_id:
        # Generate JWT token
        token = auth_manager.generate_jwt_token(user_id, username)
        
        # Set session
        session['user_id'] = user_id
        session['username'] = username
        session['token'] = token
        
        # Log registration
        enhanced_db.log_connection(user_id, 'web_register', request.remote_addr)
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user_id,
                'username': username,
                'email': email
            },
            'token': token
        })
    else:
        return jsonify({'success': False, 'message': 'Username or email already exists'})

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """Handle logout API request"""
    if 'user_id' in session:
        enhanced_db.update_user_status(session['user_id'], 'offline')
        
        # Revoke token
        if 'token' in session:
            auth_manager.revoke_token(session['token'])
    
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/rooms')
def api_get_rooms():
    """Get user's chat rooms"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'})
    
    rooms = enhanced_db.get_user_rooms(session['user_id'])
    return jsonify({'success': True, 'rooms': rooms})

@app.route('/api/rooms', methods=['POST'])
def api_create_room():
    """Create a new chat room"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'})
    
    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')
    password = data.get('password')
    is_private = data.get('is_private', False)
    
    if not name:
        return jsonify({'success': False, 'message': 'Room name is required'})
    
    # Check rate limiting
    rate_check = auth_manager.check_rate_limit(str(session['user_id']), 'room_create')
    if not rate_check['allowed']:
        return jsonify({
            'success': False,
            'message': 'Room creation rate limit exceeded'
        })
    
    room_id = enhanced_db.create_chat_room(name, description, session['user_id'], password, is_private)
    if room_id:
        return jsonify({
            'success': True,
            'message': 'Room created successfully',
            'room_id': room_id,
            'room_name': name
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to create room'})

@app.route('/api/notifications')
def api_get_notifications():
    """Get user's notifications"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'})

    notifications = enhanced_db.get_user_notifications(session['user_id'])
    return jsonify({'success': True, 'notifications': notifications})

# Socket.IO Event Handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    if 'user_id' not in session:
        return False  # Reject connection
    
    user_id = session['user_id']
    username = session['username']
    
    # Store user connection
    active_users[user_id] = request.sid
    socket_users[request.sid] = {
        'user_id': user_id,
        'username': username,
        'connected_at': datetime.now().isoformat()
    }
    
    # Update user status
    enhanced_db.update_user_status(user_id, 'online')
    
    # Join user to their rooms
    user_rooms = enhanced_db.get_user_rooms(user_id)
    for room in user_rooms:
        join_room(str(room['id']))
        # Notify other room members
        emit('user_joined', {
            'user_id': user_id,
            'username': username,
            'room_id': room['id'],
            'timestamp': datetime.now().isoformat()
        }, room=str(room['id']), include_self=False)
    
    print(f"✅ Web user {username} connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    if request.sid in socket_users:
        user_info = socket_users[request.sid]
        user_id = user_info['user_id']
        username = user_info['username']
        
        # Update user status
        enhanced_db.update_user_status(user_id, 'offline')
        
        # Notify rooms about user leaving
        user_rooms = enhanced_db.get_user_rooms(user_id)
        for room in user_rooms:
            emit('user_left', {
                'user_id': user_id,
                'username': username,
                'room_id': room['id'],
                'timestamp': datetime.now().isoformat()
            }, room=str(room['id']), include_self=False)
        
        # Clean up
        if user_id in active_users:
            del active_users[user_id]
        del socket_users[request.sid]
        
        print(f"📱 Web user {username} disconnected")

@socketio.on('join_room')
def handle_join_room(data):
    """Handle joining a room"""
    if request.sid not in socket_users:
        return
    
    user_info = socket_users[request.sid]
    user_id = user_info['user_id']
    username = user_info['username']
    
    room_id = data.get('room_id')
    password = data.get('password')
    
    if enhanced_db.join_room(user_id, room_id, password):
        join_room(str(room_id))
        emit('room_joined', {
            'success': True,
            'room_id': room_id,
            'message': 'Successfully joined room'
        })
        
        # Notify other room members
        emit('user_joined', {
            'user_id': user_id,
            'username': username,
            'room_id': room_id,
            'timestamp': datetime.now().isoformat()
        }, room=str(room_id), include_self=False)
    else:
        emit('room_joined', {
            'success': False,
            'message': 'Failed to join room'
        })

@socketio.on('leave_room')
def handle_leave_room(data):
    """Handle leaving a room"""
    if request.sid not in socket_users:
        return
    
    user_info = socket_users[request.sid]
    room_id = str(data.get('room_id'))
    
    leave_room(room_id)
    emit('room_left', {
        'success': True,
        'room_id': room_id,
        'message': 'Left room successfully'
    })

@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a message to a room"""
    if request.sid not in socket_users:
        return
    
    user_info = socket_users[request.sid]
    user_id = user_info['user_id']
    username = user_info['username']
    
    room_id = data.get('room_id')
    content = data.get('content')
    reply_to_id = data.get('reply_to_id')
    
    if not all([room_id, content]):
        emit('message_error', {'message': 'Room ID and content are required'})
        return
    
    # Check rate limiting
    rate_check = auth_manager.check_rate_limit(str(user_id), 'message')
    if not rate_check['allowed']:
        emit('message_error', {'message': 'Message rate limit exceeded'})
        return
    
    # Save message to database
    message_id = enhanced_db.add_message(
        sender_id=user_id,
        content=content,
        room_id=room_id,
        reply_to_id=reply_to_id
    )
    
    # Broadcast to room
    emit('new_message', {
        'message_id': message_id,
        'sender_id': user_id,
        'sender_username': username,
        'content': content,
        'room_id': room_id,
        'reply_to_id': reply_to_id,
        'timestamp': datetime.now().isoformat()
    }, room=str(room_id))

@socketio.on('send_private_message')
def handle_send_private_message(data):
    """Handle sending a private message"""
    if request.sid not in socket_users:
        return

    user_info = socket_users[request.sid]
    user_id = user_info['user_id']
    username = user_info['username']

    recipient_id = data.get('recipient_id')
    content = data.get('content')
    encrypt = data.get('encrypt', False)

    if not all([recipient_id, content]):
        emit('private_message_error', {'message': 'Recipient ID and content are required'})
        return

    # Save message to database
    message_id = enhanced_db.add_message(
        sender_id=user_id,
        content=content,
        recipient_id=recipient_id,
        encrypt=encrypt
    )

    # Send to recipient if online
    if recipient_id in active_users:
        recipient_sid = active_users[recipient_id]
        emit('new_private_message', {
            'message_id': message_id,
            'sender_id': user_id,
            'sender_username': username,
            'content': content,
            'encrypted': encrypt,
            'timestamp': datetime.now().isoformat()
        }, room=recipient_sid)
    else:
        # Recipient is offline, send email notification if enabled
        recipient = enhanced_db.get_user_by_id(recipient_id)
        if recipient:
            prefs = enhanced_db.get_notification_preferences(recipient_id)
            if prefs.get('email_notifications', True) and prefs.get('message_notifications', True):
                subject = f"New message from {username}"
                body = f"You have received a new private message from {username}:\n\n{content[:200]}{'...' if len(content) > 200 else ''}\n\nLogin to view the full message."
                email_notifier.send_email(recipient['email'], subject, body)

                # Create in-app notification
                enhanced_db.create_notification(
                    user_id=recipient_id,
                    notification_type='private_message',
                    title=f'Message from {username}',
                    message=f'You have a new private message',
                    data={'sender_id': user_id, 'message_id': message_id}
                )

    # Confirm to sender
    emit('private_message_sent', {
        'message_id': message_id,
        'recipient_id': recipient_id,
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('typing_start')
def handle_typing_start(data):
    """Handle typing indicator start"""
    if request.sid not in socket_users:
        return
    
    user_info = socket_users[request.sid]
    room_id = str(data.get('room_id'))
    
    emit('user_typing', {
        'user_id': user_info['user_id'],
        'username': user_info['username'],
        'room_id': room_id,
        'typing': True
    }, room=room_id, include_self=False)

@socketio.on('typing_stop')
def handle_typing_stop(data):
    """Handle typing indicator stop"""
    if request.sid not in socket_users:
        return
    
    user_info = socket_users[request.sid]
    room_id = str(data.get('room_id'))
    
    emit('user_typing', {
        'user_id': user_info['user_id'],
        'username': user_info['username'],
        'room_id': room_id,
        'typing': False
    }, room=room_id, include_self=False)
