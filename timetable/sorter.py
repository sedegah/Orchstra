import re
from datetime import datetime
from typing import Optional

_DATE_FMTS = [
    "%A, %B %d, %Y",
    "%A, %B %d %Y",
    "%B %d, %Y",
    "%B %d %Y",
    "%d %B %Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%B %d",
    "%d %B",
]
_TIME_FMTS = ["%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"]
_CURRENT_YEAR = datetime.now().year


def _parse_date(s: str) -> Optional[datetime]:
    if not s:
        return None
    s = re.sub(r"(\d+)(st|nd|rd|th)", r"", s.strip(), flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    for fmt in _DATE_FMTS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(year=_CURRENT_YEAR) if dt.year == 1900 else dt
        except ValueError:
            continue
    return None


def _parse_time(s: str) -> tuple[int, int]:
    if not s:
        return 0, 0
    s = re.sub(r"\s+", " ", s.strip().upper())
    s = re.sub(r"(\d)(AM|PM)", r" ", s)
    for fmt in _TIME_FMTS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.hour, dt.minute
        except ValueError:
            continue
    return 0, 0


def make_exam_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    dt = _parse_date(date_str)
    if dt is None:
        return None
    h, m = _parse_time(time_str)
    return dt.replace(hour=h, minute=m, second=0, microsecond=0)


def format_short_date(date_str: str) -> str:
    dt = _parse_date(date_str)
    if dt:
        return dt.strftime("%a, %b %d, %Y")
    return date_str


def format_clean_time(time_str: str) -> str:
    if not time_str:
        return ""
    clean = re.sub(r"\s+", "", time_str.strip().upper())
    m = re.match(r"^(\d{1,2}:\d{2})(AM|PM)?$", clean)
    if m:
        t_part = m.group(1)
        ampm = m.group(2) or ""
        return f"{t_part} {ampm}".strip()
    return time_str


def sort_entries(entries: list[dict]) -> list[dict]:
    def key(e):
        dt = make_exam_datetime(e.get("exam_date", ""), e.get("exam_time", ""))
        return (0, dt) if dt else (1, datetime.max)

    sorted_list = sorted(entries, key=key)
    for e in sorted_list:
        if e.get("exam_date"):
            e["exam_date"] = format_short_date(e["exam_date"])
        if e.get("exam_time"):
            e["exam_time"] = format_clean_time(e["exam_time"])

    return sorted_list
