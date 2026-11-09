"""Free-first RSS newsroom scout with public-interest ranking and image recovery."""

import hashlib
import ipaddress
import os
import json
import re
import socket
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup


class ScoutAgent:
    TOPIC_RULES = {
        "POLITICS": [
            "pti", "imran khan", " عمران خان", "پی ٹی آئی", "تحریک انصاف",
            "نواز شریف", "بلاول", "پارلیمان", "پارلیمنٹ", "election",
            "political", "وزیر اعظم", "وزیراعظم", "opposition", "حکومت",
            "حکومت اور اپوزیشن", "سیاسی",
        ],
        "COURT": [
            "supreme court", "high court", "عدالت", "عدلیہ", "چیف جسٹس",
            "جج", "سپریم کورٹ", "ہائی کورٹ", "عدالتی", "hearing",
            "verdict", "bail", "petition", "آئین", "آئینی",
        ],
        "PUBLIC_INTEREST": [
            "بجلی", "گیس", "پٹرول", "پیٹرول", "مہنگائی", "آٹا", "تنخواہ",
            "پنشن", "تعلیم", "صحت", "پانی", "لوڈشیڈنگ", "inflation",
            "electricity", "petrol", "prices", "tax", "public",
            "اسپتال", "اسکول", "بل",
        ],
        "ECONOMY": [
            "معیشت", "معاشی", "اسٹیٹ بینک", "آئی ایم ایف", "imf",
            "economy", "budget", "rupee", "exports", "trade", "قرض",
        ],
        "DEFENSE": [
            "security", "دہشت گردی", "فوج", "پاک فوج", "دفاع",
            "افغانستان", "بلوچستان", "خیبر پختونخوا", "terror",
            "militant", "attack", "دھماکہ", "حملہ",
        ],
        "WORLD": [
            "international", "world", "غزہ", "فلسطین", "اسرائیل",
            "ایران", "امریکا", "امریکی", "china", "india", "ukraine",
            "gaza", "war", "ceasefire",
        ],
    }

    HIGH_IMPACT_TERMS = [
        "arrest", "arrested", "detained", "released", "bail granted",
        "court order", "court ruling", "verdict", "disqualified",
        "convicted", "acquitted", "constitutional", "amendment",
        "no-confidence", "resigns", "resigned", "election date",
        "election commission", "assembly dissolved", "killed", "dead",
        "blast", "explosion", "attack", "fired", "tariff increase",
        "price hike", "fuel price", "power tariff", "strike",
        "اہم فیصلہ", "عدالتی حکم", "ضمانت", "گرفتار", "رہائی",
        "نااہل", "اہم پیش رفت", "آئینی ترمیم", "اسمبلی تحلیل",
        "انتخابات کی تاریخ", "دھماکہ", "حملہ", "شہید", "جاں بحق",
        "بجلی مہنگی", "پیٹرول مہنگا", "قیمتوں میں اضافہ",
    ]

    BREAKING_TERMS = [
        "breaking", "just in", "urgent", "فوری", "بریکنگ",
        "ہنگامی", "ابھی ابھی", "تازہ ترین",
    ]

    PRESS_RELEASE_TERMS = [
        "press release", "پریس ریلیز", "اعلامیہ", "ترجمان کے مطابق",
        "وزارت نے بتایا", "اجلاس کی صدارت", "وفد سے ملاقات",
        "وفد نے ملاقات", "congratulates", "inaugurated",
        "chairing a meeting", "presided over a meeting",
        "reviewed progress", "directed officials", "congratulated", "delegation meeting",
    ]

    ROUTINE_TITLE_TERMS = [
        "chairing meeting", "chairs meeting", "presides over",
        "delegation calls on", "meets delegation", "delegation meeting", "chairs routine", "inaugurates",
        "inauguration ceremony", "congratulates", "pays tribute",
        "اجلاس کی صدارت", "وفد کی ملاقات", "ملاقات کی",
        "افتتاحی تقریب", "مبارکباد", "تعزیتی پیغام",
    ]

    CORE_LANES = ("POLITICS", "COURT", "PUBLIC_INTEREST")

    def __init__(self, manifest_path="manifest.json"):
        with open(manifest_path, "r", encoding="utf-8") as handle:
            self.config = json.load(handle)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; AdeelRajaNewsroom/2.0; +https://github.com/adeelraja-prog/pakistaninside)"
        })
        self.timeout = int(self.config.get("feed_timeout_seconds", 15))

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
                    from datetime import datetime as dt
                    return dt.fromtimestamp(__import__("time").mktime(value), timezone.utc).isoformat()
                except (ValueError, OverflowError, OSError):
                    pass
        return ""

    @staticmethod
    def _public_https_url(url):
        try:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                return False
            host = parsed.hostname.lower()
            if host in {"localhost", "localhost.localdomain"}:
                return False
            try:
                addresses = {ipaddress.ip_address(host)}
            except ValueError:
                addresses = {
                    ipaddress.ip_address(item[4][0])
                    for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
                }
            return bool(addresses) and all(address.is_global for address in addresses)
        except (ValueError, OSError):
            return False

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
        for field in ("summary", "description", "content"):
            value = entry.get(field, "")
            if isinstance(value, list):
                value = " ".join(str(x.get("value", "")) for x in value if isinstance(x, dict))
            match = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", str(value), re.I)
            if match and match.group(1).startswith("https://"):
                return match.group(1)
        return ""

    def fetch_rss_news(self):
        stories = []
        feeds = self.config.get("rss_feeds", []) + self.config.get("additional_rss_feeds", [])
        # Optional public X-to-RSS bridge URLs; no paid X API or scraping is used.
        feeds.extend(url.strip() for url in os.getenv("X_RSS_FEEDS", "").split(";") if url.strip())
        for feed_url in feeds:
            try:
                response = self.session.get(feed_url, timeout=self.timeout)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                source = self.clean_html(feed.feed.get("title") or urlparse(feed_url).netloc)
                for entry in feed.entries[:int(self.config.get("entries_per_feed", 35))]:
                    title = self.clean_html(entry.get("title"))
                    summary = self.clean_html(entry.get("summary") or entry.get("description") or title)
                    link = entry.get("link", "")
                    if not title or not link.startswith("https://"):
                        continue
                    entry_source = entry.get("source") or {}
                    publisher = (
                        self.clean_html(entry_source.get("title"))
                        if isinstance(entry_source, dict) and entry_source.get("title")
                        else source
                    )
                    stories.append({
                        "title": title,
                        "summary": summary[:1800],
                        "link": link,
                        "source": publisher,
                        "published_at": self.parse_date(entry),
                        "image_url": self.extract_image(entry),
                    })
            except Exception as exc:
                print(f"[SCOUT] Feed error {feed_url}: {type(exc).__name__}: {exc}")
        return stories

    def resolve_article_image(self, story):
        """Recover a lead image from Open Graph/Twitter metadata when RSS omits it."""
        if story.get("image_url"):
            return story["image_url"]
        article_url = story.get("link", "")
        if not self._public_https_url(article_url):
            return ""
        try:
            response = self.session.get(article_url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            if not self._public_https_url(response.url):
                return ""
            if "text/html" not in response.headers.get("Content-Type", "").lower():
                return ""
            soup = BeautifulSoup(response.text[:2_000_000], "html.parser")
            for selector in (
                {"property": "og:image"},
                {"name": "twitter:image"},
                {"property": "og:image:secure_url"},
            ):
                node = soup.find("meta", attrs=selector)
                candidate = node.get("content", "").strip() if node else ""
                candidate = urljoin(response.url, candidate)
                if candidate and self._public_https_url(candidate):
                    story["image_url"] = candidate
                    return candidate
            return ""
        except Exception as exc:
            print(f"[SCOUT] Article image unavailable for {article_url}: {type(exc).__name__}: {exc}")
            return ""

    @staticmethod
    def story_key(story):
        text = re.sub(r"[^\w\u0600-\u06FF]+", " ", story["title"].lower())
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def score_story(self, story):
        title = (story.get("title") or "").lower()
        summary = (story.get("summary") or "").lower()
        text = title + " " + summary
        score = 0
        topics = []

        for topic, terms in self.TOPIC_RULES.items():
            title_hits = sum(1 for term in terms if term.lower() in title)
            body_hits = sum(1 for term in terms if term.lower() in summary)
            if title_hits or body_hits:
                topics.append(topic)
                score += min(title_hits * 9 + body_hits * 3, 24)

        impact_hits = sum(1 for term in self.HIGH_IMPACT_TERMS if term in text)
        score += min(impact_hits * 9, 27)

        age_hours = None
        if story.get("published_at"):
            try:
                published = datetime.fromisoformat(story["published_at"])
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                age_hours = (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).total_seconds() / 3600
                if age_hours < -0.25:
                    story["future_dated"] = True
                    score -= 30
                else:
                    age_hours = max(0, age_hours)
                    score += max(0, 24 - int(age_hours / 1.5))
            except (TypeError, ValueError):
                age_hours = None

        has_breaking_language = any(term in text for term in self.BREAKING_TERMS)
        has_major_event = impact_hits > 0
        if age_hours is not None and age_hours <= 2 and has_major_event:
            story["urgency"] = "POTENTIAL_BREAKING"
            score += 18
        elif has_breaking_language and age_hours is not None and age_hours <= 4 and has_major_event:
            story["urgency"] = "POTENTIAL_BREAKING"
            score += 12
        else:
            story["urgency"] = "NORMAL"

        press_release = any(term in text for term in self.PRESS_RELEASE_TERMS)
        routine_title = any(term in title for term in self.ROUTINE_TITLE_TERMS)
        story["press_release_penalty"] = press_release or routine_title
        if press_release or routine_title:
            score -= 28 if not has_major_event else 12

        if age_hours is None:
            score -= 8
        elif age_hours > 72:
            score -= 25
        elif age_hours > 24:
            score -= 12

        story["topics"] = topics or ["GENERAL"]
        story["tag"] = next((lane for lane in self.CORE_LANES if lane in topics), topics[0] if topics else "GENERAL")
        story["impact_score"] = score
        story["age_hours"] = age_hours
        story["major_event"] = has_major_event
        story["eligible"] = score >= int(getattr(self, "config", {}).get("minimum_story_score", 8)) and not story.get("future_dated")
        if routine_title and not has_major_event and score < 12:
            story["eligible"] = False
            story["exclude_reason"] = "ROUTINE_LOW_PUBLIC_INTEREST"
        return story

    @staticmethod
    def _similar_title(left, right):
        normalise = lambda value: re.sub(r"[^\w\u0600-\u06FF]+", " ", value.lower()).strip()
        return SequenceMatcher(None, normalise(left), normalise(right)).ratio()

    def cluster_related(self, stories):
        clusters = []
        for story in stories:
            match = next((
                group for group in clusters
                if self._similar_title(story["title"], group[0]["title"]) >= 0.76
            ), None)
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
            lead["impact_score"] += min(max(0, len(sources) - 1) * 8, 24)
            if len(sources) >= 2:
                lead["corroborated_by_multiple_feeds"] = True
            merged.append(lead)
        return merged

    def select_editorial_candidates(self, stories, limit=8):
        """Greedy topic diversity so a single feed/topic cannot crowd out public interest."""
        eligible = [item for item in stories if item.get("eligible", True)]
        eligible.sort(key=lambda item: (
            item["impact_score"],
            item.get("source_count", 1),
            bool(item.get("image_url")),
        ), reverse=True)
        selected, topic_counts = [], {}
        # First secure one best candidate for each core public-interest lane, when available.
        for lane in self.CORE_LANES:
            candidate = next((item for item in eligible if lane in item.get("topics", []) and item not in selected), None)
            if candidate and len(selected) < limit:
                selected.append(candidate)
                topic_counts[lane] = topic_counts.get(lane, 0) + 1
        for item in eligible:
            if item in selected or len(selected) >= limit:
                continue
            primary = item.get("tag", "GENERAL")
            if topic_counts.get(primary, 0) >= 3:
                continue
            selected.append(item)
            topic_counts[primary] = topic_counts.get(primary, 0) + 1
        return selected

    def run(self):
        print("[SCOUT] Collecting public-interest RSS feeds...")
        collected = self.fetch_rss_news()
        unique, seen = [], set()
        for story in collected:
            key = self.story_key(story)
            if key in seen:
                continue
            seen.add(key)
            unique.append(self.score_story(story))
        clustered = self.cluster_related(unique)
        candidates = self.select_editorial_candidates(clustered, limit=int(self.config.get("editorial_candidate_limit", 12)))
        # Image discovery runs only for the strongest candidate set to conserve free CI time.
        for item in candidates:
            if not item.get("image_url"):
                self.resolve_article_image(item)
        candidates.sort(key=lambda item: (
            item["impact_score"],
            bool(item.get("image_url")),
        ), reverse=True)
        print(f"[SCOUT] Fetched {len(collected)}; {len(unique)} unique; {len(candidates)} editorial candidates.")
        for item in candidates:
            print(
                f"[SCOUT] score={item['impact_score']} tag={item['tag']} "
                f"image={'yes' if item.get('image_url') else 'no'} "
                f"sources={item.get('source_count', 1)} title={item['title'][:100]}"
            )
        return candidates
