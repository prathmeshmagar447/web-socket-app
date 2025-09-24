# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

This is a comprehensive Python WebSocket application with a dual architecture supporting both raw TCP sockets and web-based communication. The project features enterprise-grade security, file transfer capabilities, chat rooms, and real-time messaging.

## Common Commands

### Running the Application
```bash
# Start the enhanced socket server (recommended)
python app.py server

# Start the basic socket client
python app.py client

# Install dependencies (for web interface and enhanced features)
pip3 install -r requirements.txt

# Run via Runfile (if available)
run server    # Starts main server
run client    # Starts socket client
```

### Development Commands
```bash
# Run tests (when implemented)
pytest

# Lint code
flake8 .

# Format code
black .

# Start Flask web interface
python web/app.py
```

### Database Operations
The application uses SQLite databases that auto-initialize. Two database managers exist:
- `database/db_manager.py` - Basic functionality
- `database/enhanced_db_manager.py` - Full feature set with 11 tables

## Architecture Overview

### Dual-Server Architecture
The application runs two distinct server implementations:

1. **Enhanced Server** (`server/enhanced_socket_server.py`)
   - Enterprise features: authentication, rate limiting, file transfer
   - Chat rooms, private messaging, encryption
   - Multi-threaded with connection pooling
   - **This is the primary server to use**

2. **Basic Server** (`server/socket_server.py`) 
   - Simple chat functionality
   - Used for basic demonstrations
   - Legacy compatibility

### Core Components

**Database Layer**
- `enhanced_db_manager.py`: 11-table schema with relationships
- Auto-encryption key generation and management
- Supports users, rooms, messages, file transfers, sessions, notifications

**Security Layer** (`security/auth_manager.py`)
- JWT token authentication with session management
- Rate limiting (login: 5/5min, messages: 30/min, files: 5/5min)
- IP blocking after 10 failed attempts
- Password strength validation
- Thread-safe implementation

**File Transfer** (`features/file_transfer.py`)
- 100MB file size limit with Base64 encoding
- Supports images, documents, audio, video, code files
- Automatic thumbnail generation for images
- SHA-256 integrity verification
- Progress tracking and chunked uploads

**Web Interface** (`web/app.py`)
- Flask + SocketIO integration
- RESTful API endpoints for auth and rooms
- Real-time WebSocket communication
- Session management

### Message Flow Architecture

**Socket Communication:**
```
Client → Enhanced Server → Database → Broadcast to Room/User
```

**Web Communication:**
```
Browser → Flask App → SocketIO → Database → WebSocket Broadcast
```

## Key Development Patterns

### Database Usage
Always use `enhanced_db_manager` for new features:
```python
from database.enhanced_db_manager import enhanced_db
user_id = enhanced_db.create_user(username, email, password)
```

### Authentication Pattern
Check authentication and rate limits for protected actions:
```python
rate_check = auth_manager.check_rate_limit(identifier, action)
if not rate_check['allowed']:
    return error_response()

token_data = auth_manager.verify_jwt_token(token)
if not token_data:
    return auth_required_response()
```

### File Upload Pattern
Always validate files before processing:
```python
validation = file_transfer_manager.validate_file(filename, size, user_id)
if not validation['valid']:
    return validation['issues']
```

### Thread Safety
All managers use threading locks. When adding shared state:
```python
import threading

class NewManager:
    def __init__(self):
        self.shared_data = {}
        self.lock = threading.Lock()
    
    def modify_shared_data(self, key, value):
        with self.lock:
            self.shared_data[key] = value
```

## Testing Approach

### Manual Testing Flow
1. Start enhanced server: `python app.py server`
2. Start client: `python app.py client` 
3. Test authentication: register → login → send messages
4. Test rooms: create room → join → send room messages
5. Test file transfer: upload → download → verify integrity

### Key Test Scenarios
- Concurrent client connections (stress test)
- Rate limiting behavior
- File upload edge cases (oversized, invalid types)
- Authentication token expiry
- Database connection handling

## Current State & Development Notes

**Completed (50% complete per TODO.md):**
- ✅ Enhanced database with 11 tables
- ✅ JWT authentication with rate limiting
- ✅ Chat rooms with membership management
- ✅ Private messaging with encryption support
- ✅ File transfer with validation and progress tracking

**Pending Implementation:**
- 🔲 Web interface completion (Flask app exists but needs SocketIO integration)
- 🔲 Desktop notifications
- 🔲 Message editing/reactions
- 🔲 Voice/media support
- 🔲 Comprehensive testing suite

## File Structure Context

```
├── app.py                          # Main entry point
├── requirements.txt                # Dependencies (cryptography, Flask, JWT)
├── database/
│   ├── db_manager.py              # Basic database (legacy)
│   └── enhanced_db_manager.py     # Primary database with full schema
├── server/
│   ├── socket_server.py           # Basic server (legacy)
│   └── enhanced_socket_server.py  # Primary server with full features
├── client/
│   └── socket_client.py           # Terminal-based client
├── web/
│   ├── app.py                     # Flask web interface
│   └── templates/                 # HTML templates
├── security/
│   └── auth_manager.py            # Authentication & rate limiting
├── features/
│   └── file_transfer.py           # File upload/download management
└── uploads/                       # File storage (auto-created)
```

## Security Considerations

- **Encryption key** auto-generated in `encryption.key` file
- **JWT secret** auto-generated per session (change for production)
- **Rate limiting** prevents abuse across all endpoints
- **IP blocking** after failed attempts
- **File validation** prevents malicious uploads
- **Session management** with token revocation

## Important Implementation Details

- The enhanced server creates upload directories automatically
- Database encryption keys are persistent across restarts
- All file transfers are logged with metadata in the database
- WebSocket and socket server can run simultaneously on different ports
- Session cleanup runs every 5 minutes automatically
- All network operations are thread-safe

When implementing new features, follow the established patterns of validation → rate limiting → database operation → response/broadcast.