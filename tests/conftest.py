"""Pytest configuration and fixtures."""

from datetime import datetime
from pathlib import Path

import pytest

from amsterdam_parking.config import AppConfig
from amsterdam_parking.models import ParkingSession


@pytest.fixture
def test_config() -> AppConfig:
    """Provide test configuration."""
    return AppConfig(
        username="test_user",
        password="test_pass",
        license_plate="TEST123",
        session_duration_minutes=10,
        max_break_minutes=5,
        headless=True,
    )


@pytest.fixture
def sample_session() -> ParkingSession:
    """Provide sample parking session."""
    return ParkingSession(
        start_time=datetime(2025, 1, 1, 13, 0),
        end_time=datetime(2025, 1, 1, 13, 10),
    )


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Provide temporary config file path."""
    return tmp_path / "test_config.json"
