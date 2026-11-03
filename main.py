import os
import sys
from engine.scout import ScoutAgent
from engine.editor import EditorAgent, GeminiQuotaExceededError
from engine.designer import DesignerAgent
from engine.strategist import StrategistAgent

def main():
    print("=== Pakistan Inside Newsroom ===")
    scout = ScoutAgent()
    stories = scout.run()
    if not stories:
        print("No stories found.")
        return

    editor = EditorAgent()
    designer = DesignerAgent()
    strategist = StrategistAgent()

    language = "ur"
    processed = None
    try:
        processed = editor.process_stories(stories[:6], language="ur")
    except GeminiQuotaExceededError:
        print("[FALLBACK] Quota exhausted. Using simple English cards (no Gemini).")
        processed = editor.fallback_stories(stories)
    except Exception as e:
        print(f"[Editor failed] {e}")
        print("[FALLBACK] Using simple English cards (no Gemini).")
        processed = editor.fallback_stories(stories)

    if not processed:
        print("No content generated this run.")
        return

    for item in processed[:3]:  # Limit posts per run
        try:
            poster_path = designer.generate_card(item)
            caption = f"{item['headline']}\n\n{item.get('body', '')}\n\n#PakistanInside #AdeelRaja"
            if os.getenv("PUBLISH_TO_FACEBOOK", "false").lower() == "true":
                result = strategist.publish_to_facebook(poster_path, caption)
                print(f"[PUBLISH] {result}")
            else:
                print(f"[DRY] Poster ready: {poster_path}")
        except Exception as e:
            print(f"[ERROR] Story failed: {e}")

if __name__ == "__main__":
    main()
