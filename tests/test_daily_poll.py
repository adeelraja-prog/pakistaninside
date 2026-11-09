import unittest
from datetime import datetime, timezone

from engine.daily_poll import POLLS, build_daily_poll


class DailyPollTests(unittest.TestCase):
    def test_poll_has_question_and_four_options(self):
        poll = build_daily_poll(datetime(2026, 11, 9, 13, 0, tzinfo=timezone.utc))
        self.assertTrue(poll["question"])
        self.assertIn("Adeel Raja", poll["message"])
        self.assertIn("https://www.youtube.com/@adeelrajaviews", poll["message"])
        self.assertEqual(poll["message"].count("\n1."), 1)
        self.assertEqual(poll["message"].count("\n4."), 1)

    def test_rotation_changes_by_day(self):
        first = build_daily_poll(datetime(2026, 11, 9, 13, 0, tzinfo=timezone.utc))
        second = build_daily_poll(datetime(2026, 11, 10, 13, 0, tzinfo=timezone.utc))
        self.assertNotEqual(first["question"], second["question"])

    def test_poll_library_has_multiple_topics(self):
        categories = {item[0] for item in POLLS}
        self.assertTrue({"POLITICS", "COURTS", "PUBLIC", "WORLD", "ENTERTAINMENT"}.issubset(categories))


if __name__ == "__main__":
    unittest.main()
