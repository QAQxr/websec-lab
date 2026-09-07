from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return a timezone-naive UTC value suitable for MySQL DATETIME columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
