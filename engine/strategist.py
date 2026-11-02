import os
import facebook

class StrategistAgent:
    def __init__(self):
        self.fb_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        self.fb_page_id = os.getenv("FACEBOOK_PAGE_ID")

    def publish_to_facebook(self, image_path, caption):
        if not self.fb_token or not self.fb_page_id:
            print("🔥 [Agent 4: Strategist] FB Tokens missing. Running in dry-run mode.")
            return False

        try:
            graph = facebook.GraphAPI(access_token=self.fb_token)
            with open(image_path, 'rb') as img:
                graph.put_photo(image=img, message=caption, album_path=f"{self.fb_page_id}/photos")
            print("🔥 [Agent 4: Strategist] Posted to Pakistan Inside Facebook Page!")
            return True
        except Exception as e:
            print(f"🔥 [Agent 4: Strategist Error] Facebook post failed: {e}")
            return False
