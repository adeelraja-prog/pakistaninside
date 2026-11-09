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
    ALLOWED_TAGS = {
        "POLITICS", "ECONOMY", "COURT", "HEALTH",
        "TECH", "DEFENSE", "GENERAL", "PUBLIC_INTEREST",
    }

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY missing")
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    def process_stories(self, stories, language="ur"):
        if language != "ur":
            raise ValueError("This newsroom pipeline currently requires Urdu-first output")
        if not stories:
            raise ValueError("No stories provided")

        prompt = self._build_prompt(stories, language)
        last_error = None

        for attempt in range(5):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.25,
                    ),
                )
                raw = (response.text or "").strip()
                if not raw:
                    raise GeminiOutputError("Empty model response")

                raw = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw, flags=re.IGNORECASE)
                data = json.loads(raw)
                if isinstance(data, dict):
                    data = [data]
                if not isinstance(data, list) or not data:
                    raise GeminiOutputError("Expected a non-empty JSON array")

                return [self._validate_item(item, language) for item in data]

            except Exception as exc:
                message = str(exc).lower()
                if any(token in message for token in ("free_tier", "quota", "resource_exhausted", "429")):
                    raise GeminiQuotaExceededError(str(exc)) from exc
                last_error = exc
                if isinstance(exc, GeminiOutputError) and attempt >= 2:
                    raise
                if attempt == 4:
                    break
                wait = min(10 * (attempt + 1), 40)
                print(f"[EDITOR] Retry {attempt + 1}/5 in {wait}s: {type(exc).__name__}: {exc}")
                time.sleep(wait)

        raise GeminiAPIError(str(last_error or "Editor failed after retries")) from last_error

    def _build_prompt(self, stories, language):
        stories_json = json.dumps(stories, ensure_ascii=False, indent=2)
        return f"""You are the senior Urdu-language news editor for Adeel Raja's independent digital newsroom.

EDITORIAL RULES:
- Write natural, idiomatic Pakistani Urdu in Urdu script, not Hindi and not Roman Urdu.
- Do not translate mechanically. Use concise, broadcast-quality newsroom Urdu.
- Prioritise verified public-interest developments: PTI/Imran Khan and opposition, courts and judiciary, constitutional matters, parliament, accountability, cost of living, public services, economy, national security, foreign affairs and major world events.
- Do not automatically favour government press releases. Routine ceremonial announcements, minor appointments and self-congratulatory press releases are low priority unless they have material public consequences.
- Do not suppress a story because it criticises or supports a political party. Apply the same evidence and public-interest standards to all sides.
- Never invent facts, names, quotes, dates, figures, legal outcomes or source attribution.
- Distinguish allegations, claims, court observations, orders and final judgments.
- Do not label a story BREAKING unless the supplied evidence supports urgency and recency.
- If the source material is insufficient, say so in the text or exclude the item.
- Keep the headline concise, factual and compelling. No clickbait.
- Every item must include a proper Urdu-script headline and body.

Return only a JSON array. Each object must contain exactly:
"tag", "headline", "urdu_text", "body", "source_name", "source_attribution", "language".
Use language="ur". tag must be one of: {", ".join(sorted(self.ALLOWED_TAGS))}.

INPUT STORIES:
{stories_json}
"""

    def _validate_item(self, item, language="ur"):
        if not isinstance(item, dict):
            raise GeminiOutputError("Each story must be a JSON object")

        headline = str(item.get("headline") or "").strip()
        urdu_text = str(item.get("urdu_text") or "").strip()
        body = str(item.get("body") or "").strip()
        if not headline or not urdu_text:
            raise GeminiOutputError("Missing Urdu headline or story text")

        # Require meaningful Arabic-script Urdu; English-only fallback is forbidden.
        arabic_chars = re.findall(r"[\u0600-\u06FF]", headline + " " + urdu_text)
        if len(arabic_chars) < 8:
            raise GeminiOutputError("Output does not contain sufficient Urdu-script text")

        tag = str(item.get("tag") or "GENERAL").upper().strip()
        if tag not in self.ALLOWED_TAGS:
            tag = "GENERAL"

        return {
            "tag": tag,
            "headline": headline,
            "urdu_text": urdu_text,
            "english_text": "",
            "body": body or urdu_text[:140],
            "source_name": str(item.get("source_name") or "Source not specified").strip(),
            "source_attribution": str(item.get("source_attribution") or "ذرائع کے مطابق").strip(),
            "language": "ur",
        }

    def fallback_stories(self, stories):
        # Deliberately disabled: raw English RSS titles must never be published as Urdu cards.
        raise GeminiOutputError(
            "English/raw-title fallback is disabled. Urdu editorial generation is mandatory."
        )
