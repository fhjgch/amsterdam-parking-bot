from src.amsterdam_parking.session_calculator import (
    ParkingPeriod,
    split_period_in_sessions,
)


def test_split_period_in_sessions():
    parking_period = ParkingPeriod(start="13:00", end="14:00")
    session_duration = 5
    break_duration = 10
    sessions = split_period_in_sessions(
        parking_period, session_duration, break_duration
    )
