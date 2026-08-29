from datetime import datetime, timedelta, timezone

# 业务统一使用东八区墙钟时间写入/展示
CN_TZ = timezone(timedelta(hours=8))


def ensure_cn(value: datetime) -> datetime:
    """naive 时间视为东八区；有时区则转换到东八区。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=CN_TZ)
    return value.astimezone(CN_TZ)


def to_iso_cn(value: datetime) -> str:
    return ensure_cn(value).isoformat()
