import feedparser
import json

class ScoutAgent:
    def __init__(self, manifest_path='manifest.json'):
        with open(manifest_path, 'r') as f:
            self.config = json.load(f)

    def fetch_rss_news(self):
        raw_stories = []
        for feed_url in self.config.get('rss_feeds', []):
            try:
                parsed = feedparser.parse(feed_url)
                for entry in parsed.entries[:3]:
                    raw_stories.append({
                        'title': entry.title,
                        'summary': getattr(entry, 'summary', entry.title),
                        'link': entry.link,
                        'source': getattr(parsed.feed, 'title', 'Web News')
                    })
            except Exception as e:
                print(f"[Scout Warning] Feed fetch failed {feed_url}: {e}")
        return raw_stories

    def run(self):
        print("🕵️ [Agent 1: Scout] Scanning Twitter/X & Web News feeds...")
        stories = self.fetch_rss_news()
        print(f"🕵️ [Agent 1: Scout] Collected {len(stories)} stories.")
        return stories
