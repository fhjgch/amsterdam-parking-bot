"""Tests for data models."""

from datetime import datetime

import pytest

from amsterdam_parking.models import BookingSummary, ParkingSession


class TestParkingSession:
    """Test ParkingSession model."""

    def test_valid_session(self) -> None:
        """Test valid session creation."""
        session = ParkingSession(
            start_time=datetime(2025, 1, 1, 13, 0),
            end_time=datetime(2025, 1, 1, 14, 0),
        )

        assert session.duration_minutes == 60
        assert str(session) == "13:00-14:00"

    def test_invalid_session(self) -> None:
        """Test that end_time before start_time raises error."""
        with pytest.raises(ValueError, match="End time must be after start time"):
            ParkingSession(
                start_time=datetime(2025, 1, 1, 14, 0),
                end_time=datetime(2025, 1, 1, 13, 0),
            )


class TestBookingSummary:
    """Test BookingSummary model."""

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        summary = BookingSummary(
            total_sessions=10,
            successful_sessions=8,
            failed_sessions=2,
        )

        assert summary.success_rate == 80.0

    def test_success_rate_zero_sessions(self) -> None:
        """Test success rate with zero sessions."""
        summary = BookingSummary(
            total_sessions=0,
            successful_sessions=0,
            failed_sessions=0,
        )

        assert summary.success_rate == 0.0
