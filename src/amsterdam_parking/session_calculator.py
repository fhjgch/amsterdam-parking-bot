"""Session calculation and optimization logic."""

from datetime import datetime, timedelta

from amsterdam_parking.models import ParkingSession


class SessionCalculator:
    """Calculate optimal parking session splits."""

    def __init__(self, session_duration_minutes: int, max_break_minutes: int):
        """Initialize calculator with session parameters.

        Args:
            session_duration_minutes: Duration of each session
            max_break_minutes: Maximum break between sessions
        """
        self.session_duration = session_duration_minutes
        self.max_break = max_break_minutes

    def parse_time_range(
        self, time_range: str, target_date: datetime | None = None
    ) -> tuple[datetime, datetime]:
        """Parse time range string into datetime objects.

        Args:
            time_range: Time range string like "13:00-14:00"
            target_date: Optional target date (defaults to today)

        Returns:
            Tuple of (start_time, end_time)

        Raises:
            ValueError: If time range format is invalid
        """
        if "-" not in time_range:
            raise ValueError("Time range must contain '-' (e.g., '13:00-14:00')")

        start_str, end_str = [t.strip() for t in time_range.split("-", 1)]
        base_date = target_date.date() if target_date else datetime.now().date()

        try:
            start_time = datetime.strptime(f"{base_date} {start_str}", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{base_date} {end_str}", "%Y-%m-%d %H:%M")
        except ValueError as e:
            raise ValueError(f"Invalid time format: {e}") from e

        if end_time <= start_time:
            if target_date is None:
                end_time += timedelta(days=1)
            else:
                raise ValueError("End time must be after start time")

        return start_time, end_time

    def calculate_sessions(
        self, start_time: datetime, end_time: datetime
    ) -> list[ParkingSession]:
        """Calculate optimal session splits.

        Args:
            start_time: Start of parking period
            end_time: End of parking period

        Returns:
            List of ParkingSession objects
        """
        total_minutes = int((end_time - start_time).total_seconds() / 60)
        sessions: list[ParkingSession] = []
        current_time = start_time

        while current_time < end_time:
            session_end = min(
                current_time + timedelta(minutes=self.session_duration), end_time
            )
            sessions.append(ParkingSession(start_time=current_time, end_time=session_end))

            if session_end >= end_time:
                break

            # Smart break calculation - avoid tiny final sessions
            remaining = int((end_time - session_end).total_seconds() / 60)
            if remaining <= self.session_duration:
                break

            current_time = session_end + timedelta(minutes=self.max_break)

        return sessions

    def format_sessions(self, sessions: list[ParkingSession]) -> str:
        """Format sessions for display.

        Args:
            sessions: List of parking sessions

        Returns:
            Formatted string representation
        """
        return ", ".join(str(session) for session in sessions)
