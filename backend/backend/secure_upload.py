import os
import hashlib
import magic
import tempfile
import shutil
from PIL import Image, ImageOps
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask import current_app, request
from .security import FileSecurityValidator, SecurityAudit

class SecureFileUpload:
    """Comprehensive secure file upload handler"""
    
    def __init__(self, upload_base_dir: str = None):
        self.upload_base_dir = upload_base_dir or os.path.join(
            current_app.root_path, 'static', 'uploads'
        )
        
        # File type configurations
        self.file_configs = {
            'profile_photo': {
                'allowed_extensions': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
                'max_size': 5 * 1024 * 1024,  # 5MB
                'max_dimensions': (1024, 1024),
                'allowed_mime_types': {
                    'image/jpeg', 'image/png', 'image/gif', 'image/webp'
                },
                'upload_dir': 'profile_photos',
                'require_image_validation': True
            },
            'college_logo': {
                'allowed_extensions': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
                'max_size': 3 * 1024 * 1024,  # 3MB
                'max_dimensions': (512, 512),
                'allowed_mime_types': {
                    'image/jpeg', 'image/png', 'image/gif', 'image/webp'
                },
                'upload_dir': 'college_logos',
                'require_image_validation': True
            },
            'document': {
                'allowed_extensions': {'pdf', 'txt', 'md', 'doc', 'docx'},
                'max_size': 10 * 1024 * 1024,  # 10MB
                'allowed_mime_types': {
                    'application/pdf', 'text/plain', 'text/markdown',
                    'application/msword', 
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                },
                'upload_dir': 'documents',
                'require_image_validation': False
            },
            'code_file': {
                'allowed_extensions': {'py', 'js', 'java', 'cpp', 'c', 'go', 'rs', 'php', 'rb'},
                'max_size': 1 * 1024 * 1024,  # 1MB
                'allowed_mime_types': {
                    'text/plain', 'text/x-python', 'application/javascript',
                    'text/x-java-source', 'text/x-c++src', 'text/x-csrc'
                },
                'upload_dir': 'code_files',
                'require_image_validation': False
            }
        }
        
        # Dangerous file signatures to block
        self.dangerous_signatures = {
            b'MZ': 'PE executable',
            b'\x7fELF': 'ELF executable',
            b'\xca\xfe\xba\xbe': 'Java class file',
            b'PK\x03\x04': 'ZIP archive (potential)',
            b'\x1f\x8b': 'GZIP compressed',
            b'BZh': 'BZIP2 compressed',
            b'\x89PNG': 'PNG (check passed separately)',
            b'\xff\xd8\xff': 'JPEG (check passed separately)',
            b'GIF8': 'GIF (check passed separately)',
            b'RIFF': 'RIFF container (WebP/AVI/WAV)'
        }
    
    def validate_and_upload(self, 
                          file: FileStorage, 
                          file_type: str, 
                          user_id: str,
                          custom_filename: str = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Comprehensive file validation and secure upload
        Returns: (success, message, file_info)
        """
        
        # Basic file validation
        if not file or not file.filename:
            return False, "No file provided", None
        
        if file_type not in self.file_configs:
            return False, f"Unsupported file type: {file_type}", None
        
        config = self.file_configs[file_type]
        
        # Log upload attempt
        SecurityAudit.log_security_event(
            'file_upload_attempt',
            user_id=user_id,
            details={
                'filename': file.filename,
                'file_type': file_type,
                'content_length': request.content_length
            }
        )
        
        # Validate file properties
        validation_result = self._validate_file_properties(file, config)
        if not validation_result[0]:
            SecurityAudit.log_security_event(
                'file_upload_validation_failed',
                user_id=user_id,
                details={'reason': validation_result[1], 'filename': file.filename}
            )
            return validation_result
        
        # Security scan
        security_result = self._security_scan_file(file)
        if not security_result[0]:
            SecurityAudit.log_security_event(
                'file_upload_security_failed',
                user_id=user_id,
                details={'reason': security_result[1], 'filename': file.filename}
            )
            return security_result
        
        # Generate secure filename
        secure_name = self._generate_secure_filename(
            file.filename, user_id, custom_filename
        )
        
        # Create upload directory
        upload_dir = os.path.join(self.upload_base_dir, config['upload_dir'])
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, secure_name)
        
        try:
            # Save file securely
            file.save(file_path)
            
            # Post-upload validation and processing
            post_process_result = self._post_upload_processing(
                file_path, config, file_type
            )
            
            if not post_process_result[0]:
                # Remove file if post-processing failed
                if os.path.exists(file_path):
                    os.remove(file_path)
                SecurityAudit.log_security_event(
                    'file_upload_post_process_failed',
                    user_id=user_id,
                    details={'reason': post_process_result[1], 'filename': secure_name}
                )
                return post_process_result
            
            # Generate file info
            file_info = {
                'filename': secure_name,
                'original_filename': file.filename,
                'file_type': file_type,
                'file_size': os.path.getsize(file_path),
                'upload_path': os.path.relpath(file_path, self.upload_base_dir),
                'file_hash': self._calculate_file_hash(file_path),
                'mime_type': magic.from_file(file_path, mime=True) if magic else None
            }
            
            SecurityAudit.log_security_event(
                'file_upload_successful',
                user_id=user_id,
                details=file_info
            )
            
            return True, "File uploaded successfully", file_info
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(file_path):
                os.remove(file_path)
            
            SecurityAudit.log_security_event(
                'file_upload_error',
                user_id=user_id,
                details={'error': str(e), 'filename': file.filename}
            )
            
            return False, f"Upload failed: {str(e)}", None
    
    def _validate_file_properties(self, 
                                file: FileStorage, 
                                config: Dict) -> Tuple[bool, str]:
        """Validate basic file properties"""
        
        # Check filename security
        filename = secure_filename(file.filename)
        if not filename:
            return False, "Invalid filename"
        
        # Check file extension
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in config['allowed_extensions']:
            return False, f"File extension '.{ext}' not allowed"
        
        # Check file size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > config['max_size']:
            return False, f"File size {size} exceeds maximum {config['max_size']} bytes"
        
        if size == 0:
            return False, "Empty file not allowed"
        
        return True, "File properties valid"
    
    def _security_scan_file(self, file: FileStorage) -> Tuple[bool, str]:
        """Perform security scan on file content"""
        
        # Read file header for signature analysis
        file.seek(0)
        header = file.read(512)  # Read first 512 bytes
        file.seek(0)
        
        # Check for dangerous file signatures
        for signature, description in self.dangerous_signatures.items():
            if header.startswith(signature):
                # Allow image files that are properly validated later
                if signature in [b'\x89PNG', b'\xff\xd8\xff', b'GIF8']:
                    continue
                # RIFF can be WebP, which is allowed
                if signature == b'RIFF' and b'WEBP' in header:
                    continue
                return False, f"Dangerous file signature detected: {description}"
        
        # Check for embedded scripts or malicious content
        if self._contains_malicious_content(header):
            return False, "Malicious content detected in file"
        
        # MIME type validation using python-magic if available
        try:
            mime_type = magic.from_buffer(header, mime=True)
            if mime_type in {'application/x-executable', 'application/x-dosexec'}:
                return False, f"Executable file type not allowed: {mime_type}"
        except:
            pass  # magic library might not be available
        
        return True, "Security scan passed"
    
    def _contains_malicious_content(self, content: bytes) -> bool:
        """Check for malicious content patterns"""
        
        malicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'onload=',
            b'onerror=',
            b'<?php',
            b'<%',
            b'#!/bin/sh',
            b'#!/bin/bash',
            b'powershell',
            b'cmd.exe',
            b'eval(',
            b'exec(',
        ]
        
        content_lower = content.lower()
        for pattern in malicious_patterns:
            if pattern in content_lower:
                return True
        
        return False
    
    def _post_upload_processing(self, 
                              file_path: str, 
                              config: Dict, 
                              file_type: str) -> Tuple[bool, str]:
        """Post-upload validation and processing"""
        
        # Image-specific validation and processing
        if config.get('require_image_validation', False):
            return self._process_image_file(file_path, config)
        
        # Document-specific validation
        if file_type == 'document':
            return self._process_document_file(file_path, config)
        
        # Code file validation
        if file_type == 'code_file':
            return self._process_code_file(file_path, config)
        
        return True, "Processing completed"
    
    def _process_image_file(self, 
                          file_path: str, 
                          config: Dict) -> Tuple[bool, str]:
        """Process and validate image files"""
        
        try:
            with Image.open(file_path) as img:
                # Validate image integrity
                img.verify()
            
            # Reopen for processing (verify() closes the image)
            with Image.open(file_path) as img:
                # Check image dimensions
                width, height = img.size
                max_width, max_height = config.get('max_dimensions', (2048, 2048))
                
                if width > max_width or height > max_height:
                    # Resize image if too large
                    img = ImageOps.fit(img, (max_width, max_height), Image.Resampling.LANCZOS)
                    img.save(file_path, optimize=True, quality=85)
                
                # Strip EXIF data for privacy
                if hasattr(img, '_getexif') and img._getexif():
                    img = ImageOps.exif_transpose(img)
                    img.save(file_path)
                
                # Validate image format matches extension
                expected_format = self._get_expected_image_format(file_path)
                if img.format.upper() != expected_format.upper():
                    return False, f"Image format {img.format} doesn't match file extension"
                
            return True, "Image processed successfully"
            
        except Exception as e:
            return False, f"Image processing failed: {str(e)}"
    
    def _process_document_file(self, 
                             file_path: str, 
                             config: Dict) -> Tuple[bool, str]:
        """Process and validate document files"""
        
        try:
            # Basic file size and structure validation
            with open(file_path, 'rb') as f:
                content = f.read(1024)  # Read first 1KB
                
            # Check for PDF structure if it's a PDF
            if file_path.endswith('.pdf'):
                if not content.startswith(b'%PDF-'):
                    return False, "Invalid PDF file structure"
            
            # Check for malicious content in text files
            if file_path.endswith(('.txt', '.md')):
                if self._contains_malicious_content(content):
                    return False, "Malicious content detected in document"
            
            return True, "Document validated successfully"
            
        except Exception as e:
            return False, f"Document validation failed: {str(e)}"
    
    def _process_code_file(self, 
                         file_path: str, 
                         config: Dict) -> Tuple[bool, str]:
        """Process and validate code files"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # Use SecurityValidator for code validation
            from .security import SecurityValidator
            
            # Determine language from file extension
            ext = file_path.split('.')[-1].lower()
            language_map = {
                'py': 'python',
                'js': 'javascript',
                'java': 'java',
                'cpp': 'cpp',
                'c': 'c'
            }
            
            language = language_map.get(ext, 'unknown')
            
            if language != 'unknown':
                is_valid, error_msg = SecurityValidator.validate_code_input(
                    code_content, language
                )
                if not is_valid:
                    return False, f"Code validation failed: {error_msg}"
            
            return True, "Code file validated successfully"
            
        except Exception as e:
            return False, f"Code file validation failed: {str(e)}"
    
    def _get_expected_image_format(self, file_path: str) -> str:
        """Get expected image format from file extension"""
        ext = file_path.split('.')[-1].lower()
        format_map = {
            'jpg': 'JPEG',
            'jpeg': 'JPEG',
            'png': 'PNG',
            'gif': 'GIF',
            'webp': 'WEBP'
        }
        return format_map.get(ext, 'UNKNOWN')
    
    def _generate_secure_filename(self, 
                                original_filename: str, 
                                user_id: str,
                                custom_filename: str = None) -> str:
        """Generate a secure, unique filename"""
        
        if custom_filename:
            base_name = secure_filename(custom_filename)
        else:
            base_name = secure_filename(original_filename)
        
        # Extract extension
        if '.' in base_name:
            name, ext = base_name.rsplit('.', 1)
        else:
            name, ext = base_name, ''
        
        # Create unique identifier
        import time
        timestamp = str(int(time.time()))
        unique_id = hashlib.md5(f"{user_id}{timestamp}{original_filename}".encode()).hexdigest()[:8]
        
        # Combine parts
        secure_name = f"{name}_{user_id}_{unique_id}"
        if ext:
            secure_name += f".{ext}"
        
        # Ensure filename length is reasonable
        if len(secure_name) > 200:
            secure_name = secure_name[:190] + f".{ext}" if ext else secure_name[:200]
        
        return secure_name
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def delete_file_securely(self, 
                           file_path: str, 
                           user_id: str) -> Tuple[bool, str]:
        """Securely delete an uploaded file"""
        
        try:
            # Validate file path is within upload directory
            abs_file_path = os.path.abspath(file_path)
            abs_upload_dir = os.path.abspath(self.upload_base_dir)
            
            if not abs_file_path.startswith(abs_upload_dir):
                SecurityAudit.log_security_event(
                    'file_deletion_path_traversal_attempt',
                    user_id=user_id,
                    details={'attempted_path': file_path}
                )
                return False, "Invalid file path"
            
            if not os.path.exists(abs_file_path):
                return False, "File not found"
            
            # Log deletion
            SecurityAudit.log_security_event(
                'file_deletion',
                user_id=user_id,
                details={'file_path': abs_file_path}
            )
            
            # Securely delete file
            os.remove(abs_file_path)
            
            return True, "File deleted successfully"
            
        except Exception as e:
            SecurityAudit.log_security_event(
                'file_deletion_error',
                user_id=user_id,
                details={'error': str(e), 'file_path': file_path}
            )
            return False, f"Deletion failed: {str(e)}"
    
    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """Get information about an uploaded file"""
        
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            
            file_info = {
                'filename': os.path.basename(file_path),
                'file_size': stat.st_size,
                'created_time': stat.st_ctime,
                'modified_time': stat.st_mtime,
                'file_hash': self._calculate_file_hash(file_path)
            }
            
            # Add MIME type if magic is available
            try:
                file_info['mime_type'] = magic.from_file(file_path, mime=True)
            except:
                file_info['mime_type'] = 'unknown'
            
            return file_info
            
        except Exception:
            return None

# Convenience functions for common upload types
def upload_profile_photo(file: FileStorage, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
    """Upload user profile photo"""
    uploader = SecureFileUpload()
    return uploader.validate_and_upload(file, 'profile_photo', user_id)

def upload_college_logo(file: FileStorage, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
    """Upload college logo"""
    uploader = SecureFileUpload()
    return uploader.validate_and_upload(file, 'college_logo', user_id)

def upload_document(file: FileStorage, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
    """Upload document file"""
    uploader = SecureFileUpload()
    return uploader.validate_and_upload(file, 'document', user_id)

def upload_code_file(file: FileStorage, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
    """Upload code file"""
    uploader = SecureFileUpload()
    return uploader.validate_and_upload(file, 'code_file', user_id)