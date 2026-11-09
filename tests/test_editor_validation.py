import unittest

from engine.editor import EditorAgent, GeminiOutputError


class EditorValidationTests(unittest.TestCase):
    def setUp(self):
        # Validation is deterministic and does not need a live Gemini client.
        self.editor = EditorAgent.__new__(EditorAgent)

    def test_accepts_urdu_story(self):
        item = {
            "tag": "POLITICS",
            "headline": "عمران خان سے ملاقات کے معاملے پر نئی پیش رفت",
            "urdu_text": "عدالت میں اس معاملے پر اہم سماعت ہوئی اور فریقین نے اپنے دلائل پیش کیے۔",
            "body": "عدالت میں اہم پیش رفت",
            "english_headline": "New development in Imran Khan meeting case",
            "english_text": "A court hearing took place and both sides presented arguments.",
            "source_name": "Test source",
        }
        result = self.editor._validate_item(item)
        self.assertEqual(result["language"], "ur")
        self.assertEqual(result["tag"], "POLITICS")
        self.assertTrue(result["urdu_text"])

    def test_rejects_english_only_fallback(self):
        item = {
            "tag": "GENERAL",
            "headline": "Major political development",
            "urdu_text": "",
            "body": "An English fallback card",
        }
        with self.assertRaises(GeminiOutputError):
            self.editor._validate_item(item)

    def test_rejects_missing_headline(self):
        item = {"urdu_text": "یہ ایک اردو خبر کا متن ہے جس میں کافی تفصیل موجود ہے۔"}
        with self.assertRaises(GeminiOutputError):
            self.editor._validate_item(item)

    def test_normalises_unknown_category(self):
        item = {
            "tag": "UNKNOWN",
            "headline": "عدالت کا اہم فیصلہ سامنے آ گیا",
            "urdu_text": "عدالت نے مقدمے کی سماعت کے دوران اہم حکم جاری کیا ہے۔",
            "english_headline": "Court issues an important order",
            "english_text": "The court issued an order during the hearing.",
        }
        result = self.editor._validate_item(item)
        self.assertEqual(result["tag"], "GENERAL")


if __name__ == "__main__":
    unittest.main()
