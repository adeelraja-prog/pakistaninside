from engine.scout import ScoutAgent
from engine.editor import EditorAgent
from engine.designer import DesignerAgent
from engine.strategist import StrategistAgent

def run_newsroom():
    print("==================================================")
    print("🏛️ LAUNCHING PAKISTAN INSIDE COMMAND & CONTROL ENGINE")
    print("==================================================")

    scout = ScoutAgent()
    editor = EditorAgent()
    designer = DesignerAgent()
    strategist = StrategistAgent()

    raw_stories = scout.run()
    if not raw_stories:
        print("No new content found. Exiting.")
        return

    top_story = raw_stories[0]
    edited_data = editor.process_story(top_story)
    card_path = designer.generate_card(edited_data)

    caption = f"{edited_data['headline']}\n\n{edited_data['urdu_text']}\n\n#PakistanInside #BreakingNews #Pakistan"
    strategist.publish_to_facebook(card_path, caption)

    print("==================================================")
    print("✅ 24/7 AUTONOMOUS NEWSROOM EXECUTION COMPLETED")
    print("==================================================")

if __name__ == "__main__":
    run_newsroom()
