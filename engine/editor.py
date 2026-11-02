import os
import time
import google.generativeai as genai

class EditorAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing from environment variables.")
        
        genai.configure(api_key=self.api_key)
        # Using the stable model endpoint with 503 retry support
        self.model = genai.GenerativeModel('gemini-3.8-flash')

    def run(self, stories):
        """Standard execution method called by main.py"""
        return self.generate_news_content(stories)

    def generate_news_content(self, stories):
        prompt = f"""
        You are the Senior Editor for 'Pakistan Inside'. 
        Analyze the following collected news stories, pick the most impactful one, 
        and write a compelling, high-engagement Urdu headline and caption for social media.
        
        Stories:
        {stories}
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                if "503" in str(e) and attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                print(f"[Editor Error] Gemini API call failed: {e}")
                raise e

    @classmethod
    def generate(cls, stories):
        """Compatibility wrapper for static calls"""
        agent = cls()
        return agent.generate_news_content(stories)
