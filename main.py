import os
import re
import sys
from pathlib import Path

from engine.scout import ScoutAgent
from engine.editor import (
    EditorAgent,
    GeminiQuotaExceededError,
    GeminiAPIError,
    GeminiOutputError,
)
from engine.designer import DesignerAgent
from engine.strategist import StrategistAgent


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

OUTPUT_PATH = Path("assets/output/latest_news_card.png")

PUBLISH_TO_FACEBOOK = (
    os.getenv("PUBLISH_TO_FACEBOOK", "false").strip().lower() == "true"
)

BRAND_HASHTAGS = "#PakistanInside #AdeelRaja"


# ---------------------------------------------------------
# CONTENT VALIDATION
# ---------------------------------------------------------

URDU_PATTERN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]"
)

URL_PATTERN = re.compile(
    r"https?://|www\.",
    re.IGNORECASE
)

FORBIDDEN_PHRASES = [
    "ماخذ کا لنک",
    "اصل خبر",
    "مکمل خبر کے لیے",
    "تفصیلات کے لیے ماخذ",
    "مزید تفصیلات کے لیے لنک",
    "source link",
    "read more",
    "click here",
    "visit the source",
]


class EditorialValidationError(Exception):
    """Raised when Gemini output is not suitable for publication."""


def contains_urdu(text):
    return bool(URDU_PATTERN.search(str(text or "")))


def validate_public_text(text, field_name, minimum_length=10):
    """
    Validate text intended for the public poster or Facebook caption.
    """

    if not isinstance(text, str):
        raise EditorialValidationError(
            f"{field_name} is missing or is not text."
        )

    text = text.strip()

    if len(text) < minimum_length:
        raise EditorialValidationError(
            f"{field_name} is too short."
        )

    if not contains_urdu(text):
        raise EditorialValidationError(
            f"{field_name} does not contain Urdu script."
        )

    if URL_PATTERN.search(text):
        raise EditorialValidationError(
            f"{field_name} contains a URL. Source links must remain internal."
        )

    lowered = text.lower()

    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in lowered:
            raise EditorialValidationError(
                f"{field_name} contains prohibited placeholder wording."
            )

    return text


def validate_editorial_output(edited_data):
    """
    Only accept original Urdu editorial output.
    Never substitute RSS headlines, source links, or fallback text.
    """

    if not isinstance(edited_data, dict):
        raise EditorialValidationError(
            "Editor did not return a valid editorial object."
        )

    headline = validate_public_text(
        edited_data.get("headline"),
        "Urdu headline",
        minimum_length=8,
    )

    urdu_text = validate_public_text(
        edited_data.get("urdu_text"),
        "Urdu editorial summary",
        minimum_length=20,
    )

    body = validate_public_text(
        edited_data.get("body"),
        "Urdu story body",
        minimum_length=30,
    )

    # Do not pass source metadata or RSS links to the Designer.
    # Only approved editorial fields are allowed through.
    approved_data = {
        "tag": str(edited_data.get("tag", "") or "").strip(),
        "headline": headline,
        "urdu_text": urdu_text,
        "body": body,
    }

    return approved_data


# ---------------------------------------------------------
# FACEBOOK CAPTION
# ---------------------------------------------------------

def create_facebook_caption(edited_data):
    """
    Create a caption exclusively from approved Urdu editorial content.
    No RSS headline, source name, URL, or generic fallback is included.
    """

    headline = edited_data["headline"]
    urdu_text = edited_data["urdu_text"]

    caption = (
        f"{headline}\n\n"
        f"{urdu_text}\n\n"
        f"{BRAND_HASHTAGS}"
    )

    # Final safety check before publishing.
    if URL_PATTERN.search(caption):
        raise EditorialValidationError(
            "Facebook caption contains a URL."
        )

    if not contains_urdu(caption):
        raise EditorialValidationError(
            "Facebook caption does not contain Urdu."
        )

    return caption


# ---------------------------------------------------------
# MAIN NEWSROOM PIPELINE
# ---------------------------------------------------------

