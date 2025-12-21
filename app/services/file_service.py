"""File upload and storage service."""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import UploadFile

from app.utils.sanitization import validate_file_content, sanitize_filename

# Try to import python-magic, but fall back to manual detection if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    MAGIC_AVAILABLE = False

from app.config import settings


class FileService:
    """Service for handling file uploads and storage."""
    
    ALLOWED_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes
    
    def __init__(self, upload_dir: Optional[str] = None):
        """
        Initialize file service.
        
        Args:
            upload_dir: Base directory for uploads (defaults to settings.upload_dir)
        """
        self.upload_dir = Path(upload_dir or settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_upload(
        self,
        file: UploadFile,
        category: str = "packages",
    ) -> tuple[str, str, int]:
        """
        Save an uploaded file with validation.
        
        Args:
            file: Uploaded file object
            category: Category for organizing files (e.g., 'packages')
            
        Returns:
            Tuple of (file_path, mime_type, file_size)
            
        Raises:
            ValueError: If file validation fails
        """
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum allowed "
                f"size ({self.MAX_FILE_SIZE} bytes)"
            )
        
        # Validate file type by content (not just extension)
        mime_type = validate_file_content(content, list(self.ALLOWED_MIME_TYPES))
        if not mime_type:
            detected = self._detect_mime_type(content)
            raise ValueError(
                f"File type '{detected}' is not allowed. "
                f"Allowed types: {', '.join(self.ALLOWED_MIME_TYPES)}"
            )
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        extension = self._get_extension_for_mime_type(mime_type)
        filename = f"{timestamp}_{unique_id}{extension}"
        
        # Organize by year/month directory structure
        now = datetime.now()
        year_month_dir = self.upload_dir / category / str(now.year) / f"{now.month:02d}"
        year_month_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = year_month_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Return relative path from upload_dir
        relative_path = str(file_path.relative_to(self.upload_dir))
        
        return relative_path, mime_type, file_size
    
    def validate_file(
        self,
        file: UploadFile,
        allowed_types: Optional[list[str]] = None,
        max_size: Optional[int] = None,
    ) -> None:
        """
        Validate file without saving it.
        
        Args:
            file: Uploaded file object
            allowed_types: List of allowed MIME types (defaults to ALLOWED_MIME_TYPES)
            max_size: Maximum file size in bytes (defaults to MAX_FILE_SIZE)
            
        Raises:
            ValueError: If validation fails
        """
        allowed = allowed_types or self.ALLOWED_MIME_TYPES
        max_size = max_size or self.MAX_FILE_SIZE
        
        # Check file size from content-length header if available
        if file.size and file.size > max_size:
            raise ValueError(
                f"File size ({file.size} bytes) exceeds maximum allowed "
                f"size ({max_size} bytes)"
            )
    
    def get_file_path(self, relative_path: str) -> Path:
        """
        Get absolute file path from relative path.
        
        Args:
            relative_path: Relative path from upload_dir
            
        Returns:
            Absolute Path object
        """
        return self.upload_dir / relative_path
    
    def delete_file(self, relative_path: str) -> None:
        """
        Delete a file from storage.
        
        Args:
            relative_path: Relative path from upload_dir
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.get_file_path(relative_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        
        file_path.unlink()
    
    def _detect_mime_type(self, content: bytes) -> str:
        """
        Detect MIME type from file content.
        
        Args:
            content: File content bytes
            
        Returns:
            MIME type string
        """
        if MAGIC_AVAILABLE:
            try:
                # Try using python-magic if available
                mime = magic.Magic(mime=True)
                return mime.from_buffer(content)
            except Exception:
                pass  # Fall through to manual detection
        
        # Fallback to simple detection based on magic bytes
        if content.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        elif content.startswith(b'\x89PNG\r\n\x1a\n'):
            return "image/png"
        elif content.startswith(b'RIFF') and b'WEBP' in content[:20]:
            return "image/webp"
        else:
            return "application/octet-stream"
    
    def _get_extension_for_mime_type(self, mime_type: str) -> str:
        """
        Get file extension for a MIME type.
        
        Args:
            mime_type: MIME type string
            
        Returns:
            File extension with leading dot
        """
        extensions = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        return extensions.get(mime_type, ".bin")


# Global file service instance
file_service = FileService()
