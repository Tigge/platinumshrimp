"""Schedule and duration parsing utilities for platinumshrimp.

This module parses relative durations (e.g., "117h 32m", "4 days 2 hours", "in 30 mins")
and absolute or natural language dates and times (e.g., "2026-10-18 14:00", "tomorrow at 2pm",
"Friday 15:00", "noon") from the prefix of a message.
"""

import re
from datetime import datetime, time, timedelta

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

_MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DAYS_OF_WEEK = r"(?:Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?)"

_DATE_PATTERNS = [
    r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
    r"\d{1,2}[-/.]\d{1,2}[-/.]\d{4}",
    r"today|tomorrow|tonight",
    r"(?:(?:next|this|on)\s+)?" + _DAYS_OF_WEEK,
    r"(?:"
    + _MONTHS
    + r"\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{4})?|\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+"
    + _MONTHS
    + r"(?:\s*,?\s*\d{4})?)",
]
_DATE_REGEX_STR = r"(?:" + "|".join(_DATE_PATTERNS) + r")"

_TIME_PATTERNS = [
    r"(?:(?:at|@)\s+)?noon\b",
    r"(?:(?:at|@)\s+)?midnight\b",
    r"(?:(?:at|@)\s+)?(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?:\s*(?:am|pm))?",
    r"(?:(?:at|@)\s+)?(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s*(?:am|pm)",
    r"(?:(?:at|@)\s+)(?:[01]?\d|2[0-3])(?::[0-5]\d)?(?:\s*(?:am|pm))?",
]
_TIME_REGEX_STR = r"(?:" + "|".join(_TIME_PATTERNS) + r")"

_UNIT_REGEX = re.compile(
    r"(?:(\d+(?:\.\d+)?)\s*(years?|yrs?|y|months?|mos?|weeks?|wks?|w|days?|d|hours?|hrs?|h|minutes?|mins?|min|m|seconds?|secs?|sec|s)"
    r"|(?:(a|an))\s+(years?|months?|weeks?|days?|hours?|minutes?|seconds?))(?![a-zA-Z])",
    re.IGNORECASE,
)

_DELIM_REGEX = re.compile(r"^(?:\s*,\s*(?:and\s+)?|\s+and\s+|\s+)", re.IGNORECASE)

_ISO_REGEX = re.compile(
    r"^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}[T ]\d{1,2}:\d{2}(?::\d{2})?)(?:\s+(.*)|$)",
    re.IGNORECASE,
)
_DATETIME_1 = re.compile(
    r"^(" + _DATE_REGEX_STR + r")(?:\s*(?:,|at|@)\s*|\s+)(" + _TIME_REGEX_STR + r")(?:\s+(.*)|$)",
    re.IGNORECASE,
)
_DATETIME_2 = re.compile(
    r"^(" + _TIME_REGEX_STR + r")(?:\s*(?:,|on)\s*|\s+)(" + _DATE_REGEX_STR + r")(?:\s+(.*)|$)",
    re.IGNORECASE,
)
_DATE_ONLY = re.compile(r"^(" + _DATE_REGEX_STR + r")(?:\s+(.*)|$)", re.IGNORECASE)
_TIME_ONLY = re.compile(r"^(" + _TIME_REGEX_STR + r")(?:\s+(.*)|$)", re.IGNORECASE)


def _parse_time_str(t_str, default_time=time(12, 0)):
    """Parse time tokens into a datetime.time object."""
    if not t_str:
        return default_time
    t_clean = re.sub(r"^(?:at|@)\s+", "", t_str.strip(), flags=re.IGNORECASE)
    t_lower = t_clean.lower()
    if t_lower == "noon":
        return time(12, 0)
    if t_lower == "midnight":
        return time(0, 0)
    if re.match(r"^\d{1,2}$", t_clean):
        return time(int(t_clean), 0)
    return dateutil_parser.parse(t_clean).time()


