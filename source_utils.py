from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from dateutil import parser as date_parser


OFFICIAL_DOMAINS = {
    "anthropic.com",
    "blog.google",
    "deepmind.google",
    "deepseek.com",
    "developer.nvidia.com",
    "huggingface.co",
    "mistral.ai",
    "moonshot.cn",
    "nvidia.com",
    "openai.com",
    "qwenlm.github.io",
    "research.nvidia.com",
    "zhipuai.cn",
}

RESEARCH_DOMAINS = {
    "arxiv.org",
    "export.arxiv.org",
    "nature.com",
    "openreview.net",
    "paperswithcode.com",
    "science.org",
    "semanticscholar.org",
}

CODE_DOMAINS = {
    "github.com",
    "gitlab.com",
    "pypi.org",
}

SOCIAL_DOMAINS = {
    "bsky.app",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "reddit.com",
    "threads.net",
    "twitter.com",
    "x.com",
}

MEDIA_DOMAINS = {
    "404media.co",
    "axios.com",
    "bbc.com",
    "bloomberg.com",
    "cnbc.com",
    "cnn.com",
    "nytimes.com",
    "techcrunch.com",
    "theinformation.com",
    "theverge.com",
    "wired.com",
}

TRUST_SCORES = {
    "official": 1.0,
    "research": 0.9,
    "code": 0.8,
    "media": 0.65,
    "social": 0.55,
}


def clean_domain(url):
    value = str(url or "").strip()
    if not value:
        return ""

    parsed = urlparse(value)
    if not parsed.netloc:
        parsed = urlparse(f"//{value}")

    domain = parsed.netloc or parsed.path.split("/", 1)[0]
    domain = domain.rsplit("@", 1)[-1].split(":", 1)[0].lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def is_google_news_url(url):
    return clean_domain(url) == "news.google.com"


def classify_source(url):
    domain = clean_domain(url)

    if domain in OFFICIAL_DOMAINS:
        return "official"
    if domain in RESEARCH_DOMAINS:
        return "research"
    if domain in CODE_DOMAINS:
        return "code"
    if domain in SOCIAL_DOMAINS:
        return "social"
    if domain in MEDIA_DOMAINS:
        return "media"

    return "media"


def source_trust_score(url):
    return TRUST_SCORES[classify_source(url)]


def parse_datetime(value):
    if not value:
        return None

    try:
        dt = date_parser.parse(str(value))
    except (TypeError, ValueError, OverflowError):
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def prune_history(items, keep_days=45, max_items=5000, now=None):
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    current_time = current_time.astimezone(timezone.utc)

    cutoff = current_time - timedelta(days=keep_days)
    kept = []

    for item in items:
        published_at = parse_datetime(item.get("published_at"))
        if published_at is None or published_at >= cutoff:
            kept.append(item)

    return kept[-max_items:]
