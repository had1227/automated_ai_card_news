import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from dateutil import parser as date_parser
from datetime import datetime, timedelta, timezone

from llm_client import generate_json


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
LLM_RECENCY_CONFIDENCE_THRESHOLD = 0.7
LLM_RECENCY_TEXT_CHARS = 2500
RECENCY_SCHEMA = {
    "type": "object",
    "properties": {
        "is_recent": {"type": "boolean"},
        "published_date": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["is_recent", "published_date", "confidence", "reason"],
}
NOISE_URL_PARTS = (
    "/privacy",
    "/policies",
    "/terms",
    "terms-of-service",
    "/legal",
    "/login",
    "/signin",
    "/sign-in",
    "/signup",
    "/sign-up",
    "/account",
    "/cookies",
)


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


def is_within_days_at(value, days=7, now=None):
    dt = parse_date(value)

    if dt is None:
        return None

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    cutoff = now - timedelta(days=days)
    return dt >= cutoff


def is_valid_href(href):
    if not href:
        return False

    if href.startswith(("mailto:", "javascript:", "#", "tel:")):
        return False

    if len(href) > 500:
        return False

    if is_noise_url(href):
        return False

    return True


def is_noise_url(url):
    value = str(url or "").lower()
    return any(part in value for part in NOISE_URL_PARTS)


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


def build_recency_prompt(title, text, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    payload = {
        "current_date": now.date().isoformat(),
        "recent_cutoff_date": cutoff.date().isoformat(),
        "title": clean_text(title),
        "text": clean_text(text)[:LLM_RECENCY_TEXT_CHARS],
    }

    return f"""
You are deciding whether a crawled website article should be kept for a weekly AI news pipeline.

Use only the JSON data below. Decide whether the article content appears to be published, announced, or updated on or after recent_cutoff_date.

Rules:
- Return JSON only.
- If the article has no clear date signal, set is_recent to true with low confidence.
- Only set is_recent to false when the content clearly points to an older date.
- Do not infer from unrelated copyright, privacy, or footer dates.

Return exactly:
{{
  "is_recent": true,
  "published_date": "YYYY-MM-DD or unknown",
  "confidence": 0.0,
  "reason": "short reason"
}}

JSON data:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()


def call_recency_llm(title, text, now=None):
    return generate_json(
        build_recency_prompt(title, text, now=now),
        RECENCY_SCHEMA,
        temperature=0.0,
    )


def as_confidence(value):
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def as_bool(value, default=True):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return default


def is_probably_recent_by_llm(title, text, now=None):
    try:
        judgment = call_recency_llm(title, text, now=now)
    except Exception as e:
        print(f"[WARN] site recency LLM failed - {e}")
        return True

    if as_bool(judgment.get("is_recent", True), default=True):
        return True

    confidence = as_confidence(judgment.get("confidence", 0.0))
    return confidence < LLM_RECENCY_CONFIDENCE_THRESHOLD


def should_keep_article(published_raw, title, text, now=None):
    structured_recent = is_within_days_at(published_raw, days=7, now=now)
    if structured_recent is not None:
        return structured_recent

    return is_probably_recent_by_llm(title, text, now=now)


def fetch_soup(url):
    res = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def fetch_article(url, title_hint, source_name):
    try:
        soup = fetch_soup(url)

        title = extract_title(soup, title_hint)
        published_raw = extract_date(soup)

        text = extract_text(soup)

        if len(text) < 200:
            return None

        if not should_keep_article(published_raw, title, text):
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
