"""Tests for session calculator."""

from datetime import datetime

import pytest

from amsterdam_parking.models import ParkingSession
from amsterdam_parking.session_calculator import SessionCalculator


class TestSessionCalculator:
    """Test session calculation logic."""

    def test_parse_valid_time_range(self) -> None:
        """Test parsing valid time range."""
        calculator = SessionCalculator(10, 5)
        start, end = calculator.parse_time_range("13:00-14:00")

        assert start.hour == 13
        assert start.minute == 0
        assert end.hour == 14
        assert end.minute == 0

    def test_parse_invalid_time_range(self) -> None:
        """Test parsing invalid time range."""
        calculator = SessionCalculator(10, 5)

        with pytest.raises(ValueError, match="must contain '-'"):
            calculator.parse_time_range("13:00")

    def test_calculate_single_session(self) -> None:
        """Test calculation for time within single session."""
        calculator = SessionCalculator(15, 5)
        start = datetime(2025, 1, 1, 13, 0)
        end = datetime(2025, 1, 1, 13, 10)

        sessions = calculator.calculate_sessions(start, end)

        assert len(sessions) == 1
        assert sessions[0].start_time == start
        assert sessions[0].end_time == end

    def test_calculate_multiple_sessions(self) -> None:
        """Test calculation for multiple sessions."""
        calculator = SessionCalculator(10, 5)
        start = datetime(2025, 1, 1, 13, 0)
        end = datetime(2025, 1, 1, 14, 0)

        sessions = calculator.calculate_sessions(start, end)

        assert len(sessions) == 4
        assert sessions[0].duration_minutes == 10
        # Check breaks between sessions
        assert (sessions[1].start_time - sessions[0].end_time).total_seconds() == 300  # 5 min

    def test_format_sessions(self) -> None:
        """Test session formatting."""
        calculator = SessionCalculator(10, 5)
        sessions = [
            ParkingSession(
                start_time=datetime(2025, 1, 1, 13, 0),
                end_time=datetime(2025, 1, 1, 13, 10),
            ),
            ParkingSession(
                start_time=datetime(2025, 1, 1, 13, 15),
                end_time=datetime(2025, 1, 1, 13, 25),
            ),
        ]

        result = calculator.format_sessions(sessions)
        assert result == "13:00-13:10, 13:15-13:25"
