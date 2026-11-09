import os
import sys

from engine.scout import ScoutAgent
from engine.editor import EditorAgent, GeminiQuotaExceededError
from engine.designer import DesignerAgent
from engine.strategist import StrategistAgent


def main():
    print("=== Adeel Raja Newsroom — Recovery Mode ===")
    scout = ScoutAgent()
    stories = scout.run()
    if not stories:
        print("[SCOUT] No stories found; nothing will be published.")
        return 0

    try:
        editor = EditorAgent()
        # Urdu-first is a hard requirement. Never silently downgrade to English.
        image_candidates = [story for story in stories if story.get("image_url")]
        if not image_candidates:
            print("[SAFE STOP] No stories with retrievable editorial images were found.")
            return 2
        processed = editor.process_stories(image_candidates[:8], language="ur")
    except GeminiQuotaExceededError as exc:
        print(f"[EDITOR BLOCKED] Urdu generation quota exhausted: {exc}")
        print("[SAFE STOP] No English fallback will be published.")
        return 2
    except Exception as exc:
        print(f"[EDITOR BLOCKED] Urdu editorial processing failed: {type(exc).__name__}: {exc}")
        print("[SAFE STOP] No content will be published without passing Urdu validation.")
        return 2

    if not processed:
        print("[SAFE STOP] Editor returned no validated Urdu stories.")
        return 2

    designer = DesignerAgent()
    strategist = StrategistAgent()
    publish = os.getenv("PUBLISH_TO_FACEBOOK", "false").lower() == "true"

    failures = 0
    for index, item in enumerate(processed[:3], start=1):
        try:
            if item.get("language") != "ur" or not item.get("urdu_text"):
                raise ValueError("Story failed Urdu-first publication gate")

            poster_path = designer.generate_card(item)
            caption = (
                f"{item['headline']}\n\n{item.get('body', '')}"
                "\n\nAdeel Raja"
                "\n#AdeelRaja"
            )
            if publish:
                result = strategist.publish_to_facebook(poster_path, caption)
                if not isinstance(result, dict) or result.get("error"):
                    raise RuntimeError(f"Facebook publishing not confirmed: {result}")
                print(f"[PUBLISH {index}] Facebook receipt: {result}")
            else:
                print(f"[DRY {index}] Poster ready: {poster_path}")
        except Exception as exc:
            failures += 1
            print(f"[STORY FAILED {index}] {type(exc).__name__}: {exc}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
