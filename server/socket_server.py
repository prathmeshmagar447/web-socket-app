import socket
import threading
import json
import sys
import os
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.db_manager import db

class SocketServer:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.clients = {}  # Dictionary to store client connections
        self.running = False
    
    def start_server(self):
        """Start the socket server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True
            
            print(f"🚀 Socket server started on {self.host}:{self.port}")
            print("Waiting for client connections...")
            
            while self.running:
                try:
                    client_socket, client_address = self.socket.accept()
                    print(f"📱 New client connected from {client_address}")
                    
                    # Start a new thread to handle this client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"❌ Error accepting connection: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Error starting server: {e}")
        finally:
            self.stop_server()
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connection"""
        user_id = None
        username = None
        
        try:
            while self.running:
                # Receive data from client
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                try:
                    # Parse JSON message
                    message = json.loads(data)
                    response = self.process_message(message, client_address, user_id)
                    
                    # Update user_id and username if login was successful
                    if message.get('action') == 'login' and response.get('success'):
                        user_id = response.get('user_id')
                        username = response.get('username')
                        self.clients[client_socket] = {
                            'user_id': user_id,
                            'username': username,
                            'address': client_address
                        }
                    
                    # Send response back to client
                    response_json = json.dumps(response)
                    client_socket.send(response_json.encode('utf-8'))
                    
                except json.JSONDecodeError:
                    error_response = {
                        'success': False,
                        'message': 'Invalid JSON format'
                    }
                    client_socket.send(json.dumps(error_response).encode('utf-8'))
                
        except Exception as e:
            print(f"❌ Error handling client {client_address}: {e}")
        finally:
            # Clean up client connection
            if client_socket in self.clients:
                del self.clients[client_socket]
            if user_id:
                db.log_connection(user_id, 'disconnect', str(client_address[0]))
                print(f"📱 Client {username} ({client_address}) disconnected")
            client_socket.close()
    
    def process_message(self, message, client_address, user_id):
        """Process different types of messages from clients"""
        action = message.get('action')
        
        if action == 'register':
            return self.handle_register(message, client_address)
        elif action == 'login':
            return self.handle_login(message, client_address)
        elif action == 'send_message':
            return self.handle_send_message(message, user_id)
        elif action == 'get_messages':
            return self.handle_get_messages()
        elif action == 'get_users':
            return self.handle_get_users()
        elif action == 'ping':
            return {'success': True, 'message': 'pong', 'timestamp': datetime.now().isoformat()}
        else:
            return {'success': False, 'message': 'Unknown action'}
    
    def handle_register(self, message, client_address):
        """Handle user registration"""
        username = message.get('username')
        email = message.get('email')
        
        if not username or not email:
            return {'success': False, 'message': 'Username and email are required'}
        
        user_id = db.create_user(username, email)
        if user_id:
            db.log_connection(user_id, 'register', str(client_address[0]))
            return {
                'success': True,
                'message': 'User registered successfully',
                'user_id': user_id
            }
        else:
            return {'success': False, 'message': 'Username or email already exists'}
    
    def handle_login(self, message, client_address):
        """Handle user login"""
        username = message.get('username')
        
        if not username:
            return {'success': False, 'message': 'Username is required'}
        
        user = db.get_user(username)
        if user:
            db.update_user_activity(user['id'])
            db.log_connection(user['id'], 'login', str(client_address[0]))
            print(f"✅ User {username} logged in from {client_address}")
            return {
                'success': True,
                'message': 'Login successful',
                'user_id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        else:
            return {'success': False, 'message': 'User not found'}
    
    def handle_send_message(self, message, user_id):
        """Handle sending a message"""
        if not user_id:
            return {'success': False, 'message': 'Please login first'}
        
        content = message.get('content')
        if not content:
            return {'success': False, 'message': 'Message content is required'}
        
        message_id = db.add_message(user_id, content)
        db.update_user_activity(user_id)
        
        # Broadcast message to all connected clients
        self.broadcast_message_to_clients({
            'type': 'new_message',
            'message_id': message_id,
            'content': content,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return {'success': True, 'message': 'Message sent', 'message_id': message_id}
    
    def handle_get_messages(self):
        """Handle getting recent messages"""
        messages = db.get_recent_messages(limit=20)
        return {
            'success': True,
            'messages': messages
        }
    
    def handle_get_users(self):
        """Handle getting all users"""
        users = db.get_all_users()
        # Remove sensitive information
        safe_users = [{'id': u['id'], 'username': u['username'], 'created_at': u['created_at']} for u in users]
        return {
            'success': True,
            'users': safe_users
        }
    
    def broadcast_message_to_clients(self, message):
        """Broadcast a message to all connected clients"""
        message_json = json.dumps(message)
        disconnected_clients = []
        
        for client_socket, client_info in self.clients.items():
            try:
                client_socket.send(message_json.encode('utf-8'))
            except Exception as e:
                print(f"❌ Error broadcasting to {client_info['username']}: {e}")
                disconnected_clients.append(client_socket)
        
        # Remove disconnected clients
        for client_socket in disconnected_clients:
            if client_socket in self.clients:
                del self.clients[client_socket]
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()
        print("🛑 Server stopped")

def main():
    server = SocketServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Server shutting down...")
        server.stop_server()

if __name__ == "__main__":
    main()