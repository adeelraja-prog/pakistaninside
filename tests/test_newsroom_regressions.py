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

    def test_breaking_label_requires_fresh_timestamp(self):
        scout = ScoutAgent.__new__(ScoutAgent)
        from datetime import datetime, timezone, timedelta
        stale = {
            "title": "BREAKING: Supreme Court hearing",
            "summary": "Latest development",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        }
        fresh = {
            "title": "BREAKING: Supreme Court hearing",
            "summary": "Latest development",
            "published_at": (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat(),
        }
        self.assertEqual(scout.score_story(stale)["urgency"], "NORMAL")
        self.assertEqual(scout.score_story(fresh)["urgency"], "POTENTIAL_BREAKING")

    def test_related_headlines_cluster_across_sources(self):
        scout = ScoutAgent.__new__(ScoutAgent)
        stories = [
            {"title": "Supreme Court suspends new tax measure", "source": "Source A", "impact_score": 20, "image_url": "https://example.com/a.jpg", "link": "https://example.com/a"},
            {"title": "Supreme Court suspends the new tax measure", "source": "Source B", "impact_score": 18, "image_url": "", "link": "https://example.com/b"},
        ]
        clustered = scout.cluster_related(stories)
        self.assertEqual(len(clustered), 1)
        self.assertEqual(clustered[0]["source_count"], 2)

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
