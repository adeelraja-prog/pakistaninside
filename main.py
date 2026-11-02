
import os
import sys

from engine.scout import ScoutAgent
from engine.editor import (
    EditorAgent,
    GeminiQuotaExceededError,
    GeminiAPIError,
    GeminiOutputError,
)
from engine.designer import DesignerAgent
from engine.strategist import StrategistAgent


def create_source_fallback(story):
    """Create a neutral, source-attributed graphic without inventing news."""

    headline = str(story.get("title", "")).strip()
    summary = str(story.get("summary", "")).strip()
    source = str(story.get("source", "Original source")).strip()
    link = str(story.get("link", "")).strip()

    if not headline or not link:
        raise ValueError("Story has no usable headline or source link.")

    return {
        "headline": headline,
        "urdu_text": "اصل خبر اور مکمل تفصیلات کے لیے ماخذ کا لنک ملاحظہ کریں۔",
        "body": summary or headline,
        "source": source,
        "link": link,
    }


def run_newsroom():

    print("==================================================")
    print("PAKISTAN INSIDE - COMMAND & CONTROL ENGINE")
    print("==================================================")

    try:
        scout = ScoutAgent()
        editor = EditorAgent()
        designer = DesignerAgent()
        strategist = StrategistAgent()

        # AGENT 1: SCOUT
        raw_stories = scout.run()

        if not raw_stories:
            print("[NEWSROOM] No stories found.")
            return False

        print(f"[SCOUT] Collected {len(raw_stories)} stories.")
        print("[NEWSROOM] Testing the first collected story.")

        story = raw_stories[0]

        # AGENT 2: EDITOR
        try:
            edited_data = editor.process_story(story)
            print("[EDITOR] Gemini successfully prepared the story.")

        except GeminiQuotaExceededError as exc:
            print("[EDITOR] Gemini quota exhausted.")
            print("[EDITOR] Using source-based fallback.")
            print(str(exc))

            edited_data = create_source_fallback(story)

        required_fields = ["headline", "urdu_text", "body"]

        for field in required_fields:
            if not edited_data.get(field):
                raise ValueError(
                    f"Editorial output is missing required field: {field}"
                )

        # AGENT 3: DESIGNER
        card_path = designer.generate_card(edited_data)

        if not card_path or not os.path.isfile(card_path):
            raise RuntimeError("Designer did not generate a valid image.")

        print(f"[DESIGNER] Poster successfully generated: {card_path}")

        # SAFE TEST: Do not publish until duplicate protection is implemented.
        publish_enabled = os.getenv(
            "PUBLISH_TO_FACEBOOK", "false"
        ).lower() in ("true", "1", "yes")

        if not publish_enabled:
            print("[SAFE TEST] Facebook publishing is disabled.")
            print("[SAFE TEST] Poster generation test completed.")
            return True

        # AGENT 4: STRATEGIST
        source = str(story.get("source", "Source")).strip()
        link = str(story.get("link", "")).strip()

        caption = (
            f"{edited_data['headline']}\n\n"
            f"{edited_data['urdu_text']}\n\n"
            f"Source: {source}\n"
            f"{link}\n\n"
            "#PakistanInside #Pakistan"
        )

        result = strategist.publish_to_facebook(card_path, caption)

        if not isinstance(result, dict):
            raise RuntimeError("Facebook returned an unexpected response.")

        if result.get("dry_run"):
            print("[PUBLISHING] Dry run only.")
            return False

        if result.get("error"):
            print(f"[PUBLISHING FAILED] {result['error']}")
            return False

        post_id = result.get("post_id") or result.get("id")

        if not post_id:
            raise RuntimeError(
                f"Facebook did not confirm a post ID: {result}"
            )

        print(f"[PUBLISHING SUCCESS] Facebook Post ID: {post_id}")
        return True

    except GeminiQuotaExceededError as exc:
        print(f"[GEMINI QUOTA ERROR] {exc}")
        return False

    except GeminiAPIError as exc:
        print(f"[GEMINI ERROR] {exc}")
        return False

    except GeminiOutputError as exc:
        print(f"[EDITORIAL OUTPUT ERROR] {exc}")
        return False

    except Exception as exc:
        print(f"[NEWSROOM ERROR] {type(exc).__name__}: {exc}")
        return False


if __name__ == "__main__":
    success = run_newsroom()

    if not success:
        sys.exit(1)
