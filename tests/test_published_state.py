import tempfile
import unittest
from pathlib import Path

from engine.published_state import PublishedState


class PublishedStateTests(unittest.TestCase):
    def test_platform_receipts_are_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            state = PublishedState(str(Path(directory) / "published.json"))
            url = "https://example.com/story"
            self.assertFalse(state.is_published(url, "facebook"))
            state.mark_published(url, "facebook", "fb-123")
            self.assertTrue(state.is_published(url, "facebook"))
            self.assertFalse(state.is_published(url, "youtube"))

    def test_poster_styles_rotate_and_persist(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "published.json")
            first = PublishedState(path)
            styles = [first.next_poster_style() for _ in range(3)]
            self.assertEqual(styles, ["light_editorial", "dark_editorial", "white_red"])
            second = PublishedState(path)
            self.assertEqual(second.next_poster_style(), "light_editorial")

    def test_state_survives_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "published.json")
            first = PublishedState(path)
            first.mark_published("https://example.com/a", "youtube", "yt-123")
            second = PublishedState(path)
            self.assertTrue(second.is_published("https://example.com/a", "youtube"))


if __name__ == "__main__":
    unittest.main()
