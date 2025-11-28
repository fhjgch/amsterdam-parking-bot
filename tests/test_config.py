"""Tests for configuration management."""

from pathlib import Path

import pytest

from amsterdam_parking.config import AppConfig


class TestAppConfig:
    """Test configuration management."""

    def test_config_validation(self) -> None:
        """Test configuration validation."""
        config = AppConfig(
            username="test_user",
            password="test_pass",
        )

        assert config.username == "test_user"
        assert config.session_duration_minutes == 10  # default

    def test_config_from_json(self, config_file: Path) -> None:
        """Test loading config from JSON."""
        config_data = {
            "username": "json_user",
            "password": "json_pass",
            "session_duration_minutes": 15,
        }

        import json

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = AppConfig.from_json(config_file)

        assert config.username == "json_user"
        assert config.session_duration_minutes == 15

    def test_config_to_json(self, config_file: Path) -> None:
        """Test saving config to JSON."""
        config = AppConfig(
            username="save_user",
            password="save_pass",
            session_duration_minutes=20,
        )

        config.to_json(config_file)

        assert config_file.exists()

        import json

        with open(config_file) as f:
            data = json.load(f)

        assert data["username"] == "save_user"
        assert data["session_duration_minutes"] == 20

    def test_invalid_log_level(self) -> None:
        """Test invalid log level raises error."""
        with pytest.raises(ValueError, match="Log level must be one of"):
            AppConfig(
                username="test",
                password="test",
                log_level="INVALID",
            )
