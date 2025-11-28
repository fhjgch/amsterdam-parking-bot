from copy import copy
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Period:
    start: datetime
    end: datetime


def split_period_in_sessions(parking_period, session_duration, break_duration):
    sessions = []
    session_period = copy(parking_period)
    while session_period.start < parking_period.end:
        session_period.end = session_period.start + timedelta(minutes=session_duration)
        if session_period.end > parking_period.end:
            session_period.end = parking_period.end
        sessions.append(copy(session_period))
        session_period.start = session_period.end + timedelta(minutes=break_duration)
    return sessions
