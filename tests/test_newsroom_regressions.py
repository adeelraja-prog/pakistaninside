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
            "title": "BREAKING: Supreme Court issues court order on Imran Khan bail",
            "summary": "Latest development",
            "published_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        }
        fresh = {
            "title": "BREAKING: Supreme Court issues court order on Imran Khan bail",
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

    def test_low_value_routine_announcement_is_excluded(self):
        scout = ScoutAgent.__new__(ScoutAgent)
        story = {
            "title": "Minister chairs routine delegation meeting",
            "summary": "Officials reviewed progress and congratulated the team",
            "published_at": "",
        }
        ranked = scout.score_story(story)
        self.assertFalse(ranked["eligible"])
        self.assertEqual(ranked["exclude_reason"], "ROUTINE_LOW_PUBLIC_INTEREST")

    def test_candidate_selection_preserves_core_public_interest_lanes(self):
        scout = ScoutAgent.__new__(ScoutAgent)
        stories = [
            {"title": "Politics", "tag": "POLITICS", "topics": ["POLITICS"], "impact_score": 90, "eligible": True},
            {"title": "Courts", "tag": "COURT", "topics": ["COURT"], "impact_score": 70, "eligible": True},
            {"title": "Bills", "tag": "PUBLIC_INTEREST", "topics": ["PUBLIC_INTEREST"], "impact_score": 60, "eligible": True},
            {"title": "General", "tag": "GENERAL", "topics": ["GENERAL"], "impact_score": 95, "eligible": True},
        ]
        selected = scout.select_editorial_candidates(stories, limit=3)
        self.assertEqual({item["tag"] for item in selected}, {"POLITICS", "COURT", "PUBLIC_INTEREST"})

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
            "english_headline": "Court issues important order",
            "english_text": "The court issued an important order.",
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
                "english_headline": "English headline",
                "english_text": "English-only body",
            })


if __name__ == "__main__":
    unittest.main()
