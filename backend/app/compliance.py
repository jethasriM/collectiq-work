"""Time-window helpers for the India Standard Time contact policy."""
from datetime import datetime, time
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def to_ist(value: datetime) -> datetime:
    """Treat naive timestamps as IST; convert aware timestamps to IST."""
    return value.replace(tzinfo=IST) if value.tzinfo is None else value.astimezone(IST)


def allowed_contact_time(value: datetime) -> bool:
    local = to_ist(value)
    local_time = local.time().replace(tzinfo=None)
    return time(8, 0) <= local_time <= time(19, 0)

BLOCKED_REMINDER_TERMS = ("threaten", "harass", "abuse", "धमकी", "गाली", "जबरदस्ती")

def reminder_language_allowed(text: str) -> bool:
    normalized = (text or "").casefold()
    return not any(term.casefold() in normalized for term in BLOCKED_REMINDER_TERMS)