def _parse_date_str(d_str, now, time_specified=None):
    """Parse date tokens into a datetime.date object."""
    d_lower = d_str.strip().lower()
    if d_lower == "today":
        return now.date()
    if d_lower == "tomorrow":
        return (now + timedelta(days=1)).date()
    if d_lower == "tonight":
        return now.date()

    day_names = {
        "mon": 0,
        "monday": 0,
        "tue": 1,
        "tuesday": 1,
        "wed": 2,
        "wednesday": 2,
        "thu": 3,
        "thursday": 3,
        "fri": 4,
        "friday": 4,
        "sat": 5,
        "saturday": 5,
        "sun": 6,
        "sunday": 6,
    }
    clean_day = re.sub(r"^(?:next|this|on)\s+", "", d_lower)
    if clean_day in day_names:
        target_wd = day_names[clean_day]
        if "next" in d_lower:
            days_ahead = ((target_wd - now.weekday()) % 7) + 7
        else:
            days_ahead = (target_wd - now.weekday()) % 7
            check_time = time_specified or time(12, 0)
            tentative_dt = datetime.combine(now.date() + timedelta(days=days_ahead), check_time)
            if tentative_dt <= now:
                days_ahead += 7
        return (now + timedelta(days=days_ahead)).date()

    clean_d = re.sub(r"\bof\s+", "", d_str, flags=re.IGNORECASE)
    clean_d = re.sub(r"(\d+)(?:st|nd|rd|th)\b", r"\1", clean_d, flags=re.IGNORECASE)
    dt = dateutil_parser.parse(clean_d, default=now, dayfirst=True)
    d_val = dt.date()
    if not re.search(r"\b\d{4}\b", d_str) and d_val < now.date():
        d_val = (dt + relativedelta(years=1)).date()
    return d_val


