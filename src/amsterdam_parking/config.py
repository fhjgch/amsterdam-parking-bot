"""Configuration management using Pydantic Settings."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application configuration with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PARKING_",
        case_sensitive=False,
        extra="ignore",
    )

    # Authentication
    username: str = Field(..., description="Amsterdam parking meldcode")
    password: str = Field(..., description="Amsterdam parking pincode")
    license_plate: str = Field(default="MQR108", description="Vehicle license plate")

    # Session configuration
    session_duration_minutes: int = Field(
        default=10, ge=5, le=60, description="Duration of each session in minutes"
    )
    max_break_minutes: int = Field(
        default=5, ge=1, le=15, description="Maximum break between sessions"
    )

    # Limits and thresholds
    balance_warning_threshold: float = Field(
        default=30.0, ge=0.0, description="Warn when balance drops below this amount (€)"
    )
    monthly_time_budget: int = Field(
        default=150, ge=0, description="Monthly parking time budget (hours)"
    )
    max_retries: int = Field(default=3, ge=1, le=10, description="Max retry attempts per session")

    # Browser settings
    headless: bool = Field(default=False, description="Run browser in headless mode")
    timeout_seconds: int = Field(
        default=15, ge=5, le=60, description="WebDriver timeout in seconds"
    )
    chromedriver_path: str = Field(
        default="/usr/bin/chromedriver", description="Path to chromedriver executable"
    )

    # URLs
    login_url: str = Field(
        default="https://aanmeldenparkeren.amsterdam.nl/login",
        description="Login page URL",
    )
    new_session_url: str = Field(
        default="https://aanmeldenparkeren.amsterdam.nl/parking-sessions/new",
        description="New session booking URL",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Path | None = Field(default=None, description="Optional log file path")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {', '.join(valid_levels)}")
        return v_upper

    @classmethod
    def from_json(cls, config_path: Path) -> "AppConfig":
        """Load configuration from JSON file."""
        import json

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            data = json.load(f)

        return cls(**data)

    def to_json(self, config_path: Path) -> None:
        """Save configuration to JSON file."""
        import json

        with open(config_path, "w") as f:
            json.dump(self.model_dump(mode="json", exclude_none=True), f, indent=2)

    @classmethod
    def create_default(cls, config_path: Path) -> "AppConfig":
        """Create default configuration file if it doesn't exist."""
        if config_path.exists():
            return cls.from_json(config_path)

        # Create default config
        default_config = cls(
            username="your_meldcode_here",
            password="your_pincode_here",
        )
        default_config.to_json(config_path)

        raise ValueError(
            f"Created default config at {config_path}. "
            "Please update with your credentials and run again."
        )
