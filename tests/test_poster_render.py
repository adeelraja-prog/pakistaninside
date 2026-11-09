import tempfile
import unittest
from pathlib import Path

from PIL import Image

from engine.designer import DesignerAgent


class PosterRenderTests(unittest.TestCase):
    def test_international_poster_renders_full_width_editorial_image(self):
        with tempfile.TemporaryDirectory() as directory:
            designer = DesignerAgent()
            designer.OUTPUT_DIR = directory
            designer._download_image = lambda _url: Image.new("RGB", (1600, 1000), (20, 120, 180))
            result = designer.generate_card({
                "headline": "عدالت نے اہم حکم جاری کر دیا",
                "urdu_text": "عدالت نے مقدمے کی سماعت کے دوران اہم حکم جاری کیا ہے۔",
                "body": "عدالت نے مقدمے کی سماعت کے دوران اہم حکم جاری کیا ہے۔",
                "english_headline": "Court issues an important order",
                "english_text": "The court issued an important order during the hearing.",
                "language": "ur",
                "tag": "COURT",
                "source_name": "Test News Source",
                "source_url": "https://example.com/story",
                "image_url": "https://images.example.com/story.jpg",
                "published_at": "2026-11-09T10:00:00+00:00",
                "urgency": "POTENTIAL_BREAKING",
            })
            output = Path(result)
            self.assertTrue(output.is_file())
            with Image.open(output) as poster:
                self.assertEqual(poster.size, (1080, 1350))
                # The hero image occupies the upper photograph region, not a blank panel.
                pixel = poster.getpixel((500, 300))
                self.assertGreater(pixel[2], pixel[0] + 80)
                self.assertGreater(pixel[2], pixel[1])


if __name__ == "__main__":
    unittest.main()
