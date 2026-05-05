# collectors/rss_collector.py

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from collectors.date_utils import is_within_days

def clean_html(html):
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)


def parse_date(date_str):
    try:
        return str(date_parser.parse(date_str))
    except Exception:
        return None


def collect_rss(source):
    """
    source = {
        "name": "...",
        "url": "..."
    }
    """

    feed = feedparser.parse(source["url"])
    items = []

    for entry in feed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()

        summary = (
            entry.get("summary")
            or entry.get("description")
            or ""
        )

        published = (
            entry.get("published")
            or entry.get("updated")
        )

        item = {
            "platform": "rss",
            "collection_mode": "source",
            "topic": None,
            "source_account": source["name"],
            "title": title,
            "text": clean_html(summary),
            "url": link,
            "author": entry.get("author"),
            "published_at": parse_date(published),
            "metrics": {},
            "media_urls": extract_media(entry),
        }

        # 기본 필터
        if not item["title"] or not item["url"]:
            continue
        
        published_at = entry.get("published") or entry.get("updated")

        if not is_within_days(published_at, days=7):
            continue

        items.append(item)

    return items


def extract_media(entry):
    media_urls = []

    # RSS media:content
    media_content = entry.get("media_content", [])
    for media in media_content:
        url = media.get("url")
        if url:
            media_urls.append(url)

    # enclosure
    enclosures = entry.get("enclosures", [])
    for enc in enclosures:
        url = enc.get("href")
        if url:
            media_urls.append(url)

    return media_urls