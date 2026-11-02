
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


def run_newsroom():

    print("==================================================")
    print("PAKISTAN INSIDE - COMMAND & CONTROL ENGINE")
    print("==================================================")

    try:
        # Initialize the four newsroom agents.
        scout = ScoutAgent()
        editor = EditorAgent()
        designer = DesignerAgent()
        strategist = StrategistAgent()

        # AGENT 1: SCOUT
        raw_stories = scout.run()

        if not raw_stories:
            print("[NEWSROOM] No new stories found. Nothing to publish.")
            return False

        print(f"[NEWSROOM] Processing the top story from {len(raw_stories)} collected stories.")

        # AGENT 2: EDITOR
        edited_data = editor.process_story(raw_stories[0])

        required_fields = ["headline", "urdu_text", "body"]

        for field in required_fields:
            if not edited_data.get(field):
                raise ValueError(
                    f"Editorial output is missing required field: {field}"
                )

        print("[EDITOR] News content successfully prepared.")

        # AGENT 3: DESIGNER
        card_path = designer.generate_card(edited_data)

        if not card_path or not os.path.isfile(card_path):
            raise RuntimeError(
                "Designer did not generate a valid image file."
            )

        print(f"[DESIGNER] Graphic generated: {card_path}")

        # Prepare Facebook caption.
        caption = (
            f"{edited_data['headline']}\n\n"
            f"{edited_data['urdu_text']}\n\n"
            "#PakistanInside #BreakingNews #Pakistan"
        )

        # AGENT 4: STRATEGIST
        result = strategist.publish_to_facebook(card_path, caption)

        if not isinstance(result, dict):
            raise RuntimeError(
                "Facebook returned an unexpected response."
            )

        if result.get("dry_run"):
            print("[PUBLISHING] Dry run only. No Facebook post was published.")
            return False

        if result.get("error"):
            print(f"[PUBLISHING FAILED] {result['error']}")
            return False

        post_id = result.get("post_id") or result.get("id")

        if not post_id:
            print(f"[PUBLISHING FAILED] Facebook did not confirm a post ID: {result}")
            return False

        print(f"[PUBLISHING SUCCESS] Facebook Post ID: {post_id}")

        print("==================================================")
        print("NEWSROOM EXECUTION COMPLETED SUCCESSFULLY")
        print("==================================================")

        return True

    except GeminiQuotaExceededError as exc:
        print("==================================================")
        print("[NEWSROOM PAUSED] GEMINI FREE-TIER QUOTA EXHAUSTED")
        print(str(exc))
        print("No paid API fallback will be used.")
        print("==================================================")
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
