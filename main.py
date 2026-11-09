import json
import os
import sys
from pathlib import Path

from engine.scout import ScoutAgent
from engine.editor import EditorAgent, GeminiQuotaExceededError
from engine.designer import DesignerAgent
from engine.video import VideoAgent
from engine.strategist import StrategistAgent
from engine.published_state import PublishedState


def _social_links():
    with open("manifest.json", "r", encoding="utf-8") as handle:
        config = json.load(handle)
    links = dict(config.get("social_links", {}))
    links["whatsapp_channel"] = (
        os.getenv("WHATSAPP_CHANNEL_URL")
        or links.get("whatsapp_channel")
        or ""
    )
    return links


def _distribution_caption(item, links):
    urdu = f"{item['headline']}\n\n{item.get('body') or item.get('urdu_text', '')}"
    english = (
        f"{item.get('english_headline', '')}\n"
        f"{item.get('english_text', '')}"
    ).strip()
    sources = ", ".join(item.get(
        "corroborating_sources",
        [item.get("source_name", "News source")],
    ))
    caption = (
        f"{urdu}\n\n"
        f"ENGLISH\n{english}\n\n"
        f"Sources: {sources}\n{item['source_url']}\n\n"
        "Adeel Raja\n#AdeelRaja"
    )
    footer = [
        ("YouTube", links.get("youtube")),
        ("Shorts", links.get("youtube_shorts")),
        ("Facebook", links.get("facebook")),
        ("X", links.get("x")),
        ("TikTok", links.get("tiktok")),
        ("WhatsApp Channel", links.get("whatsapp_channel")),
    ]
    active = [f"{label}: {url}" for label, url in footer if url]
    if active:
        caption += "\n\nFollow Adeel Raja:\n" + "\n".join(active)
    return caption


