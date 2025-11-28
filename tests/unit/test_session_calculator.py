from datetime import datetime

import pytest

from src.amsterdam_parking.session_calculator import Period, split_period_in_sessions


@pytest.mark.parametrize(
    "parking_period, session_duration, break_duration, sessions_validate",
    [
        (
            Period(start=datetime(2025, 11, 28, 13), end=datetime(2025, 11, 28, 14)),
            5,
            10,
            [
                Period(datetime(2025, 11, 28, 13), datetime(2025, 11, 28, 13, 5)),
                Period(datetime(2025, 11, 28, 13, 15), datetime(2025, 11, 28, 13, 20)),
                Period(datetime(2025, 11, 28, 13, 30), datetime(2025, 11, 28, 13, 35)),
                Period(datetime(2025, 11, 28, 13, 45), datetime(2025, 11, 28, 13, 50)),
            ],
        ),
        (
            Period(start=datetime(2025, 11, 28, 13, 5), end=datetime(2025, 11, 28, 14)),
            5,
            10,
            [
                Period(datetime(2025, 11, 28, 13, 5), datetime(2025, 11, 28, 13, 10)),
                Period(datetime(2025, 11, 28, 13, 20), datetime(2025, 11, 28, 13, 25)),
                Period(datetime(2025, 11, 28, 13, 35), datetime(2025, 11, 28, 13, 40)),
                Period(datetime(2025, 11, 28, 13, 50), datetime(2025, 11, 28, 13, 55)),
            ],
        ),
        (
            Period(start=datetime(2025, 11, 28, 13), end=datetime(2025, 11, 28, 14, 5)),
            5,
            10,
            [
                Period(datetime(2025, 11, 28, 13), datetime(2025, 11, 28, 13, 5)),
                Period(datetime(2025, 11, 28, 13, 15), datetime(2025, 11, 28, 13, 20)),
                Period(datetime(2025, 11, 28, 13, 30), datetime(2025, 11, 28, 13, 35)),
                Period(datetime(2025, 11, 28, 13, 45), datetime(2025, 11, 28, 13, 50)),
                Period(datetime(2025, 11, 28, 14, 0), datetime(2025, 11, 28, 14, 5)),
            ],
        ),
        (
            Period(
                start=datetime(2025, 11, 28, 13), end=datetime(2025, 11, 28, 14, 10)
            ),
            5,
            10,
            [
                Period(datetime(2025, 11, 28, 13), datetime(2025, 11, 28, 13, 5)),
                Period(datetime(2025, 11, 28, 13, 15), datetime(2025, 11, 28, 13, 20)),
                Period(datetime(2025, 11, 28, 13, 30), datetime(2025, 11, 28, 13, 35)),
                Period(datetime(2025, 11, 28, 13, 45), datetime(2025, 11, 28, 13, 50)),
                Period(datetime(2025, 11, 28, 14, 0), datetime(2025, 11, 28, 14, 5)),
            ],
        ),
        (
            Period(start=datetime(2025, 11, 28, 13), end=datetime(2025, 11, 28, 14, 5)),
            10,
            10,
            [
                Period(datetime(2025, 11, 28, 13), datetime(2025, 11, 28, 13, 10)),
                Period(datetime(2025, 11, 28, 13, 20), datetime(2025, 11, 28, 13, 30)),
                Period(datetime(2025, 11, 28, 13, 40), datetime(2025, 11, 28, 13, 50)),
                Period(datetime(2025, 11, 28, 14, 0), datetime(2025, 11, 28, 14, 5)),
            ],
        ),
    ],
    ids=[
        "13:00-14:00@5/10",
        "13:05-14:00@5/10",
        "13:00-14:05@5/10",
        "13:00-14:10@5/10",
        "13:00-14:05@10/10",
    ],
)
def test_split_period_in_sessions(
    parking_period, session_duration, break_duration, sessions_validate
):
    print(parking_period)
    sessions = split_period_in_sessions(
        parking_period, session_duration, break_duration
    )
    assert sessions
    assert len(sessions) == len(sessions_validate)
    for i in range(len(sessions)):
        assert sessions[i] == sessions_validate[i]


# def test_split_period_in_sessions():
#     parking_period = Period(
#         start=datetime(2025, 11, 28, 13, 0), end=datetime(2025, 11, 28, 14)
#     )
#     session_duration = 5
#     break_duration = 10
#
#     sessions = split_period_in_sessions(
#         parking_period, session_duration, break_duration
#     )
#
#     assert sessions
#     assert len(sessions) == 4
#
#     sessions_validate = [
#         Period(datetime(2025, 11, 28, 13), datetime(2025, 11, 28, 13, 5)),
#         Period(datetime(2025, 11, 28, 13, 15), datetime(2025, 11, 28, 13, 20)),
#         Period(datetime(2025, 11, 28, 13, 30), datetime(2025, 11, 28, 13, 35)),
#         Period(datetime(2025, 11, 28, 13, 45), datetime(2025, 11, 28, 13, 50)),
#     ]
#     for i in range(len(sessions_validate)):
#         assert sessions[i] == sessions_validate[i]