def parse_schedule(message, now=None):
    """Parse a date, time, or relative duration prefix from a message.

    Extracts scheduling information from the beginning of `message` and returns
    the computed target `datetime`, the remaining message text, and a boolean
    flag indicating whether a scheduling specification was found.

    Supported formats include:
      - Relative durations: "117h 32m", "4 days 2 hours", "in 30 mins", "+2h",
        "1.5 hours", "in an hour", "1d 2h 30m 10s".
      - Calendar dates and times: "2026-10-18 14:00", "2026/10/18", "18-10-2026 14:00",
        ISO 8601 "2026-10-18T14:00:00".
      - Natural language dates: "tomorrow", "today 18:00", "tonight", "Friday 3pm",
        "next Monday 10:00", "Oct 18 2026 14:00", "18th of October at 2pm".
      - Time expressions: "14:00", "2pm", "2:30pm", "2:30 PM", "noon", "midnight",
        "at 14:00", "@ 2pm", as well as time preceding date ("2pm tomorrow").

    Defaults applied when partial information is provided:
      - Date-only input defaults to 12:00:00 (noon), except "tonight" which defaults to 20:00:00.
      - Time-only input defaults to today's date at the specified time.
      - When no valid time, date, or duration prefix is found, defaults to `now + 1 minute`
        with `is_specified=False` and the entire input returned as `remaining_message`.

    Args:
        message (str): Input string containing scheduling instructions followed by
            the message content (e.g. "4 days 2 hours will it rain?").
        now (datetime, optional): Base reference datetime for calculating relative
            offsets and resolving defaults. Defaults to `datetime.now()`.

    Returns:
        tuple[datetime, str, bool]: A 3-tuple of:
            - target_dt (datetime): Computed schedule datetime (with microsecond=0).
            - remaining_message (str): Message text with schedule prefix stripped.
            - is_specified (bool): True if a schedule was parsed, False otherwise.

    Examples:
        >>> dt, msg, ok = parse_schedule("117h 32m will it rain?")
        >>> dt, msg, ok = parse_schedule("tomorrow at 2pm will it rain?")
        >>> dt, msg, ok = parse_schedule("hello world") # ok is False
    """
    if now is None:
        now = datetime.now()
    now_clean = now.replace(microsecond=0)
    s = message.strip()

    # 1. Try relative duration (e.g. "117h 32m", "4 days 2 hours", "in 30 mins")
    m_lead = re.match(r"^(?:in\s+|\+\s*)", s, re.IGNORECASE)
    pos = m_lead.end() if m_lead else 0

    duration_units = []
    temp_pos = pos
    while temp_pos < len(s):
        m = _UNIT_REGEX.match(s, temp_pos)
        if not m:
            break
        if m.group(1) is not None:
            val = float(m.group(1))
            unit = m.group(2).lower()
        else:
            val = 1.0
            unit = m.group(4).lower()
        duration_units.append((val, unit))
        temp_pos = m.end()
        delim_m = _DELIM_REGEX.match(s[temp_pos:])
        if delim_m:
            temp_pos += delim_m.end()

    if duration_units:
        delta_kwargs = {}
        for val, unit in duration_units:
            if unit in ("y", "yr", "yrs", "year", "years"):
                delta_kwargs["years"] = delta_kwargs.get("years", 0) + val
            elif unit in ("mo", "mos", "month", "months"):
                delta_kwargs["months"] = delta_kwargs.get("months", 0) + val
            elif unit in ("w", "wk", "wks", "week", "weeks"):
                delta_kwargs["weeks"] = delta_kwargs.get("weeks", 0) + val
            elif unit in ("d", "day", "days"):
                delta_kwargs["days"] = delta_kwargs.get("days", 0) + val
            elif unit in ("h", "hr", "hrs", "hour", "hours"):
                delta_kwargs["hours"] = delta_kwargs.get("hours", 0) + val
            elif unit in ("m", "min", "mins", "minute", "minutes"):
                delta_kwargs["minutes"] = delta_kwargs.get("minutes", 0) + val
            elif unit in ("s", "sec", "secs", "second", "seconds"):
                delta_kwargs["seconds"] = delta_kwargs.get("seconds", 0) + val

        target_dt = now_clean + relativedelta(**delta_kwargs)
        target_dt = target_dt.replace(microsecond=0)
        rem_msg = s[temp_pos:].strip()
        return target_dt, rem_msg, True

    # 2. Try date and/or time patterns
    try:
        if m := _ISO_REGEX.match(s):
            dt_str = m.group(1).replace("T", " ")
            dt = dateutil_parser.parse(dt_str)
            rem_msg = (m.group(2) or "").strip()
            return dt.replace(microsecond=0), rem_msg, True

        if m := _DATETIME_1.match(s):
            t_val = _parse_time_str(m.group(2))
            d_val = _parse_date_str(m.group(1), now, time_specified=t_val)
            rem_msg = (m.group(3) or "").strip()
            return datetime.combine(d_val, t_val), rem_msg, True

        if m := _DATETIME_2.match(s):
            t_val = _parse_time_str(m.group(1))
            d_val = _parse_date_str(m.group(2), now, time_specified=t_val)
            rem_msg = (m.group(3) or "").strip()
            return datetime.combine(d_val, t_val), rem_msg, True

        if m := _DATE_ONLY.match(s):
            d_str = m.group(1)
            def_time = time(20, 0) if d_str.lower() == "tonight" else time(12, 0)
            d_val = _parse_date_str(d_str, now, time_specified=def_time)
            rem_msg = (m.group(2) or "").strip()
            return datetime.combine(d_val, def_time), rem_msg, True

        if m := _TIME_ONLY.match(s):
            t_val = _parse_time_str(m.group(1))
            rem_msg = (m.group(2) or "").strip()
            return datetime.combine(now.date(), t_val), rem_msg, True
    except (ValueError, OverflowError):
        pass

    # 3. No date/time specified
    target_dt = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return target_dt, s, False
