import os
import time
import json
from google import genai
from google.genai import types

class EditorAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[Editor Warning] GEMINI_API_KEY missing. Using fallback.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def process_story(self, raw_story):
        if not self.client:
            return {
                'headline': raw_story['title'],
                'urdu_text': raw_story['summary'],
                'tag': 'BREAKING NEWS'
            }

        prompt = f"""
        You are the lead editor of Pakistan Inside digital newsroom.
        Analyze this raw news item:
        Title: {raw_story['title']}
        Summary: {raw_story['summary']}

        Tasks:
        1. Rewrite into a high-impact, viral Urdu News Headline (max 10-12 words).
        2. Write a 2-line Urdu context explaining "The Story Behind The Story".
        3. Assign an urgency tag: BREAKING, CONTROVERSY, DEBATE, or URGENT.

        Return ONLY a JSON object matching this structure:
        {{
            "headline": "اردو سرخی",
            "urdu_text": "تفصیل",
            "tag": "TAG"
        }}
        """

        try:
            time.sleep(2)
            response = self.client.models.generate_content(
                model='gemini-1.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"[Editor Error] Gemini API call failed: {e}")
            return {
                'headline': raw_story['title'],
                'urdu_text': raw_story['summary'],
                'tag': 'BREAKING'
            }
