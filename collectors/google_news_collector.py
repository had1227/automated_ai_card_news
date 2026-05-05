import feedparser
from urllib.parse import quote

from collectors.date_utils import is_within_days

def collect_google_news(query):
    encoded_query = quote(query)

    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(url)

    items = []

    for entry in feed.entries[:100]:
        published_at = entry.get("published")

        if not is_within_days(published_at, days=7):
            continue

        items.append({
            "platform": "google_news",
            "collection_mode": "search",
            "topic": query,
            "source_account": "Google News",
            "title": entry.title,
            "text": entry.summary,
            "url": entry.link,
            "author": entry.get("source", {}).get("title", "news"),
            "published_at": entry.get("published", None),
            "metrics": {},
            "media_urls": []
        })

    return items