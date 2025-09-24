import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

class DatabaseManager:
    """Manages SQLite database operations for the web socket application"""
    
    def __init__(self, db_path: str = "web_socket_app.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def init_database(self):
        """Initialize the database with required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP
                )
            ''')
            
            # Messages table for chat/communication
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Connection logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS connection_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    ip_address TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            conn.commit()
    
    def create_user(self, username: str, email: str) -> Optional[int]:
        """Create a new user and return user ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO users (username, email) VALUES (?, ?)',
                    (username, email)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None  # User already exists
    
    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_user_activity(self, user_id: int):
        """Update user's last active timestamp"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?',
                (user_id,)
            )
            conn.commit()
    
    def add_message(self, user_id: int, content: str) -> int:
        """Add a new message"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO messages (user_id, content) VALUES (?, ?)',
                (user_id, content)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_recent_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages with user information"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.*, u.username 
                FROM messages m
                JOIN users u ON m.user_id = u.id
                ORDER BY m.timestamp DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def log_connection(self, user_id: int, action: str, ip_address: str = None):
        """Log connection activity"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO connection_logs (user_id, action, ip_address) VALUES (?, ?, ?)',
                (user_id, action, ip_address)
            )
            conn.commit()
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection (called automatically with context manager)"""
        pass

# Initialize database instance
db = DatabaseManager()