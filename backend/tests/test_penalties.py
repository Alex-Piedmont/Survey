from datetime import datetime, timedelta, timezone

from app.services.penalties import calculate_penalty

DEADLINE = datetime(2026, 2, 24, 0, 29, 0, tzinfo=timezone.utc)  # 23:59 + 30min grace


class TestPenaltyCalculation:
    def test_on_time(self):
        submitted = DEADLINE - timedelta(minutes=5)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is False
        assert pct == 0

    def test_exactly_at_deadline(self):
        is_late, pct = calculate_penalty(DEADLINE, DEADLINE)
        assert is_late is False
        assert pct == 0

    def test_1_second_late(self):
        submitted = DEADLINE + timedelta(seconds=1)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 5

    def test_12_hours_late(self):
        submitted = DEADLINE + timedelta(hours=12)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 5

    def test_exactly_24_hours(self):
        submitted = DEADLINE + timedelta(hours=24)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 5  # 0-24 hours boundary

    def test_24_hours_1_second(self):
        submitted = DEADLINE + timedelta(hours=24, seconds=1)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 10

    def test_36_hours_late(self):
        submitted = DEADLINE + timedelta(hours=36)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 10

    def test_exactly_48_hours(self):
        submitted = DEADLINE + timedelta(hours=48)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 10

    def test_48_hours_1_second(self):
        submitted = DEADLINE + timedelta(hours=48, seconds=1)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 30

    def test_60_hours_late(self):
        submitted = DEADLINE + timedelta(hours=60)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 30

    def test_exactly_72_hours(self):
        submitted = DEADLINE + timedelta(hours=72)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 30

    def test_72_hours_1_second(self):
        submitted = DEADLINE + timedelta(hours=72, seconds=1)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 50

    def test_5_days_late(self):
        submitted = DEADLINE + timedelta(days=5)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 50

    def test_exactly_7_days(self):
        submitted = DEADLINE + timedelta(days=7)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == 50

    def test_7_days_1_second_rejected(self):
        submitted = DEADLINE + timedelta(days=7, seconds=1)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == -1  # Rejected

    def test_30_days_rejected(self):
        submitted = DEADLINE + timedelta(days=30)
        is_late, pct = calculate_penalty(DEADLINE, submitted)
        assert is_late is True
        assert pct == -1
