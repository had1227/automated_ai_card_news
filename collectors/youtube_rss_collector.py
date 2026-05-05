# collectors/youtube_rss_collector.py

import feedparser
from collectors.date_utils import is_within_days

def collect_youtube_channel_rss(channel):
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel['channel_id']}"
    feed = feedparser.parse(rss_url)

    items = []

    for entry in feed.entries:
            
        published_at = entry.get("published")

        if not is_within_days(published_at, days=7):
            continue
        
        items.append({
            "platform": "youtube",
            "collection_mode": "account",
            "topic": None,
            "source_account": channel["name"],
            "title": entry.get("title"),
            "text": entry.get("summary", ""),
            "url": entry.get("link"),
            "author": channel["name"],
            "published_at": entry.get("published"),
            "metrics": {},
            "media_urls": [],
        })

    return items