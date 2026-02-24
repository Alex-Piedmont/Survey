from datetime import datetime, timedelta, timezone


def calculate_penalty(deadline: datetime, submitted_at: datetime) -> tuple[bool, int]:
    """Calculate late penalty based on elapsed time after deadline.

    Returns (is_late, penalty_pct).
    If submitted before deadline, returns (False, 0).
    If submitted after 7 days, returns (True, -1) to indicate rejection.
    """
    # Normalize both to UTC-aware for comparison (SQLite may strip tzinfo)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    if submitted_at.tzinfo is None:
        submitted_at = submitted_at.replace(tzinfo=timezone.utc)

    elapsed = submitted_at - deadline
    if elapsed <= timedelta(0):
        return False, 0

    hours = elapsed.total_seconds() / 3600

    if hours <= 24:
        return True, 5
    elif hours <= 48:
        return True, 10
    elif hours <= 72:
        return True, 30
    elif elapsed <= timedelta(days=7):
        return True, 50
    else:
        return True, -1  # Rejected
