import jwt
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict
import threading

class RateLimiter:
    """Rate limiter to prevent spam and abuse"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_allowed(self, identifier: str, max_requests: int = 10, window_seconds: int = 60) -> bool:
        """Check if request is allowed based on rate limits"""
        with self.lock:
            now = time.time()
            # Clean old requests
            self.requests[identifier] = [req_time for req_time in self.requests[identifier] 
                                       if now - req_time < window_seconds]
            
            # Check if under limit
            if len(self.requests[identifier]) < max_requests:
                self.requests[identifier].append(now)
                return True
            return False
    
    def get_remaining_requests(self, identifier: str, max_requests: int = 10, window_seconds: int = 60) -> int:
        """Get remaining requests for identifier"""
        with self.lock:
            now = time.time()
            self.requests[identifier] = [req_time for req_time in self.requests[identifier] 
                                       if now - req_time < window_seconds]
            return max(0, max_requests - len(self.requests[identifier]))

class AuthManager:
    """Advanced authentication and security manager"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or self._generate_secret_key()
        self.rate_limiter = RateLimiter()
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = set()
        self.active_sessions = {}
        self.lock = threading.Lock()
    
    def _generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def generate_jwt_token(self, user_id: int, username: str, role: str = 'user', 
                          expires_in_hours: int = 24) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
            'iat': datetime.utcnow(),
            'jti': hashlib.md5(f"{user_id}{username}{time.time()}".encode()).hexdigest()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        # Store active session
        with self.lock:
            self.active_sessions[payload['jti']] = {
                'user_id': user_id,
                'username': username,
                'role': role,
                'created_at': datetime.utcnow(),
                'expires_at': payload['exp']
            }
        
        return token
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check if session is still active
            jti = payload.get('jti')
            with self.lock:
                if jti not in self.active_sessions:
                    return None
                
                session = self.active_sessions[jti]
                if session['expires_at'] < datetime.utcnow():
                    del self.active_sessions[jti]
                    return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            jti = payload.get('jti')
            
            with self.lock:
                if jti in self.active_sessions:
                    del self.active_sessions[jti]
                    return True
            return False
            
        except jwt.InvalidTokenError:
            return False
    
    def check_rate_limit(self, identifier: str, action: str) -> Dict[str, Any]:
        """Check rate limit for different actions"""
        rate_limits = {
            'login': (5, 300),      # 5 attempts per 5 minutes
            'register': (3, 3600),   # 3 attempts per hour
            'message': (30, 60),     # 30 messages per minute
            'file_upload': (5, 300), # 5 file uploads per 5 minutes
            'room_create': (3, 3600) # 3 room creations per hour
        }
        
        max_requests, window = rate_limits.get(action, (10, 60))
        allowed = self.rate_limiter.is_allowed(f"{identifier}:{action}", max_requests, window)
        remaining = self.rate_limiter.get_remaining_requests(f"{identifier}:{action}", max_requests, window)
        
        return {
            'allowed': allowed,
            'remaining': remaining,
            'reset_time': int(time.time()) + window if not allowed else None
        }
    
    def record_failed_attempt(self, ip_address: str, username: str = None):
        """Record failed login attempt"""
        with self.lock:
            identifier = f"{ip_address}:{username}" if username else ip_address
            self.failed_attempts[identifier].append(time.time())
            
            # Clean old attempts (older than 1 hour)
            hour_ago = time.time() - 3600
            self.failed_attempts[identifier] = [
                attempt for attempt in self.failed_attempts[identifier] 
                if attempt > hour_ago
            ]
            
            # Block IP after 10 failed attempts in 1 hour
            if len(self.failed_attempts[identifier]) >= 10:
                self.blocked_ips.add(ip_address)
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked"""
        return ip_address in self.blocked_ips
    
    def unblock_ip(self, ip_address: str):
        """Unblock an IP address"""
        with self.lock:
            self.blocked_ips.discard(ip_address)
    
    def get_failed_attempts(self, ip_address: str) -> int:
        """Get number of failed attempts for IP"""
        with self.lock:
            attempts = 0
            hour_ago = time.time() - 3600
            for identifier in self.failed_attempts:
                if identifier.startswith(ip_address):
                    attempts += len([a for a in self.failed_attempts[identifier] if a > hour_ago])
            return attempts
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        result = {
            'valid': True,
            'score': 0,
            'issues': []
        }
        
        if len(password) < 8:
            result['valid'] = False
            result['issues'].append('Password must be at least 8 characters long')
        else:
            result['score'] += 1
        
        if not any(c.islower() for c in password):
            result['valid'] = False
            result['issues'].append('Password must contain lowercase letters')
        else:
            result['score'] += 1
        
        if not any(c.isupper() for c in password):
            result['valid'] = False
            result['issues'].append('Password must contain uppercase letters')
        else:
            result['score'] += 1
        
        if not any(c.isdigit() for c in password):
            result['valid'] = False
            result['issues'].append('Password must contain numbers')
        else:
            result['score'] += 1
        
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
            result['issues'].append('Password should contain special characters')
        else:
            result['score'] += 1
        
        # Additional strength checks
        if len(password) >= 12:
            result['score'] += 1
        
        if len(set(password)) >= len(password) * 0.7:  # Character diversity
            result['score'] += 1
        
        return result
    
    def generate_session_id(self, user_id: int, ip_address: str) -> str:
        """Generate unique session ID"""
        import secrets
        data = f"{user_id}{ip_address}{time.time()}{secrets.token_hex(8)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def clean_expired_sessions(self):
        """Clean expired sessions (should be called periodically)"""
        with self.lock:
            now = datetime.utcnow()
            expired_sessions = [
                jti for jti, session in self.active_sessions.items()
                if session['expires_at'] < now
            ]
            
            for jti in expired_sessions:
                del self.active_sessions[jti]
    
    def get_active_sessions_count(self, user_id: int = None) -> int:
        """Get count of active sessions"""
        with self.lock:
            if user_id:
                return sum(1 for session in self.active_sessions.values() 
                          if session['user_id'] == user_id)
            return len(self.active_sessions)
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for HTTP responses"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }

# Global auth manager instance
auth_manager = AuthManager()