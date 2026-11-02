
import os
import json

from google import genai


class GeminiQuotaExceededError(RuntimeError):
    """Raised when the Gemini free-tier quota has been exhausted."""


class GeminiAPIError(RuntimeError):
    """Raised when Gemini cannot complete a generation request."""


class GeminiOutputError(RuntimeError):
    """Raised when Gemini returns invalid or incomplete editorial output."""


class EditorAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing from GitHub Actions secrets."
            )

        # Keep the existing Gemini model.
        # It can be changed later through the GEMINI_MODEL environment variable.
        self.model_name = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.8-flash"
        )

        self.client = genai.Client(api_key=self.api_key)

    def run(self, stories):
        return self.process_story(stories)

    def process_story(self, stories):

        if not stories:
            raise ValueError("No news story was supplied to the Editor.")

        stories_json = json.dumps(
            stories,
            ensure_ascii=False,
            indent=2,
            default=str
        )

        prompt = f"""
You are the Senior Editor of Pakistan Inside.

Your job is to analyse the supplied news story and prepare
accurate Urdu content for a Pakistani news audience.

IMPORTANT RULES:
1. Use only information supported by the supplied story.
2. Do not invent facts, quotations, names or allegations.
3. Do not exaggerate or present speculation as confirmed news.
4. Write natural, professional Urdu script.
5. Create a concise and compelling Urdu headline.
6. Write a detailed Urdu social media summary.
7. Write a shorter Urdu description suitable for a news graphic.

Return one valid JSON object with exactly these keys:

{{
    "tag": "BREAKING NEWS",
    "headline": "Urdu headline",
    "urdu_text": "Detailed Urdu news summary",
    "body": "Short Urdu graphic description"
}}

NEWS STORY:
{stories_json}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )

        except Exception as exc:
            error_message = str(exc)
            error_lower = error_message.lower()

            # Detect exhausted daily free-tier quota.
            daily_quota_exhausted = (
                "free_tier_requests" in error_lower
                or "per day" in error_lower
                or "requestsperday" in error_lower
            )

            if daily_quota_exhausted:
                raise GeminiQuotaExceededError(
                    "Gemini free-tier daily quota is exhausted. "
                    "No paid API fallback will be used. "
                    "Wait for the quota reset before trying again. "
                    f"Details: {error_message}"
                ) from exc

            raise GeminiAPIError(
                f"Gemini request failed: {error_message}"
            ) from exc

        raw_text = response.text

        if not raw_text or not raw_text.strip():
            raise GeminiOutputError(
                "Gemini returned an empty response."
            )

        try:
            cleaned_text = raw_text.strip()

            # Remove Markdown fences if Gemini includes them.
            if cleaned_text.startswith("```"):
                cleaned_text = cleaned_text.split("```", 2)[1].strip()

                if cleaned_text.lower().startswith("json"):
                    cleaned_text = cleaned_text[4:].strip()

            parsed_data = json.loads(cleaned_text)

        except (json.JSONDecodeError, IndexError) as exc:
            raise GeminiOutputError(
                "Gemini returned invalid JSON. "
                "The story will not be published."
            ) from exc

        if not isinstance(parsed_data, dict):
            raise GeminiOutputError(
                "Gemini response must be a JSON object."
            )

        headline = parsed_data.get("headline")
        urdu_text = parsed_data.get("urdu_text")
        body = parsed_data.get("body")

        if not urdu_text:
            urdu_text = body

        if not body:
            body = urdu_text

        if not isinstance(headline, str) or not headline.strip():
            raise GeminiOutputError(
                "Gemini did not provide a valid headline."
            )

        if not isinstance(urdu_text, str) or not urdu_text.strip():
            raise GeminiOutputError(
                "Gemini did not provide a valid Urdu summary."
            )

        if not isinstance(body, str) or not body.strip():
            raise GeminiOutputError(
                "Gemini did not provide a valid graphic description."
            )

        return {
            "tag": str(parsed_data.get("tag") or "PAKISTAN INSIDE"),
            "headline": headline.strip(),
            "urdu_text": urdu_text.strip(),
            "body": body.strip()
        }

    @classmethod
    def generate(cls, stories):
        agent = cls()
        return agent.process_story(stories)
