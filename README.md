# Web Socket Application with Web Interface and Enhanced Features

A comprehensive Python web socket application featuring a client-server architecture, a web interface, and an enhanced SQLite database integration.

## 🚀 Features

- **Socket Communication**: TCP socket-based client-server communication
- **Web Interface**: Flask-based web interface for chat
- **Real-time Messaging**: Send and receive messages in real-time via Flask-SocketIO
- **Enhanced Database Integration**: SQLite database with `enhanced_db_manager.py` for robust data persistence
- **User Management**: Registration, login, and user activity tracking
- **Multi-client Support**: Handle multiple clients concurrently using threading and Eventlet for the web server
- **Connection Logging**: Track user connections and activities
- **Security**: Basic authentication and encryption key management
- **File Transfer**: Capabilities for transferring files between clients
- **Notifications**: Email notification system

## 📁 Project Structure

```
web_socket_app/
├── app.py                 # Main launcher script
├── config.py              # Application configuration
├── requirements.txt       # Project dependencies
├── README.md              # This file
├── client/
│   └── socket_client.py   # Socket client implementation
├── database/
│   ├── db_manager.py      # Basic database operations
│   └── enhanced_db_manager.py # Enhanced database operations and management
├── features/
│   └── file_transfer.py   # File transfer functionality
├── notifications/
│   └── email_notifier.py  # Email notification system
├── security/
│   └── auth_manager.py    # Authentication management
├── server/
│   ├── socket_server.py   # Basic socket server implementation
│   └── enhanced_socket_server.py # Enhanced socket server implementation
└── web/
    ├── app.py             # Flask web application
    ├── wsgi.py            # Gunicorn/Eventlet WSGI entry point
    ├── encryption.key     # Web application encryption key
    ├── static/
    │   ├── css/
    │   │   └── style.css  # Stylesheets
    │   └── js/
    │       └── chat.js    # Frontend JavaScript for chat
    └── templates/
        ├── chat.html      # Chat interface template
        ├── login.html     # Login page template
        └── register.html  # Registration page template
```

## 🛠️ Installation

1. **Clone or download the project**:
   ```bash
   cd /Users/prathmesh/web_socket_app
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Python version**:
   ```bash
   python --version  # Should be Python 3.6+
   ```

## 🚦 Quick Start

### 1. Start the Web Server (Gunicorn with Eventlet)

Open a terminal and run:
```bash
cd /Users/prathmesh/web_socket_app
gunicorn --worker-class eventlet -w 1 wsgi:app -b 0.0.0.0:5000
```
Or, if you prefer to run with Flask's development server (not recommended for production):
```bash
cd /Users/prathmesh/web_socket_app
python web/app.py
```

You should see output indicating the Flask application is running, e.g.:
```
* Serving Flask app 'web.app'
* Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
* Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

### 2. Access the Web Interface

Open your web browser and navigate to `http://127.0.0.1:5000`.

### 3. Start a Socket Client (Optional, for direct socket communication)

Open another terminal and run:
```bash
cd /Users/prathmesh/web_socket_app
python app.py client
```

### 4. Use the Web Interface

- **Register**: Create a new user account.
- **Login**: Log in with your registered credentials.
- **Chat**: Send and receive messages in real-time.

## 🎯 Usage Examples

### Web Interface:
- Navigate to `http://127.0.0.1:5000`
- Register a new user (e.g., `john`, `john@example.com`)
- Log in with `john`
- Send messages in the chat interface

### Socket Client Terminal (if used):
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
>>> login john
✅ Login successful! Welcome, john
>>> send Hello from socket client!
✅ Message sent successfully
```

## 📊 Database Schema

The application automatically creates a SQLite database with these tables:

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email address
- `password_hash`: Hashed password (new)
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

You can modify the application configuration in `config.py`.
Key configurations include:
- `SECRET_KEY`: Flask secret key for session management
- `DATABASE_URI`: Path to the SQLite database
- `SERVER_HOST`, `SERVER_PORT`: Socket server host and port
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`: Email notification settings

## 🚨 Troubleshooting

### Common Issues:

1. **"Address already in use" error**:
   - Ensure no other process is using port 5000 (for web) or 12345 (for socket server).
   - Change the port number in `config.py` and restart.

2. **"Connection refused" error**:
   - Make sure the server (web or socket) is running first.
   - Check that host/port match between client and server configurations.

3. **Import errors**:
   - Make sure all dependencies are installed (`pip install -r requirements.txt`).
   - Ensure you're running from the `web_socket_app` directory.

4. **Database errors**:
   - The SQLite database file is created automatically.
   - Check file permissions in the project directory.

## 🔒 Security Notes

- This application includes basic authentication and encryption key management.
- Password hashing is implemented for user passwords.
- Input sanitization is still recommended for production use.
- Ensure `SECRET_KEY` and `encryption.key` are kept secure.

## 🎈 Extending the Application

Ideas for enhancement:
- Implement private messaging.
- Enhance file transfer with progress indicators and larger file support.
- Add chat rooms/channels.
- Integrate more robust security features (e.g., OAuth, rate limiting).
- Improve UI/UX of the web interface.

## 📝 License

This project is created for educational purposes. Feel free to modify and distribute.
