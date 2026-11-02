import os
import requests

class StrategistAgent:
    def __init__(self):
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")
        self.access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")

    def run(self, image_path, caption):
        """Standard execution method called by main.py"""
        return self.publish_to_facebook(image_path, caption)

    def publish_to_facebook(self, image_path, caption):
        if not self.page_id or not self.access_token:
            print("🔥 [Agent 4: Strategist] FB Tokens missing. Running in dry-run mode.")
            return {"dry_run": True}
        
        # Facebook Graph API Photos Endpoint
        url = f"https://graph.facebook.com/v19.0/{self.page_id}/photos"
        
        payload = {
            'caption': caption,
            'access_token': self.access_token
        }
        
        try:
            with open(image_path, 'rb') as img_file:
                files = {'source': img_file}
                response = requests.post(url, data=payload, files=files)
                res_json = response.json()
                
                if "id" in res_json or "post_id" in res_json:
                    print(f"🎉 [Agent 4: Strategist] LIVE POST SUCCESSFUL! Post ID: {res_json}")
                else:
                    print(f"❌ [Agent 4: Strategist Error] FB Returned Error Response: {res_json}")
                    
                return res_json
        except Exception as e:
            print(f"💥 [Agent 4: Strategist Exception] Failed: {e}")
            return {"error": str(e)}

    @classmethod
    def publish(cls, image_path, caption):
        """Compatibility wrapper for static calls"""
        agent = cls()
        return agent.publish_to_facebook(image_path, caption)
