import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class RequestBudgetExceeded(RuntimeError):
    pass


class DailyRequestBudget:
    """Persist a hard cap on Gemini API calls in Pakistan local time."""

    def __init__(self, path="state/gemini_usage.json", limit=None, now=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limit = int(limit or os.getenv("GEMINI_DAILY_REQUEST_LIMIT", "16"))
        self.day = (now or datetime.now(ZoneInfo("America/Los_Angeles"))).astimezone(
            ZoneInfo("America/Los_Angeles")
        ).date().isoformat()
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self.data, dict) or self.data.get("day") != self.day:
                self.data = {"day": self.day, "requests": 0}
        except (OSError, json.JSONDecodeError):
            self.data = {"day": self.day, "requests": 0}

    def consume(self):
        used = int(self.data.get("requests", 0))
        if used >= self.limit:
            raise RequestBudgetExceeded(
                f"Daily free-tier Gemini request cap reached ({self.limit} requests, America/Los_Angeles day)."
            )
        self.data["requests"] = used + 1
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.data["requests"]
