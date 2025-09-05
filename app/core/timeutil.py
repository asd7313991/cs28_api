import pytz
from datetime import datetime
TZ = pytz.timezone("Asia/Shanghai")

def now_sh() -> datetime:
    return datetime.now(TZ)

def to_naive(dt: datetime) -> datetime:
    if dt.tzinfo:
        return dt.astimezone(TZ).replace(tzinfo=None)
    return dt
