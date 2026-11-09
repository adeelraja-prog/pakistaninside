import os
import sys

from engine.scout import ScoutAgent
from engine.editor import EditorAgent, GeminiQuotaExceededError
from engine.designer import DesignerAgent
from engine.video import VideoAgent
from engine.strategist import StrategistAgent


def main():
    print("=== Adeel Raja Newsroom — Recovery Mode ===")
    scout = ScoutAgent()
    stories = scout.run()
    if not stories:
        print("[SCOUT] No stories found; nothing will be published.")
        return 0

    image_candidates = [story for story in stories if story.get("image_url")]
    if not image_candidates:
        print("[SAFE STOP] No stories with retrievable editorial images were found.")
        return 2

    try:
        editor = EditorAgent()
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
    video_agent = VideoAgent()
    strategist = StrategistAgent()
    publish_facebook = os.getenv("PUBLISH_TO_FACEBOOK", "false").lower() == "true"
    publish_youtube = os.getenv("PUBLISH_TO_YOUTUBE", "false").lower() == "true"
    youtube = None

    if publish_youtube:
        from engine.youtube import YouTubePublisher
        youtube = YouTubePublisher()

    failures = 0
    for index, item in enumerate(processed[:3], start=1):
        try:
            if item.get("language") != "ur" or not item.get("urdu_text"):
                raise ValueError("Story failed Urdu-first publication gate")
            if not item.get("image_url") or not item.get("source_url"):
                raise ValueError("Story is missing a source URL or editorial image")

            poster_path = designer.generate_card(item)
            video_path = video_agent.generate_reel(item)
            caption = (
                f"{item['headline']}\n\n{item.get('body', '')}"
                f"\n\nSource: {item.get('source_name', 'News source')}"
                f"\n{item['source_url']}"
                "\n\nAdeel Raja\n#AdeelRaja"
            )

            print(f"[OUTPUT {index}] Poster: {poster_path}")
            print(f"[OUTPUT {index}] Reel: {video_path}")

            if publish_facebook:
                result = strategist.publish_to_facebook(poster_path, caption)
                if not isinstance(result, dict) or result.get("error"):
                    raise RuntimeError(f"Facebook publishing not confirmed: {result}")
                print(f"[FACEBOOK {index}] Confirmed receipt: {result}")

            if publish_youtube:
                result = youtube.upload_short(
                    video_path,
                    item["headline"],
                    caption,
                    tags=["AdeelRaja", "PakistanNews", "PTI", "Pakistan", "Shorts"],
                )
                print(f"[YOUTUBE {index}] Confirmed receipt: {result}")

        except Exception as exc:
            failures += 1
            print(f"[STORY FAILED {index}] {type(exc).__name__}: {exc}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
