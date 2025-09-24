import sqlite3
import os
import hashlib
import secrets
import base64
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from cryptography.fernet import Fernet

class UserRole(Enum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"

class MessageType(Enum):
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    AUDIO = "audio"
    SYSTEM = "system"

class EnhancedDatabaseManager:
    """Enhanced database manager with advanced features"""
    
    def __init__(self, db_path: str = "enhanced_web_socket_app.db"):
        self.db_path = db_path
        self.encryption_key = self._get_or_create_encryption_key()
        self.init_database()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for message encryption"""
        key_file = "encryption.key"
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize the database with all required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Enhanced Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    avatar_path TEXT,
                    bio TEXT,
                    status TEXT DEFAULT 'offline',
                    last_seen TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # Chat Rooms table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    password_hash TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_private BOOLEAN DEFAULT 0,
                    max_members INTEGER DEFAULT 100,
                    FOREIGN KEY (created_by) REFERENCES users (id)
                )
            ''')
            
            # Room Memberships table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS room_memberships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    room_id INTEGER,
                    role TEXT DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_muted BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (room_id) REFERENCES chat_rooms (id),
                    UNIQUE(user_id, room_id)
                )
            ''')
            
            # Enhanced Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER,
                    room_id INTEGER,
                    recipient_id INTEGER,
                    content TEXT NOT NULL,
                    message_type TEXT DEFAULT 'text',
                    file_path TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    encrypted BOOLEAN DEFAULT 0,
                    edited BOOLEAN DEFAULT 0,
                    edited_at TIMESTAMP,
                    reply_to_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sender_id) REFERENCES users (id),
                    FOREIGN KEY (room_id) REFERENCES chat_rooms (id),
                    FOREIGN KEY (recipient_id) REFERENCES users (id),
                    FOREIGN KEY (reply_to_id) REFERENCES messages (id)
                )
            ''')
            
            # Message Reactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_reactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    user_id INTEGER,
                    reaction TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (message_id) REFERENCES messages (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(message_id, user_id, reaction)
                )
            ''')
            
            # File Transfers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER,
                    recipient_id INTEGER,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    file_type TEXT,
                    transfer_id TEXT UNIQUE,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0.0,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (sender_id) REFERENCES users (id),
                    FOREIGN KEY (recipient_id) REFERENCES users (id)
                )
            ''')
            
            # User Sessions table (for JWT and authentication)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_token TEXT UNIQUE,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Friendships/Contacts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS friendships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    requester_id INTEGER,
                    addressee_id INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (requester_id) REFERENCES users (id),
                    FOREIGN KEY (addressee_id) REFERENCES users (id),
                    UNIQUE(requester_id, addressee_id)
                )
            ''')
            
            # Notifications table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    title TEXT,
                    message TEXT,
                    data JSON,
                    read BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Enhanced Connection Logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS connection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def hash_password(self, password: str) -> tuple[str, str]:
        """Hash a password with salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return base64.b64encode(password_hash).decode(), salt
    
    def verify_password(self, password: str, password_hash: str, salt: str) -> bool:
        """Verify a password against its hash"""
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return base64.b64encode(computed_hash).decode() == password_hash
    
    def create_user(self, username: str, email: str, password: str, role: str = 'user') -> Optional[int]:
        """Create a new user with password"""
        try:
            password_hash, salt = self.hash_password(password)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?)',
                    (username, email, password_hash, salt, role)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ? AND is_active = 1', (username,))
            user = cursor.fetchone()
            
            if user and self.verify_password(password, user['password_hash'], user['salt']):
                return dict(user)
            return None
    
    def create_chat_room(self, name: str, description: str, created_by: int, password: str = None, is_private: bool = False) -> Optional[int]:
        """Create a new chat room"""
        try:
            password_hash = None
            if password:
                password_hash, _ = self.hash_password(password)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO chat_rooms (name, description, password_hash, created_by, is_private) VALUES (?, ?, ?, ?, ?)',
                    (name, description, password_hash, created_by, is_private)
                )
                room_id = cursor.lastrowid
                
                # Add creator as admin
                cursor.execute(
                    'INSERT INTO room_memberships (user_id, room_id, role) VALUES (?, ?, ?)',
                    (created_by, room_id, 'admin')
                )
                conn.commit()
                return room_id
        except sqlite3.IntegrityError:
            return None
    
    def join_room(self, user_id: int, room_id: int, password: str = None) -> bool:
        """Join a chat room"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if room exists and get password info
            cursor.execute('SELECT password_hash FROM chat_rooms WHERE id = ?', (room_id,))
            room = cursor.fetchone()
            
            if not room:
                return False
            
            # Check password if required
            if room['password_hash'] and password:
                if not self.verify_password(password, room['password_hash'], ''):
                    return False
            elif room['password_hash'] and not password:
                return False
            
            # Add membership
            try:
                cursor.execute(
                    'INSERT INTO room_memberships (user_id, room_id) VALUES (?, ?)',
                    (user_id, room_id)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Already a member
    
    def add_message(self, sender_id: int, content: str, room_id: int = None, recipient_id: int = None, 
                   message_type: str = 'text', file_path: str = None, file_name: str = None, 
                   file_size: int = None, reply_to_id: int = None, encrypt: bool = False) -> int:
        """Add a message (room or private)"""
        
        # Encrypt content if requested
        if encrypt and content:
            fernet = Fernet(self.encryption_key)
            content = fernet.encrypt(content.encode()).decode()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO messages (sender_id, room_id, recipient_id, content, message_type, 
                                    file_path, file_name, file_size, encrypted, reply_to_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sender_id, room_id, recipient_id, content, message_type, file_path, 
                  file_name, file_size, encrypt, reply_to_id))
            conn.commit()
            return cursor.lastrowid
    
    def get_room_messages(self, room_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages for a specific room"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*, u.username, u.avatar_path
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.room_id = ?
                ORDER BY m.timestamp DESC
                LIMIT ? OFFSET ?
            ''', (room_id, limit, offset))
            
            messages = []
            for row in cursor.fetchall():
                message = dict(row)
                # Decrypt if encrypted
                if message['encrypted'] and message['content']:
                    fernet = Fernet(self.encryption_key)
                    message['content'] = fernet.decrypt(message['content'].encode()).decode()
                messages.append(message)
            
            return messages
    
    def get_private_messages(self, user1_id: int, user2_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get private messages between two users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*, u.username, u.avatar_path
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE (m.sender_id = ? AND m.recipient_id = ?) 
                   OR (m.sender_id = ? AND m.recipient_id = ?)
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', (user1_id, user2_id, user2_id, user1_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                message = dict(row)
                # Decrypt if encrypted
                if message['encrypted'] and message['content']:
                    fernet = Fernet(self.encryption_key)
                    message['content'] = fernet.decrypt(message['content'].encode()).decode()
                messages.append(message)
            
            return messages
    
    def add_reaction(self, message_id: int, user_id: int, reaction: str) -> bool:
        """Add a reaction to a message"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO message_reactions (message_id, user_id, reaction) VALUES (?, ?, ?)',
                    (message_id, user_id, reaction)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def create_file_transfer(self, sender_id: int, recipient_id: int, file_name: str, 
                           file_path: str, file_size: int, file_type: str) -> str:
        """Create a new file transfer record"""
        transfer_id = secrets.token_urlsafe(16)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO file_transfers (sender_id, recipient_id, file_name, file_path, 
                                          file_size, file_type, transfer_id) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (sender_id, recipient_id, file_name, file_path, file_size, file_type, transfer_id))
            conn.commit()
            
        return transfer_id
    
    def update_transfer_progress(self, transfer_id: str, progress: float, status: str = None):
        """Update file transfer progress"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    'UPDATE file_transfers SET progress = ?, status = ? WHERE transfer_id = ?',
                    (progress, status, transfer_id)
                )
            else:
                cursor.execute(
                    'UPDATE file_transfers SET progress = ? WHERE transfer_id = ?',
                    (progress, transfer_id)
                )
            conn.commit()
    
    def create_notification(self, user_id: int, notification_type: str, title: str, 
                          message: str, data: Dict = None) -> int:
        """Create a notification for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO notifications (user_id, type, title, message, data) VALUES (?, ?, ?, ?, ?)',
                (user_id, notification_type, title, message, json.dumps(data) if data else None)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_user_rooms(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all rooms a user is a member of"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, rm.role, rm.joined_at
                FROM chat_rooms r
                JOIN room_memberships rm ON r.id = rm.room_id
                WHERE rm.user_id = ?
                ORDER BY rm.joined_at DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_user_status(self, user_id: int, status: str):
        """Update user's online status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET status = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?',
                (status, user_id)
            )
            conn.commit()
    
    def get_online_users(self) -> List[Dict[str, Any]]:
        """Get all online users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, status, avatar_path FROM users WHERE status = 'online'"
            )
            return [dict(row) for row in cursor.fetchall()]

# Initialize enhanced database instance
enhanced_db = EnhancedDatabaseManager()