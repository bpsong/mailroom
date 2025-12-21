"""Input sanitization utilities."""

import re
from typing import Optional


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename with only safe characters
    """
    # Remove any path components
    filename = filename.split("/")[-1].split("\\")[-1]
    
    # Remove any non-alphanumeric characters except dots, dashes, and underscores
    filename = re.sub(r"[^\w\-.]", "_", filename)
    
    # Prevent hidden files
    if filename.startswith("."):
        filename = "_" + filename[1:]
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + ("." + ext if ext else "")
    
    return filename


def sanitize_search_query(query: str, max_length: int = 100) -> str:
    """
    Sanitize search query to prevent injection attacks.
    
    Args:
        query: Search query string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized query string
    """
    # Trim whitespace
    query = query.strip()
    
    # Limit length
    if len(query) > max_length:
        query = query[:max_length]
    
    # Remove null bytes
    query = query.replace("\x00", "")
    
    return query


def validate_uuid(uuid_str: str) -> bool:
    """
    Validate UUID format to prevent injection.
    
    Args:
        uuid_str: UUID string to validate
        
    Returns:
        True if valid UUID format, False otherwise
    """
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )
    return bool(uuid_pattern.match(uuid_str))


def sanitize_html_input(text: str) -> str:
    """
    Sanitize HTML input by removing potentially dangerous characters.
    
    Note: Jinja2 auto-escaping should handle most XSS prevention,
    but this provides an additional layer of defense.
    
    Args:
        text: Input text
        
    Returns:
        Sanitized text
    """
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Remove control characters except newlines and tabs
    text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
    
    return text


def validate_file_type(filename: str, allowed_types: list[str]) -> bool:
    """
    Validate file type by extension.
    
    Args:
        filename: Filename to validate
        allowed_types: List of allowed MIME types
        
    Returns:
        True if file type is allowed, False otherwise
    """
    # Get file extension
    if "." not in filename:
        return False
    
    ext = filename.rsplit(".", 1)[1].lower()
    
    # Map extensions to MIME types
    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "pdf": "application/pdf",
        "csv": "text/csv",
    }
    
    mime_type = mime_map.get(ext)
    return mime_type in allowed_types if mime_type else False


def validate_file_content(content: bytes, allowed_types: list[str]) -> Optional[str]:
    """
    Validate file content by checking magic bytes.
    
    Args:
        content: File content bytes
        allowed_types: List of allowed MIME types
        
    Returns:
        Detected MIME type if valid, None otherwise
    """
    # Check magic bytes for common file types
    if content.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        mime_type = "image/webp"
    elif content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        mime_type = "image/gif"
    elif content.startswith(b"%PDF"):
        mime_type = "application/pdf"
    else:
        return None
    
    return mime_type if mime_type in allowed_types else None


# SQL Injection Prevention Guidelines
# ====================================
# 
# ALWAYS use parameterized queries with placeholders (?)
# NEVER concatenate user input directly into SQL strings
# 
# GOOD:
#   conn.execute("SELECT * FROM users WHERE username = ?", [username])
# 
# BAD:
#   conn.execute(f"SELECT * FROM users WHERE username = '{username}'")
# 
# When building dynamic WHERE clauses:
# - Build clause structure from hardcoded strings
# - Pass all user inputs as parameters
# 
# GOOD:
#   where_clauses = []
#   params = []
#   if query:
#       where_clauses.append("name LIKE ?")
#       params.append(f"%{query}%")
#   where_sql = " AND ".join(where_clauses) or "1=1"
#   conn.execute(f"SELECT * FROM table WHERE {where_sql}", params)
# 
# The f-string is safe here because where_sql contains only hardcoded strings,
# and all user inputs are in the params list.


# XSS Prevention Guidelines
# ==========================
# 
# Jinja2 auto-escaping is ENABLED by default for .html templates
# This automatically escapes HTML special characters: < > & " '
# 
# To explicitly mark content as safe (use with caution):
#   {{ content | safe }}
# 
# To explicitly escape content:
#   {{ content | escape }}
# 
# For user-generated content that may contain HTML:
# - Use auto-escaping (default behavior)
# - Or use a HTML sanitization library like bleach
# 
# Additional protection:
# - Set Content-Security-Policy headers
# - Validate and sanitize all user inputs
# - Use HttpOnly cookies for session tokens
