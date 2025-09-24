import os
import base64
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Optional, List, Any
import threading
import time
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.enhanced_db_manager import enhanced_db
from security.auth_manager import auth_manager

class FileTransferManager:
    """Manages file transfers with security, validation, and progress tracking"""
    
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.chunk_size = 64 * 1024  # 64KB chunks
        self.allowed_extensions = {
            'images': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'},
            'documents': {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'},
            'audio': {'.mp3', '.wav', '.ogg', '.m4a', '.flac'},
            'video': {'.mp4', '.avi', '.mkv', '.mov', '.webm'},
            'archives': {'.zip', '.rar', '.7z', '.tar', '.gz'},
            'code': {'.py', '.js', '.html', '.css', '.json', '.xml', '.sql'}
        }
        self.blocked_extensions = {'.exe', '.bat', '.cmd', '.scr', '.com', '.pif', '.vbs', '.jar'}
        self.active_transfers = {}  # transfer_id -> transfer_info
        self.lock = threading.Lock()
        
        # Create upload directories
        self.create_upload_directories()
    
    def create_upload_directories(self):
        """Create necessary upload directories"""
        directories = [
            self.upload_dir / "files",
            self.upload_dir / "images",
            self.upload_dir / "audio",
            self.upload_dir / "video",
            self.upload_dir / "documents",
            self.upload_dir / "thumbnails",
            self.upload_dir / "temp"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate_file(self, filename: str, file_size: int, user_id: int) -> Dict[str, Any]:
        """Validate file before upload"""
        result = {
            'valid': True,
            'issues': [],
            'file_type': 'unknown',
            'category': 'files'
        }
        
        # Check file size
        if file_size > self.max_file_size:
            result['valid'] = False
            result['issues'].append(f'File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size ({self.max_file_size / (1024*1024)}MB)')
        
        # Check file extension
        file_ext = Path(filename).suffix.lower()
        
        if file_ext in self.blocked_extensions:
            result['valid'] = False
            result['issues'].append(f'File type {file_ext} is not allowed for security reasons')
            return result
        
        # Determine file category
        for category, extensions in self.allowed_extensions.items():
            if file_ext in extensions:
                result['category'] = category
                break
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        result['file_type'] = mime_type or 'application/octet-stream'
        
        # Rate limiting for file uploads
        rate_check = auth_manager.check_rate_limit(str(user_id), 'file_upload')
        if not rate_check['allowed']:
            result['valid'] = False
            result['issues'].append(f'Upload rate limit exceeded. Try again in {rate_check["reset_time"] - int(time.time())} seconds')
        
        return result
    
    def start_file_upload(self, sender_id: int, recipient_id: int, filename: str, 
                         file_size: int, file_data: str = None) -> Dict[str, Any]:
        """Start a file upload process"""
        
        # Validate file
        validation = self.validate_file(filename, file_size, sender_id)
        if not validation['valid']:
            return {
                'success': False,
                'message': 'File validation failed',
                'issues': validation['issues']
            }
        
        # Generate unique filename to prevent conflicts
        safe_filename = self.generate_safe_filename(filename)
        category = validation['category']
        file_path = self.upload_dir / category / safe_filename
        
        # Create file transfer record in database
        transfer_id = enhanced_db.create_file_transfer(
            sender_id=sender_id,
            recipient_id=recipient_id,
            file_name=filename,
            file_path=str(file_path),
            file_size=file_size,
            file_type=validation['file_type']
        )
        
        # Store transfer info in memory
        with self.lock:
            self.active_transfers[transfer_id] = {
                'sender_id': sender_id,
                'recipient_id': recipient_id,
                'filename': filename,
                'safe_filename': safe_filename,
                'file_path': file_path,
                'file_size': file_size,
                'file_type': validation['file_type'],
                'category': category,
                'bytes_transferred': 0,
                'chunks_received': 0,
                'started_at': time.time(),
                'temp_file': None
            }
        
        # If file data provided, handle single upload
        if file_data:
            return self.handle_single_file_upload(transfer_id, file_data)
        
        return {
            'success': True,
            'transfer_id': transfer_id,
            'message': 'File upload started',
            'chunk_size': self.chunk_size
        }
    
    def handle_single_file_upload(self, transfer_id: str, file_data: str) -> Dict[str, Any]:
        """Handle complete file upload in single request"""
        try:
            # Decode base64 data
            file_bytes = base64.b64decode(file_data)
            
            with self.lock:
                if transfer_id not in self.active_transfers:
                    return {'success': False, 'message': 'Transfer not found'}
                
                transfer_info = self.active_transfers[transfer_id]
                
                # Verify file size matches
                if len(file_bytes) != transfer_info['file_size']:
                    del self.active_transfers[transfer_id]
                    return {'success': False, 'message': 'File size mismatch'}
                
                # Write file
                with open(transfer_info['file_path'], 'wb') as f:
                    f.write(file_bytes)
                
                # Update progress
                enhanced_db.update_transfer_progress(transfer_id, 100.0, 'completed')
                
                # Create thumbnail if image
                thumbnail_path = None
                if transfer_info['category'] == 'images':
                    thumbnail_path = self.create_thumbnail(transfer_info['file_path'])
                
                # Clean up
                del self.active_transfers[transfer_id]
                
                return {
                    'success': True,
                    'message': 'File uploaded successfully',
                    'file_path': str(transfer_info['file_path']),
                    'thumbnail_path': thumbnail_path,
                    'file_hash': self.calculate_file_hash(transfer_info['file_path'])
                }
                
        except Exception as e:
            with self.lock:
                if transfer_id in self.active_transfers:
                    del self.active_transfers[transfer_id]
            enhanced_db.update_transfer_progress(transfer_id, 0.0, 'failed')
            return {'success': False, 'message': f'Upload failed: {str(e)}'}
    
    def create_thumbnail(self, image_path: Path, size: tuple = (200, 200)) -> Optional[str]:
        """Create thumbnail for image files"""
        try:
            # Try to import PIL, if not available, skip thumbnail creation
            from PIL import Image
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumb_filename = f"thumb_{image_path.stem}.jpg"
                thumb_path = self.upload_dir / "thumbnails" / thumb_filename
                
                img.save(thumb_path, 'JPEG', quality=85, optimize=True)
                
                return str(thumb_path)
                
        except ImportError:
            print("⚠️ PIL not available, skipping thumbnail creation")
            return None
        except Exception as e:
            print(f"❌ Error creating thumbnail: {e}")
            return None
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file for integrity verification"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"❌ Error calculating file hash: {e}")
            return ""
    
    def generate_safe_filename(self, filename: str) -> str:
        """Generate safe filename to prevent conflicts and security issues"""
        # Get file stem and extension
        path = Path(filename)
        stem = path.stem
        ext = path.suffix
        
        # Remove unsafe characters
        safe_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        safe_stem = ''.join(c for c in stem if c in safe_chars)
        
        # Truncate if too long
        if len(safe_stem) > 100:
            safe_stem = safe_stem[:100]
        
        # Add timestamp to ensure uniqueness
        timestamp = int(time.time() * 1000)  # milliseconds
        
        return f"{safe_stem}_{timestamp}{ext}"
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file information"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
            
            stat = path.stat()
            mime_type, _ = mimetypes.guess_type(str(path))
            
            return {
                'filename': path.name,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'mime_type': mime_type or 'application/octet-stream',
                'exists': True
            }
        except Exception as e:
            print(f"❌ Error getting file info: {e}")
            return None
    
    def download_file(self, file_path: str, user_id: int) -> Dict[str, Any]:
        """Prepare file for download"""
        try:
            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'message': 'File not found'}
            
            # Check if user has permission (implement your own logic)
            # For now, allow all authenticated users
            
            # Read file in chunks to avoid memory issues
            with open(path, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode('utf-8')
            
            return {
                'success': True,
                'filename': path.name,
                'file_data': file_data,
                'file_size': path.stat().st_size,
                'mime_type': mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Download failed: {str(e)}'}
    
    def get_transfer_progress(self, transfer_id: str) -> Dict[str, Any]:
        """Get current transfer progress"""
        with self.lock:
            if transfer_id in self.active_transfers:
                info = self.active_transfers[transfer_id]
                progress = (info['bytes_transferred'] / info['file_size']) * 100 if info['file_size'] > 0 else 0
                
                return {
                    'success': True,
                    'progress': progress,
                    'bytes_transferred': info['bytes_transferred'],
                    'file_size': info['file_size'],
                    'chunks_received': info['chunks_received'],
                    'elapsed_time': time.time() - info['started_at']
                }
        
        return {'success': False, 'message': 'Transfer not found'}
    
    def cancel_transfer(self, transfer_id: str, user_id: int) -> Dict[str, Any]:
        """Cancel an active transfer"""
        with self.lock:
            if transfer_id not in self.active_transfers:
                return {'success': False, 'message': 'Transfer not found'}
            
            transfer_info = self.active_transfers[transfer_id]
            
            # Check if user has permission to cancel
            if user_id != transfer_info['sender_id'] and user_id != transfer_info['recipient_id']:
                return {'success': False, 'message': 'Permission denied'}
            
            # Cleanup
            self.cleanup_failed_transfer(transfer_id)
            
            return {'success': True, 'message': 'Transfer cancelled'}
    
    def cleanup_failed_transfer(self, transfer_id: str):
        """Clean up failed transfer"""
        with self.lock:
            if transfer_id in self.active_transfers:
                transfer_info = self.active_transfers[transfer_id]
                
                # Close temp file if open
                if transfer_info.get('temp_file'):
                    try:
                        transfer_info['temp_file'].close()
                    except:
                        pass
                
                # Remove temp file
                temp_path = self.upload_dir / "temp" / f"{transfer_id}.tmp"
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except:
                        pass
                
                del self.active_transfers[transfer_id]
        
        # Update database
        enhanced_db.update_transfer_progress(transfer_id, 0.0, 'failed')

# Global file transfer manager instance
file_transfer_manager = FileTransferManager()