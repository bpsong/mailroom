"""Password hashing, verification, and policy enforcement (Argon2id)."""

import json
import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

from app.config import settings


def _build_hasher() -> PasswordHasher:
    """Build the Argon2 hasher from configured work factors."""
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
    )


_password_hasher = _build_hasher()

def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return str(_password_hasher.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: Hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    try:
        _password_hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHash, VerificationError):
        # Wrong password, corrupt hash, or unsupported hash format:
        # all mean "not verified", never a 500.
        return False


def validate_password_strength(password: str) -> tuple[bool, str | None]:
    """
    Validate password meets strength requirements.

    Requirements:
    - At least 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < settings.password_min_length:
        return False, f"Password must be at least {settings.password_min_length} characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"

    return True, None


def check_password_history(password: str, password_history: str | None) -> bool:
    """
    Check if password was used in recent history.

    Args:
        password: Plain text password to check
        password_history: JSON string of previous password hashes

    Returns:
        True if password is in history (should be rejected), False otherwise
    """
    if not password_history:
        return False

    try:
        history = json.loads(password_history)
        if not isinstance(history, list):
            return False

        # Check against last N passwords
        for old_hash in history[-settings.password_history_count:]:
            if verify_password(password, old_hash):
                return True

        return False
    except (json.JSONDecodeError, TypeError, AttributeError):
        # Corrupt history payload or non-string entries: treat as no match
        # rather than failing authentication flows.
        return False


def update_password_history(current_hash: str, 
    password_history: str | None
) -> str:
    """
    Update password history with new hash.

    Args:
        current_hash: New password hash to add
        password_history: Existing password history JSON string

    Returns:
        Updated password history JSON string
    """
    try:
        if password_history:
            history = json.loads(password_history)
            if not isinstance(history, list):
                history = []
        else:
            history = []
    except json.JSONDecodeError:
        history = []

    # Add current hash to history
    history.append(current_hash)

    # Keep only the last N+1 passwords (current + history)
    history = history[-(settings.password_history_count + 1):]

    return json.dumps(history)
