import os
import time
import json
import google.generativeai as genai

class EditorAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment variables.")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-3.8-flash')

    def run(self, stories):
        return self.process_story(stories)

    def process_story(self, stories):
        prompt = f"""
        You are the Senior Editor for 'Pakistan Inside'. 
        Analyze the following news stories and select the single most impactful breaking story.
        
        Respond STRICTLY with a valid JSON object only (no markdown, no backticks, no text outside JSON) with these exact keys:
        {{
            "tag": "BREAKING NEWS",
            "headline": "Short punchy Urdu headline",
            "urdu_text": "Detailed Urdu summary paragraph for social media post body",
            "body": "Short Urdu description text for the graphical image card"
        }}

        Stories:
        {stories}
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                cleaned_text = response.text.strip()
                
                # Clean Markdown wrappers if present
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text.split("```")[1]
                    if cleaned_text.startswith("json"):
                        cleaned_text = cleaned_text[4:]
                cleaned_text = cleaned_text.strip()
                
                parsed_json = json.loads(cleaned_text)
                
                # Ensure fallback for urdu_text if missing
                if "urdu_text" not in parsed_json:
                    parsed_json["urdu_text"] = parsed_json.get("body", "")
                if "body" not in parsed_json:
                    parsed_json["body"] = parsed_json.get("urdu_text", "")
                    
                return parsed_json
            except json.JSONDecodeError:
                text_content = response.text.strip()
                return {
                    "tag": "PAKISTAN INSIDE",
                    "headline": "پاکستان کی اہم خبر",
                    "urdu_text": text_content,
                    "body": text_content
                }
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                print(f"[Editor Error] Gemini API call failed: {e}")
                raise e

    @classmethod
    def generate(cls, stories):
        agent = cls()
        return agent.process_story(stories)
