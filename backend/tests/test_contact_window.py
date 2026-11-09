from datetime import datetime, timezone, timedelta
from app.compliance import allowed_contact_time, to_ist, reminder_language_allowed

def test_contact_window_boundaries():
    assert allowed_contact_time(datetime(2026, 11, 9, 8, 0))
    assert allowed_contact_time(datetime(2026, 11, 9, 19, 0))
    assert not allowed_contact_time(datetime(2026, 11, 9, 7, 59))
    assert not allowed_contact_time(datetime(2026, 11, 9, 19, 1))

def test_aware_timestamp_is_converted_to_ist():
    # 02:30 UTC is 08:00 IST.
    value = datetime(2026, 11, 9, 2, 30, tzinfo=timezone.utc)
    assert allowed_contact_time(value)
    assert to_ist(value).hour == 8


def test_reminder_filter_allows_respectful_template():
    assert reminder_language_allowed("Please contact your assigned officer if you need assistance.")

def test_reminder_filter_blocks_threatening_language():
    assert not reminder_language_allowed("We will threaten and harass you.")
