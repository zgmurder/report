from datetime import datetime
from zoneinfo import ZoneInfo

LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")


def local_now() -> datetime:
    """Return local business time as a naive datetime for MySQL DATETIME columns."""
    return datetime.now(LOCAL_TIMEZONE).replace(tzinfo=None)
