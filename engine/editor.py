import json
import os
import re
import time
from google import genai
from google.genai import types

class GeminiQuotaExceededError(Exception):
    pass

class GeminiAPIError(Exception):
    pass

class GeminiOutputError(Exception):
    pass

class EditorAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY missing")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    def process_stories(self, stories, language="ur"):
        if not stories:
            raise ValueError("No stories provided")

        prompt = self._build_prompt(stories, language)

        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.4,
                    ),
                )
                text = response.text.strip()
                if not text:
                    raise GeminiOutputError("Empty response")

                # Strip fences if present
                text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE)
                data = json.loads(text)

                if isinstance(data, dict):
                    data = [data]
                if not isinstance(data, list):
                    raise GeminiOutputError("Expected list of stories")

                results = []
                for item in data:
                    results.append(self._validate_item(item, language))
                return results

            except Exception as e:
                err = str(e).lower()
                if "free_tier" in err or "quota" in err or "resource_exhausted" in err:
                    raise GeminiQuotaExceededError("Quota exhausted")
                if attempt == 2:
                    raise GeminiAPIError(str(e))
                time.sleep(15 * (attempt + 1))

        raise GeminiAPIError("Failed after retries")

    def _build_prompt(self, stories, language):
        stories_json = json.dumps(stories, ensure_ascii=False, indent=2)

        if language == "ur":
            lang_instruction = """
Write natural, professional Urdu (Nastaliq style).
Headline must be catchy, impactful, and tempting (masala) while remaining 100% factual.
Focus on the most interesting angle: public impact, numbers, court orders, petrol/electricity, schemes, etc.
Never invent facts, quotes, or sources.
"""
        else:
            lang_instruction = """
Write clear, professional English.
Headline must be catchy and factual.
"""

        return f"""You are the Senior Editor of Pakistan Inside.
Brand: Pakistan Inside with Adeel Raja
Tagline: THE STORY BEHIND THE STORY

Rules (strict):
- Use ONLY the information provided in the stories.
- Do not invent facts, names, quotes, or sources.
- Do not create anti-army content.
- Prefer high-impact stories (economy, petrol, electricity, court, government schemes, public welfare).
- Make headlines catchy and discussion-worthy (masala) without exaggeration.
- {lang_instruction}

Return a JSON array of objects. Each object must have exactly these keys:
"tag" (category: POLITICS, ECONOMY, COURT, HEALTH, TECH, DEFENSE, GENERAL),
"headline",
"urdu_text" (or "english_text" if English mode),
"body" (short graphic line),
"source_name",
"source_attribution" (e.g. "زرائع کے مطابق" or columnist name)

Stories:
{stories_json}
"""

    def _validate_item(self, item, language):
        if not isinstance(item, dict):
            raise GeminiOutputError("Invalid item")

        headline = item.get("headline", "").strip()
        body = item.get("body", "").strip()
        text_key = "urdu_text" if language == "ur" else "english_text"
        main_text = item.get(text_key, item.get("urdu_text", "")).strip()

        if not headline or not main_text:
            raise GeminiOutputError("Missing headline or text")

        return {
            "tag": item.get("tag", "GENERAL").upper(),
            "headline": headline,
            "urdu_text": main_text if language == "ur" else "",
            "english_text": main_text if language == "en" else "",
            "body": body or main_text[:120],
            "source_name": item.get("source_name", "Source"),
            "source_attribution": item.get("source_attribution", "زرائع کے مطابق"),
            "language": language,
        }
