import os
import requests

def publish_to_facebook(image_path, caption):
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    
    # Fallback to dry-run mode if tokens are not set
    if not page_id or not access_token:
        print("🔥 [Agent 4: Strategist] FB Tokens missing. Running in dry-run mode.")
        return {"dry_run": True}
    
    # Correct Page Photos API endpoint (avoids deprecated user-level publish_actions)
    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    
    payload = {
        'caption': caption,
        'access_token': access_token
    }
    
    try:
        with open(image_path, 'rb') as img_file:
            files = {'source': img_file}
            response = requests.post(url, data=payload, files=files)
            res_json = response.json()
            print(f"🔥 [Agent 4: Strategist] Facebook Response: {res_json}")
            return res_json
    except Exception as e:
        print(f"🔥 [Agent 4: Strategist Error] Facebook post failed: {e}")
        return {"error": str(e)}
