import unittest

from engine.designer import DesignerAgent
from engine.scout import ScoutAgent
from engine.editor import EditorAgent, GeminiOutputError


class NewsroomRegressionTests(unittest.TestCase):
    def test_scout_prioritises_court_and_public_interest_topics(self):
        scout = ScoutAgent.__new__(ScoutAgent)
        story = {
            "title": "Supreme Court hearing on electricity prices",
            "summary": "Court examines public impact of electricity bills",
            "published_at": "",
        }
        ranked = scout.score_story(story)
        self.assertIn("COURT", ranked["topics"])
        self.assertIn("PUBLIC_INTEREST", ranked["topics"])
        self.assertGreater(ranked["impact_score"], 0)

    def test_routine_press_release_is_penalised(self):
        scout = ScoutAgent.__new__(ScoutAgent)
        story = {
            "title": "Ministry issues routine press release after delegation meeting",
            "summary": "Official announcement",
            "published_at": "",
        }
        ranked = scout.score_story(story)
        self.assertTrue(ranked["press_release_penalty"])
        self.assertLess(ranked["impact_score"], 0)

    def test_poster_refuses_missing_image(self):
        designer = DesignerAgent.__new__(DesignerAgent)
        with self.assertRaises(ValueError):
            designer._download_image("")

    def test_editor_requires_exact_source_url_field(self):
        editor = EditorAgent.__new__(EditorAgent)
        item = {
            "tag": "COURT",
            "headline": "عدالت میں اہم پیش رفت سامنے آ گئی",
            "urdu_text": "عدالت نے مقدمے کی سماعت کے دوران اہم حکم جاری کیا ہے۔",
            "source_url": "https://example.com/story",
        }
        result = editor._validate_item(item)
        self.assertEqual(result["source_url"], "https://example.com/story")

    def test_editor_rejects_english_fallback(self):
        editor = EditorAgent.__new__(EditorAgent)
        with self.assertRaises(GeminiOutputError):
            editor._validate_item({
                "headline": "English headline",
                "urdu_text": "English-only body",
            })


if __name__ == "__main__":
    unittest.main()
