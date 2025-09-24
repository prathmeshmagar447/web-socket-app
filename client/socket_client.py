import socket
import json
import threading
import time
from datetime import datetime

class SocketClient:
    def __init__(self, host='localhost', port=12345):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.user_info = None
        self.listening = False
    
    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"✅ Connected to server at {self.host}:{self.port}")
            
            # Start listening for incoming messages in a separate thread
            listen_thread = threading.Thread(target=self.listen_for_messages)
            listen_thread.daemon = True
            listen_thread.start()
            
            return True
        except Exception as e:
            print(f"❌ Failed to connect to server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        self.connected = False
        self.listening = False
        if self.socket:
            self.socket.close()
        print("🔌 Disconnected from server")
    
    def send_message(self, message):
        """Send a message to the server"""
        if not self.connected:
            print("❌ Not connected to server")
            return None
        
        try:
            message_json = json.dumps(message)
            self.socket.send(message_json.encode('utf-8'))
            
            # Receive response
            response = self.socket.recv(1024).decode('utf-8')
            return json.loads(response)
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None
    
    def listen_for_messages(self):
        """Listen for incoming messages from server"""
        self.listening = True
        while self.listening and self.connected:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if data:
                    try:
                        message = json.loads(data)
                        self.handle_incoming_message(message)
                    except json.JSONDecodeError:
                        print(f"❌ Received invalid JSON: {data}")
                else:
                    break
            except Exception as e:
                if self.connected:
                    print(f"❌ Error receiving message: {e}")
                break
        
        self.listening = False
    
    def handle_incoming_message(self, message):
        """Handle incoming messages from server"""
        message_type = message.get('type')
        
        if message_type == 'new_message':
            print(f"\n📨 New message: {message.get('content')}")
            print(f"   From User ID: {message.get('user_id')}")
            print(f"   Time: {message.get('timestamp')}")
            print(">>> ", end="", flush=True)  # Restore input prompt
    
    def register(self, username, email):
        """Register a new user"""
        message = {
            'action': 'register',
            'username': username,
            'email': email
        }
        
        response = self.send_message(message)
        if response and response.get('success'):
            print(f"✅ Registration successful! User ID: {response.get('user_id')}")
            return True
        else:
            print(f"❌ Registration failed: {response.get('message') if response else 'No response'}")
            return False
    
    def login(self, username):
        """Login with username"""
        message = {
            'action': 'login',
            'username': username
        }
        
        response = self.send_message(message)
        if response and response.get('success'):
            self.user_info = {
                'id': response.get('user_id'),
                'username': response.get('username'),
                'email': response.get('email')
            }
            print(f"✅ Login successful! Welcome, {response.get('username')}")
            return True
        else:
            print(f"❌ Login failed: {response.get('message') if response else 'No response'}")
            return False
    
    def send_chat_message(self, content):
        """Send a chat message"""
        if not self.user_info:
            print("❌ Please login first")
            return False
        
        message = {
            'action': 'send_message',
            'content': content
        }
        
        response = self.send_message(message)
        if response and response.get('success'):
            print("✅ Message sent successfully")
            return True
        else:
            print(f"❌ Failed to send message: {response.get('message') if response else 'No response'}")
            return False

    def send_private_message(self, recipient_id, content):
        """Send a private message to a user"""
        if not self.user_info:
            print("❌ Please login first")
            return False

        message = {
            'action': 'send_private_message',
            'recipient_id': recipient_id,
            'content': content
        }

        response = self.send_message(message)
        if response and response.get('success'):
            print("✅ Private message sent successfully")
            return True
        else:
            print(f"❌ Failed to send private message: {response.get('message') if response else 'No response'}")
            return False
    
    def get_recent_messages(self):
        """Get recent messages from the server"""
        message = {'action': 'get_messages'}
        
        response = self.send_message(message)
        if response and response.get('success'):
            messages = response.get('messages', [])
            print(f"\n📋 Recent Messages ({len(messages)} messages):")
            print("-" * 50)
            for msg in reversed(messages):  # Show oldest first
                print(f"[{msg.get('timestamp')}] {msg.get('username')}: {msg.get('content')}")
            print("-" * 50)
            return messages
        else:
            print(f"❌ Failed to get messages: {response.get('message') if response else 'No response'}")
            return []
    
    def get_users(self):
        """Get list of all users"""
        message = {'action': 'get_users'}
        
        response = self.send_message(message)
        if response and response.get('success'):
            users = response.get('users', [])
            print(f"\n👥 Registered Users ({len(users)} users):")
            print("-" * 30)
            for user in users:
                print(f"• {user.get('username')} (ID: {user.get('id')})")
            print("-" * 30)
            return users
        else:
            print(f"❌ Failed to get users: {response.get('message') if response else 'No response'}")
            return []
    
    def ping_server(self):
        """Ping the server to test connectivity"""
        message = {'action': 'ping'}
        
        response = self.send_message(message)
        if response and response.get('success'):
            print(f"🏓 Pong! Server responded at {response.get('timestamp')}")
            return True
        else:
            print("❌ Server did not respond to ping")
            return False

def main():
    client = SocketClient()
    
    # Connect to server
    if not client.connect():
        return
    
    print("\n🎉 Welcome to Socket Chat Client!")
    print("Commands:")
    print("  register <username> <email> - Register a new user")
    print("  login <username>            - Login with username")
    print("  send <message>              - Send a chat message")
    print("  pm <recipient_id> <message> - Send a private message")
    print("  messages                    - Get recent messages")
    print("  users                       - Get list of users")
    print("  ping                        - Test server connectivity")
    print("  quit                        - Exit the client")
    print("-" * 50)
    
    try:
        while client.connected:
            try:
                user_input = input(">>> ").strip()
                
                if not user_input:
                    continue
                
                parts = user_input.split(' ', 2)
                command = parts[0].lower()
                
                if command == 'quit' or command == 'exit':
                    break
                elif command == 'register':
                    if len(parts) >= 3:
                        username = parts[1]
                        email = parts[2]
                        client.register(username, email)
                    else:
                        print("Usage: register <username> <email>")
                elif command == 'login':
                    if len(parts) >= 2:
                        username = parts[1]
                        client.login(username)
                    else:
                        print("Usage: login <username>")
                elif command == 'send':
                    if len(parts) >= 2:
                        message = ' '.join(parts[1:])
                        client.send_chat_message(message)
                    else:
                        print("Usage: send <message>")
                elif command == 'pm':
                    if len(parts) >= 3:
                        try:
                            recipient_id = int(parts[1])
                            message = ' '.join(parts[2:])
                            client.send_private_message(recipient_id, message)
                        except ValueError:
                            print("Usage: pm <recipient_id> <message>")
                    else:
                        print("Usage: pm <recipient_id> <message>")
                elif command == 'messages':
                    client.get_recent_messages()
                elif command == 'users':
                    client.get_users()
                elif command == 'ping':
                    client.ping_server()
                else:
                    print("Unknown command. Type 'quit' to exit.")
                
            except EOFError:
                break
            except KeyboardInterrupt:
                break
                
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()