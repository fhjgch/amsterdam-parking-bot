"""Data models for parking sessions and configuration."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ParkingSession(BaseModel):
    """Represents a single parking session."""

    start_time: datetime
    end_time: datetime

    @field_validator("end_time")
    @classmethod
    def validate_end_after_start(cls, v: datetime, info: Any) -> datetime:
        """Ensure end time is after start time."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("End time must be after start time")
        return v

    @property
    def duration_minutes(self) -> int:
        """Calculate session duration in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def __str__(self) -> str:
        """Format session as HH:MM-HH:MM."""
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"


class BookingResult(BaseModel):
    """Result of a booking operation."""

    session: ParkingSession
    success: bool
    error_message: str | None = None
    attempt_count: int = Field(default=1, ge=1)


class BookingSummary(BaseModel):
    """Summary of multiple booking operations."""

    total_sessions: int = Field(ge=0)
    successful_sessions: int = Field(ge=0)
    failed_sessions: int = Field(ge=0)
    cost: float = Field(default=0.0, ge=0.0)
    results: list[BookingResult] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_sessions == 0:
            return 0.0
        return (self.successful_sessions / self.total_sessions) * 100
