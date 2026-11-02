import os
import time
import google.generativeai as genai

def generate_news_content(stories):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing from environment variables.")
    
    genai.configure(api_key=api_key)
    
    # Using the updated stable model with retry logic for 503 spikes
    model = genai.GenerativeModel('gemini-3.8-flash')
    
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
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "503" in str(e) and attempt < max_retries - 1:
                time.sleep(3)
                continue
            print(f"[Editor Error] Gemini API call failed: {e}")
            raise e
