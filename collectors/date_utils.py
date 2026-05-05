from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser


def parse_date(value):
    if not value:
        return None

    try:
        dt = date_parser.parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def is_within_days(value, days=7):
    dt = parse_date(value)

    # 날짜 없으면 일단 유지
    # 나중에 AI 필터/히스토리 중복 제거에서 처리
    if dt is None:
        return True

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return dt >= cutoff