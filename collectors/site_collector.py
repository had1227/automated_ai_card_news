import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from dateutil import parser as date_parser
from datetime import datetime, timedelta, timezone


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

MAX_WORKERS = 8


def clean_text(text):
    return " ".join((text or "").split())


def parse_date(value):
    if not value:
        return None
    try:
        dt = date_parser.parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def is_within_days(value, days=7):
    dt = parse_date(value)

    # 사이트는 날짜 추출 실패가 많으므로 날짜 없으면 유지
    if dt is None:
        return True

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return dt >= cutoff


def is_valid_href(href):
    if not href:
        return False

    if href.startswith(("mailto:", "javascript:", "#", "tel:")):
        return False

    if len(href) > 500:
        return False

    return True


def extract_title(soup, fallback=""):
    og = soup.select_one("meta[property='og:title']")
    if og and og.get("content"):
        return clean_text(og["content"])

    h1 = soup.select_one("h1")
    if h1:
        return clean_text(h1.get_text(" ", strip=True))

    title = soup.select_one("title")
    if title:
        return clean_text(title.get_text(" ", strip=True))

    return fallback


def extract_date(soup):
    time_tag = soup.find("time")
    if time_tag:
        value = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)
        if value:
            return value

    meta_keys = [
        "article:published_time",
        "article:modified_time",
        "datePublished",
        "date",
        "pubdate",
        "publish_date",
        "published",
    ]

    for key in meta_keys:
        meta = soup.select_one(
            f"meta[property='{key}'], meta[name='{key}'], meta[itemprop='{key}']"
        )
        if meta and meta.get("content"):
            return meta["content"]

    return None


def extract_text(soup):
    selectors = [
        "article",
        "main",
        "[class*=post]",
        "[class*=article]",
        "[class*=content]",
        "[class*=body]",
    ]

    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            text = clean_text(el.get_text(" ", strip=True))
            if len(text) > 200:
                return text[:6000]

    return clean_text(soup.get_text(" ", strip=True))[:4000]


def fetch_soup(url):
    res = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def fetch_article(url, title_hint, source_name):
    try:
        soup = fetch_soup(url)

        title = extract_title(soup, title_hint)
        published_raw = extract_date(soup)

        # 날짜가 잡히면 7일 이내만 유지
        if not is_within_days(published_raw, days=7):
            return None

        text = extract_text(soup)

        if len(text) < 200:
            return None

        return {
            "platform": "site",
            "collection_mode": "source",
            "topic": None,
            "source_account": source_name,
            "title": title,
            "text": text,
            "url": url,
            "author": source_name,
            "published_at": str(parse_date(published_raw)) if published_raw else None,
            "metrics": {},
            "media_urls": [],
        }

    except Exception:
        return None


def collect_site(source):
    items = []

    try:
        list_soup = fetch_soup(source["url"])
    except Exception as e:
        print(f"[WARN] 사이트 목록 실패: {source.get('name')} - {e}")
        return items

    selector = source.get("item_selector", "a")
    url_contains = source.get("url_contains")
    max_items = source.get("max_items", 20)

    links = []
    seen = set()

    for a in list_soup.select(selector):
        href = a.get("href")

        if not is_valid_href(href):
            continue

        url = urljoin(source["url"], href)

        if url_contains and url_contains not in url:
            continue

        if url in seen:
            continue

        title = clean_text(a.get_text(" ", strip=True))

        seen.add(url)
        links.append((title, url))

        if len(links) >= max_items:
            break

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(fetch_article, url, title, source["name"])
            for title, url in links
        ]

        for future in as_completed(futures):
            item = future.result()
            if item:
                items.append(item)

    return items