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
        "POLITICS", "COURT", "PUBLIC_INTEREST", "ECONOMY", "DEFENSE",
        "WORLD", "HEALTH", "EDUCATION", "TECHNOLOGY", "BUSINESS",
        "SPORTS", "ENTERTAINMENT", "CRIME", "ENVIRONMENT", "ENERGY",
        "TRANSPORT", "GOVERNANCE", "ELECTIONS", "DIPLOMACY",
        "HUMAN_RIGHTS", "CLIMATE", "INVESTIGATION", "LOCAL", "GENERAL",
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

                validated = []
                source_map = {story.get("link"): story for story in stories if story.get("link")}
                for item in data:
                    clean = self._validate_item(item, language)
                    original = source_map.get(clean.get("source_url"))
                    if not original:
                        raise GeminiOutputError("Editor output did not preserve a valid source_url")
                    clean.update({
                        "source_url": original.get("link", ""),
                        "source_name": original.get("source", clean["source_name"]),
                        "image_url": original.get("image_url", ""),
                        "published_at": original.get("published_at", ""),
                        "impact_score": original.get("impact_score", 0),
                        "urgency": original.get("urgency", "NORMAL"),
                        "topics": original.get("topics", []),
                        "source_count": original.get("source_count", 1),
                        "corroborating_sources": original.get("corroborating_sources", [original.get("source", "News source")]),
                    })
                    validated.append(clean)
                return validated

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
- Treat source_count and corroborating_sources as metadata, not proof by themselves. State independent confirmation only when the supplied sources genuinely support the same fact.
- Distinguish allegations, claims, court observations, orders and final judgments.
- Do not label a story BREAKING unless the supplied evidence supports urgency and recency.
- If the source material is insufficient, say so in the text or exclude the item.
- Keep the headline concise, factual and compelling. No clickbait.
- Every item must include a proper Urdu-script headline and body.
- Also provide a concise, accurate English headline and English summary for bilingual distribution.
- Urdu is the primary publication language; English must not replace or dilute the Urdu story.
- Use neutral Pakistani newsroom vocabulary and preserve the difference between allegations, official claims and verified facts.

Return only a JSON array. Each object must contain exactly:
"tag", "headline", "urdu_text", "body", "english_headline", "english_text", "source_name", "source_attribution", "source_url", "language".
For source_url, copy the exact original link from the corresponding input story. Never invent or modify a URL.
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
        english_headline = str(item.get("english_headline") or "").strip()
        english_text = str(item.get("english_text") or "").strip()
        if not headline or not urdu_text:
            raise GeminiOutputError("Missing Urdu headline or story text")

        if not english_headline or not english_text:
            raise GeminiOutputError("Missing English headline or summary for bilingual output")

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
            "english_headline": english_headline,
            "english_text": english_text,
            "body": body or urdu_text[:140],
            "source_name": str(item.get("source_name") or "Source not specified").strip(),
            "source_attribution": str(item.get("source_attribution") or "ذرائع کے مطابق").strip(),
            "source_url": str(item.get("source_url") or "").strip(),
            "language": "ur",
        }

    def fallback_stories(self, stories):
        # Deliberately disabled: raw English RSS titles must never be published as Urdu cards.
        raise GeminiOutputError(
            "English/raw-title fallback is disabled. Urdu editorial generation is mandatory."
        )