def main():

    print("\n" + "=" * 60)
    print("PAKISTAN INSIDE — NEWSROOM AUTOMATION")
    print("THE STORY BEHIND THE STORY")
    print("=" * 60)

    print(
        f"\n[CONFIG] Facebook publishing: "
        f"{'ENABLED' if PUBLISH_TO_FACEBOOK else 'DISABLED'}"
    )

    try:

        # -------------------------------------------------
        # AGENT 1 — SCOUT
        # -------------------------------------------------

        print("\n[AGENT 1: SCOUT] Collecting news...")

        scout = ScoutAgent()
        raw_stories = scout.run()

        if not raw_stories:
            raise RuntimeError(
                "Scout did not collect any news stories."
            )

        print(
            f"[SCOUT] Collected {len(raw_stories)} stories."
        )

        # One story per run until the editorial pipeline
        # has been reviewed and approved.
        story = raw_stories[0]

        if not isinstance(story, dict):
            raise RuntimeError(
                "Scout returned an invalid story format."
            )

        print(
            "[SCOUT] Selected one story for editorial processing."
        )

        # -------------------------------------------------
        # AGENT 2 — EDITOR
        # -------------------------------------------------

        print("\n[AGENT 2: EDITOR] Generating original Urdu journalism...")

        editor = EditorAgent()

        # Source information is provided internally to the Editor.
        # It must not automatically become public-facing content.
        edited_data = editor.process_story(story)

        # Stop immediately if the Editor output is not suitable.
        approved_data = validate_editorial_output(edited_data)

        print("[EDITOR] Urdu editorial content passed validation.")
        print("[EDITOR] Original Urdu headline approved.")

        # -------------------------------------------------
        # AGENT 3 — DESIGNER
        # -------------------------------------------------

        print("\n[AGENT 3: DESIGNER] Creating branded news poster...")

        designer = DesignerAgent()

        # Only approved Urdu editorial fields reach the Designer.
        card_path = designer.generate_card(approved_data)

        if not card_path:
            raise RuntimeError(
                "Designer did not return a poster path."
            )

        card_path = Path(card_path)

        if not card_path.is_file():
            raise RuntimeError(
                f"Poster file was not created: {card_path}"
            )

        print(f"[DESIGNER] Poster generated: {card_path}")

        # -------------------------------------------------
        # AGENT 4 — STRATEGIST / PUBLISHER
        # -------------------------------------------------

        caption = create_facebook_caption(approved_data)

        if not PUBLISH_TO_FACEBOOK:

            print("\n[STRATEGIST] Facebook publishing is disabled.")
            print("[STRATEGIST] Poster generated but NOT published.")
            print(f"[OUTPUT] {card_path}")

            return

        print("\n[AGENT 4: STRATEGIST] Publishing approved content...")

        strategist = StrategistAgent()

        result = strategist.publish_to_facebook(
            str(card_path),
            caption
        )

        if not result:
            raise RuntimeError(
                "Facebook publisher returned no confirmation."
            )

        if isinstance(result, dict):
            post_id = (
                result.get("post_id")
                or result.get("id")
            )
        else:
            post_id = None

        if not post_id:
            raise RuntimeError(
                "Facebook publishing was not confirmed. "
                "No successful post ID was returned."
            )

        print("\n" + "=" * 60)
        print("[PUBLISHING SUCCESS]")
        print(f"Facebook Post ID: {post_id}")
        print("=" * 60)

    except GeminiQuotaExceededError as error:

        print("\n[NEWSROOM PAUSED]")
        print("[EDITOR] Gemini free-tier quota has been exhausted.")
        print("[SAFETY] No fallback content will be generated.")
        print("[SAFETY] No poster will be published.")
        print(f"[DETAILS] {error}")

        sys.exit(1)

    except GeminiAPIError as error:

        print("\n[NEWSROOM STOPPED]")
        print("[EDITOR] Gemini API error.")
        print("[SAFETY] No fallback content will be generated.")
        print("[SAFETY] Facebook publishing stopped.")
        print(f"[DETAILS] {error}")

        sys.exit(1)

    except GeminiOutputError as error:

        print("\n[NEWSROOM STOPPED]")
        print("[EDITOR] Gemini returned invalid editorial output.")
        print("[SAFETY] No fallback content will be generated.")
        print("[SAFETY] Facebook publishing stopped.")
        print(f"[DETAILS] {error}")

        sys.exit(1)

    except EditorialValidationError as error:

        print("\n[EDITORIAL QUALITY CHECK FAILED]")
        print(f"[REASON] {error}")
        print("[SAFETY] Designer and Facebook Publisher were not called.")

        sys.exit(1)

    except Exception as error:

        print("\n[NEWSROOM ERROR]")
        print(f"[ERROR] {type(error).__name__}: {error}")
        print("[SAFETY] Pipeline stopped. No fallback content will be published.")

        sys.exit(1)


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
