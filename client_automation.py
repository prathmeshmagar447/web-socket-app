import socket
import json
import time

def send_command(command):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', 12345))
    s.send(json.dumps(command).encode('utf-8'))
    response = s.recv(1024).decode('utf-8')
    s.close()
    return json.loads(response)

# Register a new user
response = send_command({'action': 'register', 'username': 'testuser', 'email': 'test@user.com'})
print(response)

# Login
response = send_command({'action': 'login', 'username': 'testuser'})
print(response)
user_id = response.get('user_id')

# Get users
response = send_command({'action': 'get_users'})
print(response)

# Send a private message to ourselves
response = send_command({'action': 'send_private_message', 'recipient_id': user_id, 'content': 'hello from the automated client'})
print(response)