def _write_platform_drafts(item, poster_path, video_path, caption, links):
    draft_dir = Path("assets/output/drafts")
    draft_dir.mkdir(parents=True, exist_ok=True)
    slug = Path(poster_path).stem.replace("adeel_raja_news_", "")
    whatsapp = {
        "platform": "WhatsApp Channel",
        "status": "READY_FOR_MANUAL_POST",
        "poster_style": item.get("poster_style", "light_editorial"),
        "headline_urdu": item["headline"],
        "body_urdu": item.get("body") or item.get("urdu_text", ""),
        "headline_english": item.get("english_headline", ""),
        "body_english": item.get("english_text", ""),
        "caption": caption,
        "image_file": poster_path,
        "video_file": video_path or "",
        "source_url": item["source_url"],
        "channel_invite_url": links.get("whatsapp_channel", ""),
    }
    (draft_dir / f"whatsapp_{slug}.json").write_text(
        json.dumps(whatsapp, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    x_text = (
        f"{item['headline']}\n"
        f"{item.get('english_headline', '')}\n"
        f"{item['source_url']}\n"
        "#AdeelRaja"
    )
    (draft_dir / f"x_{slug}.txt").write_text(x_text, encoding="utf-8")

    metadata = {
        "publisher": "Adeel Raja",
        "source_url": item["source_url"],
        "facebook_caption": caption,
        "youtube_title": (item.get("english_headline") or item["headline"])[:90] + " #Shorts",
        "youtube_description": caption,
        "youtube_privacy_default": "private",
        "poster_style": item.get("poster_style", "light_editorial"),
        "poster_file": poster_path,
        "reel_file": video_path or "",
        "whatsapp_draft": str(draft_dir / f"whatsapp_{slug}.json"),
        "x_draft": str(draft_dir / f"x_{slug}.txt"),
    }
    (draft_dir / f"distribution_{slug}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata


def main():
    print("=== Adeel Raja Newsroom — Bilingual Public-Interest Edition ===")
    scout = ScoutAgent()
    stories = scout.run()
    if not stories:
        print("[SCOUT] No eligible public-interest stories found; nothing will be published.")
        return 0

    image_candidates = [story for story in stories if story.get("image_url")]
    if not image_candidates:
        print("[SAFE STOP] No candidate has a verified editorial image. No broken posters will be produced.")
        return 2

    # One bounded Urdu-first bilingual editorial request per run to conserve free-tier quota.
    try:
        editor = EditorAgent()
        processed = editor.process_stories(image_candidates[:8], language="ur")
    except GeminiQuotaExceededError as exc:
        print(f"[EDITOR BLOCKED] Free-tier quota exhausted: {exc}")
        print("[SAFE STOP] No unedited or English-only source headlines will be published.")
        return 2
    except Exception as exc:
        print(f"[EDITOR BLOCKED] Urdu/bilingual editorial validation failed: {type(exc).__name__}: {exc}")
        print("[SAFE STOP] No unverified or malformed copy will be published.")
        return 2

    if not processed:
        print("[SAFE STOP] Editor returned no validated bilingual stories.")
        return 2

    designer = DesignerAgent()
    video_agent = VideoAgent()
    strategist = StrategistAgent()
    published_state = PublishedState()
    links = _social_links()

    publish_facebook = os.getenv("PUBLISH_TO_FACEBOOK", "false").lower() == "true"
    publish_youtube = os.getenv("PUBLISH_TO_YOUTUBE", "false").lower() == "true"
    youtube = None
    if publish_youtube:
        from engine.youtube import YouTubePublisher
        youtube = YouTubePublisher()

    max_posts = int(os.getenv("MAX_POSTS_PER_RUN", "3"))
    failures = 0
    completed = 0

    for index, item in enumerate(processed, start=1):
        if completed >= max_posts:
            break
        source_url = item.get("source_url", "")
        if item.get("language") != "ur" or not item.get("urdu_text"):
            print(f"[STORY SKIPPED {index}] Urdu-first gate failed.")
            failures += 1
            continue
        if not item.get("english_headline") or not item.get("english_text"):
            print(f"[STORY SKIPPED {index}] English companion copy is missing.")
            failures += 1
            continue
        if not item.get("image_url") or not source_url:
            print(f"[STORY SKIPPED {index}] Image or source URL is missing.")
            failures += 1
            continue

        try:
            item["poster_style"] = published_state.next_poster_style()
            poster_path = designer.generate_card(item)
        except Exception as exc:
            failures += 1
            print(f"[POSTER FAILED {index}] {type(exc).__name__}: {exc}")
            continue

        video_path = ""
        try:
            video_path = video_agent.generate_reel(item)
            print(f"[REEL {index}] Created: {video_path}")
        except Exception as exc:
            failures += 1
            print(f"[REEL FAILED {index}] {type(exc).__name__}: {exc}")
            # A reel failure must not suppress an otherwise valid poster or its Facebook post.

        caption = _distribution_caption(item, links)
        drafts = _write_platform_drafts(item, poster_path, video_path, caption, links)
        print(f"[POSTER {index}] Created: {poster_path}")
        print(f"[DRAFTS {index}] WhatsApp and X drafts: {drafts['whatsapp_draft']}, {drafts['x_draft']}")

        if publish_facebook:
            if published_state.is_published(source_url, "facebook"):
                print(f"[FACEBOOK {index}] Already published; skipping duplicate.")
            else:
                result = strategist.publish_to_facebook(poster_path, caption)
                if not isinstance(result, dict) or result.get("error"):
                    failures += 1
                    print(f"[FACEBOOK FAILED {index}] {result}")
                else:
                    published_state.mark_published(
                        source_url, "facebook", result.get("id") or result.get("post_id")
                    )
                    print(f"[FACEBOOK CONFIRMED {index}] {result}")

        if publish_youtube and video_path:
            if published_state.is_published(source_url, "youtube"):
                print(f"[YOUTUBE {index}] Already uploaded; skipping duplicate.")
            else:
                try:
                    result = youtube.upload_short(
                        video_path,
                        item.get("english_headline") or item["headline"],
                        caption,
                        tags=["AdeelRaja", "PakistanNews", "PTI", "Pakistan", "Shorts"],
                    )
                    published_state.mark_published(source_url, "youtube", result["video_id"])
                    print(f"[YOUTUBE CONFIRMED {index}] {result}")
                except Exception as exc:
                    failures += 1
                    print(f"[YOUTUBE FAILED {index}] {type(exc).__name__}: {exc}")

        completed += 1

    print(f"[SUMMARY] {completed} stories processed; {failures} errors.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
