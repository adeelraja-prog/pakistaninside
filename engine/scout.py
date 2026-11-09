import json
import re
import time
import hashlib
from difflib import SequenceMatcher
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urlparse

import feedparser
import requests


class ScoutAgent:
    """Collect, normalise, deduplicate and rank public-interest RSS stories."""

    TOPIC_RULES = {
        "POLITICS": ["pti", "imran khan", " عمران خان", "پی ٹی آئی", "تحریک انصاف", "نواز شریف", "بلاول", "پارلیمان", "پارلیمنٹ", "election", "political", "وزیر اعظم", "وزیراعظم"],
        "COURT": ["supreme court", "high court", "عدالت", "عدلیہ", "چیف جسٹس", "جج", "سپریم کورٹ", "ہائی کورٹ", "عدالتی", "hearing", "verdict", "bail", "petition"],
        "PUBLIC_INTEREST": ["بجلی", "گیس", "پٹرول", "پیٹرول", "مہنگائی", "آٹا", "تنخواہ", "پنشن", "تعلیم", "صحت", "water", "load shedding", "inflation", "electricity", "petrol", "prices", "tax"],
        "ECONOMY": ["معیشت", "معاشی", "اسٹیٹ بینک", "آئی ایم ایف", "imf", "economy", "budget", "rupee", "دہشت گردی", "exports", "trade"],
        "DEFENSE": ["security", "دہشت گردی", "فوج", "پاک فوج", "دفاع", "افغانستان", "بلوچستان", "خیبر پختونخوا", "terror", "militant", "attack"],
        "WORLD": ["international", "world", "غزہ", "فلسطین", "اسرائیل", "ایران", "امریکا", "امریکی", "china", "india", "ukraine", "gaza"],
    }
    BREAKING_TERMS = ["breaking", "just in", "urgent", "فوری", "بریکنگ", "ہنگامی", "ابھی ابھی"]
    PRESS_RELEASE_TERMS = ["press release", "پریس ریلیز", "اعلامیہ", "ترجمان کے مطابق", "وزارت نے بتایا", "اجلاس کی صدارت", "وفد سے ملاقات", "وفد نے ملاقات"]

    def __init__(self, manifest_path="manifest.json"):
        with open(manifest_path, "r", encoding="utf-8") as handle:
            self.config = json.load(handle)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AdeelRajaNewsroom/1.0 (RSS news monitor)"})

    @staticmethod
    def clean_html(value):
        value = re.sub(r"<[^>]+>", " ", str(value or ""))
        return re.sub(r"\s+", " ", unescape(value)).strip()

    @staticmethod
    def parse_date(entry):
        for key in ("published", "updated", "created"):
            raw = entry.get(key)
            if raw:
                try:
                    dt = parsedate_to_datetime(raw)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc).isoformat()
                except (TypeError, ValueError, OverflowError):
                    pass
        for key in ("published_parsed", "updated_parsed"):
            value = entry.get(key)
            if value:
                try:
                    return datetime.fromtimestamp(time.mktime(value), timezone.utc).isoformat()
                except (ValueError, OverflowError, OSError):
                    pass
        return ""

    @staticmethod
    def extract_image(entry):
        for item in entry.get("media_content", []) + entry.get("media_thumbnail", []):
            url = item.get("url")
            if url and url.startswith("https://"):
                return url
        for item in entry.get("links", []):
            if item.get("rel") == "enclosure" and item.get("type", "").startswith("image/"):
                url = item.get("href", "")
                if url.startswith("https://"):
                    return url
        for field in ("summary", "description"):
            match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', entry.get(field, ""), re.I)
            if match and match.group(1).startswith("https://"):
                return match.group(1)
        return ""

    def fetch_rss_news(self):
        stories = []
        for feed_url in self.config.get("rss_feeds", []):
            try:
                response = self.session.get(feed_url, timeout=20)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                source = self.clean_html(feed.feed.get("title") or urlparse(feed_url).netloc)
                for entry in feed.entries[:30]:
                    title = self.clean_html(entry.get("title"))
                    summary = self.clean_html(entry.get("summary") or entry.get("description") or title)
                    link = entry.get("link", "")
                    if not title or not link.startswith("http"):
                        continue
                    stories.append({
                        "title": title,
                        "summary": summary[:1400],
                        "link": link,
                        "source": source,
                        "published_at": self.parse_date(entry),
                        "image_url": self.extract_image(entry),
                    })
            except Exception as exc:
                print(f"[SCOUT] Feed error {feed_url}: {type(exc).__name__}: {exc}")
        return stories

    @staticmethod
    def story_key(story):
        text = re.sub(r"[^\w\u0600-\u06FF]+", " ", story["title"].lower())
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def score_story(self, story):
        text = (story["title"] + " " + story["summary"]).lower()
        score, topics = 0, []
        age_hours = None
        for topic, terms in self.TOPIC_RULES.items():
            hits = sum(1 for term in terms if term.lower() in text)
            if hits:
                topics.append(topic)
                score += min(hits * 5, 18)

        # Recency is explicit: missing timestamps never qualify as breaking.
        if story.get("published_at"):
            try:
                published = datetime.fromisoformat(story["published_at"])
                age_hours = max(0, (datetime.now(timezone.utc) - published).total_seconds() / 3600)
                score += max(0, 18 - int(age_hours / 2))
            except ValueError:
                age_hours = None

        has_breaking_language = any(term in text for term in self.BREAKING_TERMS)
        if has_breaking_language and age_hours is not None and age_hours <= 3:
            score += 12
            story["urgency"] = "POTENTIAL_BREAKING"
        else:
            story["urgency"] = "NORMAL"

        if any(term in text for term in self.PRESS_RELEASE_TERMS):
            score -= 12
            story["press_release_penalty"] = True
        else:
            story["press_release_penalty"] = False

        story["topics"] = topics or ["GENERAL"]
        story["tag"] = next((t for t in ("COURT", "POLITICS", "PUBLIC_INTEREST", "DEFENSE", "ECONOMY", "WORLD") if t in topics), "GENERAL")
        story["impact_score"] = score
        return story

    @staticmethod
    def _similar_title(left, right):
        normalise = lambda value: re.sub(r"[^\w\u0600-\u06FF]+", " ", value.lower()).strip()
        return SequenceMatcher(None, normalise(left), normalise(right)).ratio()

    def cluster_related(self, stories):
        clusters = []
        for story in stories:
            match = next((group for group in clusters if self._similar_title(story["title"], group[0]["title"]) >= 0.76), None)
            if match is None:
                clusters.append([story])
            else:
                match.append(story)

        merged = []
        for group in clusters:
            lead = max(group, key=lambda item: (item["impact_score"], bool(item.get("image_url"))))
            sources = sorted({item["source"] for item in group if item.get("source")})
            lead["source_count"] = len(sources)
            lead["corroborating_sources"] = sources
            lead["source_urls"] = [item["link"] for item in group if item.get("link")]
            lead["impact_score"] += min(max(0, len(sources) - 1) * 6, 12)
            merged.append(lead)
        return merged

    def run(self):
        print("[SCOUT] Collecting up to 30 entries per feed...")
        collected = self.fetch_rss_news()
        unique, seen = [], set()
        for story in collected:
            key = self.story_key(story)
            if key in seen:
                continue
            seen.add(key)
            unique.append(self.score_story(story))
        unique = self.cluster_related(unique)
        unique.sort(key=lambda item: (item["impact_score"], bool(item.get("image_url"))), reverse=True)
        print(f"[SCOUT] Collected {len(collected)}; {len(unique)} unique stories.")
        for item in unique[:10]:
            print(f"[SCOUT] score={item['impact_score']} topics={item['topics']} source={item['source']} title={item['title'][:110]}")
        return unique[:30]
