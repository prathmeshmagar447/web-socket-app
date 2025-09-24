# Web Socket Application with Database

A complete Python socket-based web application with client-server architecture and SQLite database integration.

## 🚀 Features

- **Socket Communication**: TCP socket-based client-server communication
- **Database Integration**: SQLite database for data persistence
- **User Management**: Registration, login, and user activity tracking  
- **Real-time Messaging**: Send and receive messages in real-time
- **Multi-client Support**: Handle multiple clients concurrently using threading
- **Connection Logging**: Track user connections and activities

## 📁 Project Structure

```
web_socket_app/
├── app.py                 # Main launcher script
├── requirements.txt       # Project dependencies  
├── README.md             # This file
├── database/
│   └── db_manager.py     # Database operations and management
├── server/
│   └── socket_server.py  # Socket server implementation
└── client/
    └── socket_client.py  # Socket client implementation
```

## 🛠️ Installation

1. **Clone or download the project**:
   ```bash
   cd /Users/prathmesh/web_socket_app
   ```

2. **No additional dependencies required!**
   This project uses only Python's built-in modules (socket, sqlite3, threading, json, etc.)

3. **Verify Python version**:
   ```bash
   python --version  # Should be Python 3.6+
   ```

## 🚦 Quick Start

### 1. Start the Server

Open a terminal and run:
```bash
cd /Users/prathmesh/web_socket_app
python app.py server
```

You should see:
```
🚀 Socket server started on localhost:12345
Waiting for client connections...
```

### 2. Start a Client

Open another terminal and run:
```bash
cd /Users/prathmesh/web_socket_app  
python app.py client
```

### 3. Use the Client

Once connected, you can use these commands:

```bash
# Register a new user
register john john@example.com

# Login 
login john

# Send a message
send Hello, everyone!

# Get recent messages
messages

# See all users
users

# Test connection
ping

# Exit
quit
```

## 🎯 Usage Examples

### Server Terminal:
```bash
$ python app.py server
🚀 Socket server started on localhost:12345
Waiting for client connections...
📱 New client connected from ('127.0.0.1', 54321)
✅ User john logged in from ('127.0.0.1', 54321)
📱 New client connected from ('127.0.0.1', 54322)
✅ User alice logged in from ('127.0.0.1', 54322)
```

### Client Terminal:
```bash
$ python app.py client
✅ Connected to server at localhost:12345

🎉 Welcome to Socket Chat Client!
Commands:
  register <username> <email> - Register a new user
  login <username>            - Login with username
  send <message>              - Send a chat message
  messages                    - Get recent messages
  users                       - Get list of users
  ping                        - Test server connectivity
  quit                        - Exit the client
--------------------------------------------------
>>> register john john@example.com
✅ Registration successful! User ID: 1
>>> login john  
✅ Login successful! Welcome, john
>>> send Hello, world!
✅ Message sent successfully
>>> messages

📋 Recent Messages (1 messages):
--------------------------------------------------
[2024-09-24 04:16:00] john: Hello, world!
--------------------------------------------------
```

## 📊 Database Schema

The application automatically creates a SQLite database with these tables:

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email address
- `created_at`: Registration timestamp
- `last_active`: Last activity timestamp

### Messages Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `content`: Message content
- `timestamp`: Message timestamp

### Connection Logs Table
- `id`: Primary key
- `user_id`: Foreign key to users table
- `action`: Action type (login, logout, register, etc.)
- `ip_address`: Client IP address
- `timestamp`: Action timestamp

## 🔧 Configuration

You can modify the server configuration in `server/socket_server.py`:

```python
class SocketServer:
    def __init__(self, host='localhost', port=12345):
        # Change host and port as needed
```

And in the client in `client/socket_client.py`:

```python
class SocketClient:
    def __init__(self, host='localhost', port=12345):
        # Must match server configuration
```

## 🚨 Troubleshooting

### Common Issues:

1. **"Address already in use" error**:
   - Wait a few seconds and try again
   - Or change the port number in both server and client

2. **"Connection refused" error**:
   - Make sure the server is running first
   - Check that host/port match between server and client

3. **Import errors**:
   - Make sure you're running from the `web_socket_app` directory
   - Use `python app.py` instead of running individual modules

4. **Database errors**:
   - The SQLite database file is created automatically
   - Check file permissions in the project directory

## 🔒 Security Notes

- This is a development/demonstration application
- No password encryption is implemented
- No input sanitization for production use
- Use only in trusted networks

## 🎈 Extending the Application

Ideas for enhancement:
- Add password authentication
- Implement private messaging
- Add file transfer capabilities  
- Create a web interface
- Add message encryption
- Implement chat rooms/channels

## 📝 License

This project is created for educational purposes. Feel free to modify and distribute.