import feedparser
import json
import re

class ScoutAgent:
    def __init__(self, manifest_path="manifest.json"):
        with open(manifest_path, "r") as f:
            self.config = json.load(f)

    def fetch_rss_news(self):
        stories = []
        for url in self.config.get("rss_feeds", []):
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", title)
                    stories.append({
                        "title": title,
                        "summary": re.sub(r"<[^>]+>", "", summary)[:400],
                        "link": entry.get("link", ""),
                        "source": feed.feed.get("title", "News"),
                    })
            except Exception as e:
                print(f"[Scout] Feed error {url}: {e}")
        return stories

    def run(self):
        print("[Scout] Collecting stories...")
        stories = self.fetch_rss_news()
        # Simple impact scoring
        impact_keywords = ["petrol", "electricity", "imf", "court", "scheme", "price", "inflation", "پٹرول", "بجلی"]
        for s in stories:
            text = (s["title"] + " " + s["summary"]).lower()
            s["impact"] = sum(1 for k in impact_keywords if k in text)
        stories.sort(key=lambda x: x["impact"], reverse=True)
        print(f"[Scout] Collected {len(stories)} stories")
        return stories[:20]
