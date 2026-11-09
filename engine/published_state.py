import json
from pathlib import Path


class PublishedState:
    """Best-effort cross-run duplicate guard, persisted by GitHub Actions cache."""

    def __init__(self, path="state/published.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(self.data, dict):
                self.data = {}
        except (OSError, json.JSONDecodeError):
            self.data = {}

    def next_poster_style(self):
        """Rotate the three approved editorial looks across runs."""
        styles = ("light_editorial", "dark_editorial", "white_red")
        meta = self.data.setdefault("_meta", {})
        index = int(meta.get("poster_style_index", 0))
        style = styles[index % len(styles)]
        meta["poster_style_index"] = index + 1
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return style

    def is_published(self, source_url, platform):
        return bool(self.data.get(source_url, {}).get(platform))

    def mark_published(self, source_url, platform, receipt):
        record = self.data.setdefault(source_url, {})
        record[platform] = {
            "confirmed": True,
            "receipt": str(receipt),
        }
        # Bound the cache file so it cannot grow indefinitely.
        if len(self.data) > 500:
            self.data = dict(list(self.data.items())[-500:])
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
