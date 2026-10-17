import unittest
from datetime import datetime, timedelta

from utils.schedule_parser import parse_schedule


class TestScheduleParser(unittest.TestCase):
    def setUp(self):
        # Saturday, Oct 17, 2026 at 10:00:00
        self.now = datetime(2026, 10, 17, 10, 0, 0)

    def test_legacy_format_date_and_time(self):
        target, msg, specified = parse_schedule("2026-10-18 14:00 will it rain tomorrow?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))
        self.assertEqual(msg, "will it rain tomorrow?")

    def test_legacy_format_date_only(self):
        # When only date is provided, defaults to 12:00 noon
        target, msg, specified = parse_schedule("2026-10-18 will it rain tomorrow?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 12, 0, 0))
        self.assertEqual(msg, "will it rain tomorrow?")

    def test_legacy_format_time_only(self):
        target, msg, specified = parse_schedule("14:00 will it rain?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 17, 14, 0, 0))
        self.assertEqual(msg, "will it rain?")

    def test_flexible_date_separators_and_formats(self):
        # Slash separators
        target, msg, specified = parse_schedule("2026/10/18 14:00 test slash", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))
        self.assertEqual(msg, "test slash")

        # Single digit month and day
        target, msg, specified = parse_schedule("2026-5-3 09:30 single digit", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 5, 3, 9, 30, 0))
        self.assertEqual(msg, "single digit")

        # Day-first format
        target, msg, specified = parse_schedule("18-10-2026 14:00 day first", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))
        self.assertEqual(msg, "day first")

    def test_iso_format(self):
        target, msg, specified = parse_schedule("2026-10-18T14:00:30 iso test", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 30))
        self.assertEqual(msg, "iso test")

    def test_relative_duration_hours_minutes(self):
        target, msg, specified = parse_schedule("117h 32m will it rain?", self.now)
        self.assertTrue(specified)
        # 117 hours and 32 minutes from 2026-10-17 10:00:00 -> 2026-10-22 07:32:00
        expected = self.now + timedelta(hours=117, minutes=32)
        self.assertEqual(target, expected)
        self.assertEqual(msg, "will it rain?")

    def test_relative_duration_adjacent_units(self):
        target, msg, specified = parse_schedule("117h32m will it rain?", self.now)
        self.assertTrue(specified)
        expected = self.now + timedelta(hours=117, minutes=32)
        self.assertEqual(target, expected)
        self.assertEqual(msg, "will it rain?")

    def test_relative_duration_days_hours(self):
        target, msg, specified = parse_schedule("4 days 2 hours will it rain?", self.now)
        self.assertTrue(specified)
        expected = self.now + timedelta(days=4, hours=2)
        self.assertEqual(target, expected)
        self.assertEqual(msg, "will it rain?")

    def test_relative_duration_with_commas_and_and(self):
        target, msg, specified = parse_schedule(
            "4 days, 2 hours, and 15 minutes will it rain?", self.now
        )
        self.assertTrue(specified)
        expected = self.now + timedelta(days=4, hours=2, minutes=15)
        self.assertEqual(target, expected)
        self.assertEqual(msg, "will it rain?")

    def test_relative_duration_with_in_and_plus(self):
        target1, msg1, spec1 = parse_schedule("in 4 days 2 hours test", self.now)
        self.assertTrue(spec1)
        self.assertEqual(target1, self.now + timedelta(days=4, hours=2))
        self.assertEqual(msg1, "test")

        target2, msg2, spec2 = parse_schedule("+2h test", self.now)
        self.assertTrue(spec2)
        self.assertEqual(target2, self.now + timedelta(hours=2))
        self.assertEqual(msg2, "test")

    def test_relative_duration_articles(self):
        target1, msg1, spec1 = parse_schedule("in an hour check dinner", self.now)
        self.assertTrue(spec1)
        self.assertEqual(target1, self.now + timedelta(hours=1))
        self.assertEqual(msg1, "check dinner")

        target2, msg2, spec2 = parse_schedule("in a day check task", self.now)
        self.assertTrue(spec2)
        self.assertEqual(target2, self.now + timedelta(days=1))
        self.assertEqual(msg2, "check task")

    def test_relative_duration_floats(self):
        target, msg, specified = parse_schedule("1.5 hours meeting", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, self.now + timedelta(hours=1, minutes=30))
        self.assertEqual(msg, "meeting")

    def test_relative_duration_various_units(self):
        t_sec, _, _ = parse_schedule("30s test", self.now)
        self.assertEqual(t_sec, self.now + timedelta(seconds=30))

        t_min, _, _ = parse_schedule("45 mins test", self.now)
        self.assertEqual(t_min, self.now + timedelta(minutes=45))

        t_wk, _, _ = parse_schedule("2 weeks test", self.now)
        self.assertEqual(t_wk, self.now + timedelta(weeks=2))

    def test_natural_language_dates_tomorrow_today_tonight(self):
        # Tomorrow at 2pm
        target, msg, specified = parse_schedule("tomorrow at 2pm will it rain?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))
        self.assertEqual(msg, "will it rain?")

        # Tomorrow without time -> noon
        target, msg, specified = parse_schedule("tomorrow will it rain?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 12, 0, 0))
        self.assertEqual(msg, "will it rain?")

        # Today with time
        target, msg, specified = parse_schedule("today 18:00 will it rain?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 17, 18, 0, 0))
        self.assertEqual(msg, "will it rain?")

        # Tonight without time -> defaults to 20:00
        target, msg, specified = parse_schedule("tonight will it rain?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 17, 20, 0, 0))
        self.assertEqual(msg, "will it rain?")

    def test_natural_language_special_times(self):
        # Noon
        target, msg, specified = parse_schedule("tomorrow at noon will it rain?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 12, 0, 0))

        # Midnight
        target, msg, specified = parse_schedule("tomorrow at midnight test", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 0, 0, 0))

        # 12-hour AM/PM formats
        target, msg, specified = parse_schedule("2:30 PM will it rain?", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 17, 14, 30, 0))

    def test_time_before_date(self):
        target, msg, specified = parse_schedule("14:00 2026-10-18 test", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))
        self.assertEqual(msg, "test")

        target, msg, specified = parse_schedule("2pm tomorrow test", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))
        self.assertEqual(msg, "test")

    def test_month_names(self):
        target, msg, specified = parse_schedule("Oct 18 2026 14:00 test", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))

        target, msg, specified = parse_schedule("18th of October 14:00 test", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))

    def test_weekday(self):
        # Oct 17, 2026 is Saturday. Upcoming Sunday is Oct 18, 2026.
        target, msg, specified = parse_schedule("Sunday 14:00 test", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 18, 14, 0, 0))

        # Upcoming Friday is Oct 23, 2026.
        target, msg, specified = parse_schedule("Friday at 3pm test", self.now)
        self.assertTrue(specified)
        self.assertEqual(target, datetime(2026, 10, 23, 15, 0, 0))

    def test_no_date_or_time_specified(self):
        cases = [
            "will it rain tomorrow?",
            "2 cats are cute",
            "may the force be with you",
            "hello world",
        ]
        for c in cases:
            target, msg, specified = parse_schedule(c, self.now)
            self.assertFalse(specified, f"Expected specified=False for {c!r}")
            self.assertEqual(target, self.now + timedelta(minutes=1))
            self.assertEqual(msg, c)

    def test_empty_remainder_message(self):
        target, msg, specified = parse_schedule("117h 32m", self.now)
        self.assertTrue(specified)
        self.assertEqual(msg, "")

        target, msg, specified = parse_schedule("2026-10-18 14:00", self.now)
        self.assertTrue(specified)
        self.assertEqual(msg, "")


if __name__ == "__main__":
    unittest.main()
