import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from engine.usage_budget import DailyRequestBudget, RequestBudgetExceeded


class DailyRequestBudgetTests(unittest.TestCase):
    def test_budget_blocks_requests_after_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            budget = DailyRequestBudget(
                path=str(Path(directory) / "usage.json"),
                limit=2,
                now=datetime(2026, 11, 9, 10, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            )
            self.assertEqual(budget.consume(), 1)
            self.assertEqual(budget.consume(), 2)
            with self.assertRaises(RequestBudgetExceeded):
                budget.consume()

    def test_budget_resets_on_next_pakistan_day(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "usage.json")
            first = DailyRequestBudget(
                path=path,
                limit=1,
                now=datetime(2026, 11, 9, 23, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            )
            first.consume()
            second = DailyRequestBudget(
                path=path,
                limit=1,
                now=datetime(2026, 11, 10, 1, 0, tzinfo=ZoneInfo("America/Los_Angeles")),
            )
            self.assertEqual(second.consume(), 1)


if __name__ == "__main__":
    unittest.main()
