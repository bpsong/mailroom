"""File upload and storage service."""

import uuid
from pathlib import Path
from typing import Any, cast

from fastapi import UploadFile

from app.clock import utc_now
from app.config import settings
from app.utils.sanitization import validate_file_content

# Try to import python-magic, but fall back to manual detection if not available.
# Annotated as Any up front so the fallback assignment type-checks.
magic: Any
try:
    import magic
except (ImportError, OSError):  # pragma: no cover - environment dependent
    magic = None

MAGIC_AVAILABLE = magic is not None


class FileService:
    """Service for handling file uploads and storage."""

    # Fallback defaults used when settings are unavailable (e.g. bare import
    # in scripts). Normal operation always takes these from Settings so that
    # MAX_UPLOAD_SIZE / ALLOWED_IMAGE_TYPES env vars take effect.
    ALLOWED_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

    def __init__(
        self,
        upload_dir: str | None = None,
        max_file_size: int | None = None,
        allowed_mime_types: set[str] | list[str] | None = None,
    ):
        """
        Initialize file service.

        Args:
            upload_dir: Base directory for uploads (defaults to settings.upload_dir)
            max_file_size: Maximum upload size in bytes
                (defaults to settings.max_upload_size)
            allowed_mime_types: Allowed MIME types
                (defaults to settings.allowed_image_types_list)
        """
        self.upload_dir = Path(upload_dir or settings.upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = (
            max_file_size if max_file_size is not None else settings.max_upload_size
        )
        if allowed_mime_types is None:
            allowed_mime_types = list(settings.allowed_image_types_list)
        self.allowed_mime_types = set(allowed_mime_types)
    
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
        if file_size > self.max_file_size:
            raise ValueError(
                f"File size ({file_size} bytes) exceeds maximum allowed "
                f"size ({self.max_file_size} bytes)"
            )

        # Validate file type by content (not just extension)
        mime_type = validate_file_content(content, sorted(self.allowed_mime_types))
        if not mime_type:
            detected = self._detect_mime_type(content)
            raise ValueError(
                f"File type '{detected}' is not allowed. "
                f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}"
            )
        
        # Generate unique filename with timestamp
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        extension = self._get_extension_for_mime_type(mime_type)
        filename = f"{timestamp}_{unique_id}{extension}"
        
        # Organize by year/month directory structure
        now = utc_now()
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
        allowed_types: list[str] | set[str] | None = None,
        max_size: int | None = None,
    ) -> None:
        """
        Header-level pre-check without reading the file body.

        This cannot verify content (that happens in :meth:`save_upload`);
        it only rejects requests whose declared size or content type already
        violate the limits, so oversized bodies fail fast at the edge.

        Args:
            file: Uploaded file object
            allowed_types: Allowed MIME types (defaults to this service's allowlist)
            max_size: Maximum file size in bytes (defaults to this service's limit)

        Raises:
            ValueError: If the declared headers violate the limits
        """
        allowed = set(allowed_types) if allowed_types is not None else self.allowed_mime_types
        limit = max_size if max_size is not None else self.max_file_size

        # Check file size from content-length header if available
        if file.size and file.size > limit:
            raise ValueError(
                f"File size ({file.size} bytes) exceeds maximum allowed "
                f"size ({limit} bytes)"
            )

        # Check declared content type (client-supplied: pre-check only,
        # content is re-validated by magic bytes in save_upload).
        if file.content_type and file.content_type not in allowed:
            raise ValueError(
                f"Content type '{file.content_type}' is not allowed. "
                f"Allowed types: {', '.join(sorted(allowed))}"
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
        if MAGIC_AVAILABLE and magic is not None:
            try:
                # Try using python-magic if available
                mime = magic.Magic(mime=True)
                return cast(str, mime.from_buffer(content))
            except Exception:  # noqa: BLE001 - libmagic failures must fall through to manual detection
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
