"""Application configuration management."""

import os
import sys
import logging
from pathlib import Path
from typing import Literal

from pydantic import field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["development", "production", "testing"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str

    # Database
    database_path: str = "./data/mailroom.duckdb"
    database_checkpoint_interval: int = 300

    # File Storage
    upload_dir: str = "./uploads"
    max_upload_size: int = 5242880  # 5MB
    allowed_image_types: str = "image/jpeg,image/png,image/webp"

    # Security
    session_timeout: int = 1800  # 30 minutes
    max_concurrent_sessions: int = 3  # Maximum concurrent sessions per user
    max_failed_logins: int = 5
    account_lockout_duration: int = 1800  # 30 minutes
    password_min_length: int = 12
    password_history_count: int = 3

    # Argon2
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 19456  # 19MB in KiB
    argon2_parallelism: int = 1

    # Rate Limiting
    rate_limit_login: int = 10  # requests per minute
    rate_limit_api: int = 100  # requests per minute

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/mailroom.log"
    log_rotation: str = "weekly"
    log_retention_days: int = 365

    # HTTPS
    domain: str = "mailroom.company.local"
    tls_cert_path: str = "./certs/cert.pem"
    tls_key_path: str = "./certs/key.pem"

    @property
    def allowed_image_types_list(self) -> list[str]:
        """Get allowed image types as a list."""
        return [t.strip() for t in self.allowed_image_types.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.app_env == "testing"
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Validate that secret key is set and secure in production."""
        if not v:
            raise ValueError("SECRET_KEY must be set")
        
        # Check if using default insecure key in production
        if info.data.get("app_env") == "production":
            if "change-this" in v.lower() or len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be changed from default and be at least 32 characters in production"
                )
        
        return v
    
    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, v: str) -> str:
        """Ensure database directory exists."""
        db_path = Path(v)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("upload_dir")
    @classmethod
    def validate_upload_dir(cls, v: str) -> str:
        """Ensure upload directory exists."""
        upload_path = Path(v)
        upload_path.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("log_file")
    @classmethod
    def validate_log_file(cls, v: str) -> str:
        """Ensure log directory exists."""
        log_path = Path(v)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return v


def load_settings() -> Settings:
    """
    Load and validate application settings.
    
    Returns:
        Settings instance
        
    Raises:
        SystemExit: If configuration is invalid
    """
    try:
        settings = Settings()
        
        # Log configuration status
        logger.info(f"Configuration loaded successfully")
        logger.info(f"Environment: {settings.app_env}")
        logger.info(f"Database: {settings.database_path}")
        logger.info(f"Upload directory: {settings.upload_dir}")
        logger.info(f"Log file: {settings.log_file}")
        
        # Validate required directories exist
        required_dirs = [
            Path(settings.database_path).parent,
            Path(settings.upload_dir),
            Path(settings.log_file).parent,
        ]
        
        for directory in required_dirs:
            if not directory.exists():
                logger.error(f"Required directory does not exist: {directory}")
                sys.exit(1)
        
        # Production-specific validations
        if settings.is_production:
            logger.info("Running in PRODUCTION mode")
            
            # Warn about insecure configurations
            if settings.app_host == "0.0.0.0":
                logger.warning(
                    "APP_HOST is set to 0.0.0.0 - ensure this is behind a reverse proxy"
                )
            
            if not settings.domain or settings.domain == "mailroom.company.local":
                logger.warning(
                    "DOMAIN is not configured - HTTPS certificates may not work correctly"
                )
        
        else:
            logger.info(f"Running in {settings.app_env.upper()} mode")
        
        return settings
    
    except ValidationError as e:
        logger.error("Configuration validation failed:")
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            logger.error(f"  {field}: {error['msg']}")
        
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)


# Global settings instance
settings = load_settings()
