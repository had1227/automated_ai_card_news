import feedparser
import requests
from io import BytesIO
from datetime import datetime, timezone
from collectors.date_utils import is_within_days

ARXIV_FEEDS = [
    "cs.AI",
    "cs.LG",
    "cs.CL"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

MAX_PDF_EXCERPT_CHARS = 6000
MAX_PDF_PAGES = 3


# --------------------------
# 필터 함수 (핵심)
# --------------------------

def is_valid_arxiv(entry):
    title = entry.title or ""
    summary = entry.summary or ""

    text = (title + " " + summary).lower()

    # 1️⃣ 길이 필터
    if len(summary) < 200:
        return False

    # 2️⃣ AI 키워드 필터
    AI_KEYWORDS = [
        "llm",
        "language model",
        "transformer",
        "diffusion",
        "agent",
        "multimodal",
        "gpt",
        "vision",
        "reasoning",
        "alignment",
    ]

    if not any(k in text for k in AI_KEYWORDS):
        return False

    return True


# --------------------------
# 메인 collector
# --------------------------

def arxiv_pdf_url_from_entry_link(link):
    value = str(link or "").strip()
    if not value:
        return ""
    if "/pdf/" in value:
        return value
    if "/abs/" in value:
        return value.replace("/abs/", "/pdf/", 1)
    return ""


def extract_pdf_text(pdf_bytes, max_pages=MAX_PDF_PAGES):
    try:
        from pypdf import PdfReader
    except ImportError:
        print("[WARN] pypdf is not installed; skipping arXiv PDF text extraction")
        return ""

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except Exception as e:
        print(f"[WARN] arXiv PDF parse failed - {e}")
        return ""

    text_parts = []
    for page in reader.pages[:max_pages]:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue

    text = " ".join(" ".join(part.split()) for part in text_parts if part)
    return text[:MAX_PDF_EXCERPT_CHARS]


def fetch_pdf_excerpt(pdf_url):
    if not pdf_url:
        return ""

    try:
        res = requests.get(pdf_url, headers=HEADERS, timeout=30)
        res.raise_for_status()
    except Exception as e:
        print(f"[WARN] arXiv PDF fetch failed: {pdf_url} - {e}")
        return ""

    return extract_pdf_text(res.content)


def build_arxiv_text(summary, pdf_excerpt):
    parts = [summary]
    if pdf_excerpt:
        parts.append("PDF excerpt:")
        parts.append(pdf_excerpt)
    return "\n\n".join(part for part in parts if part)


def collect_arxiv():
    items = []

    for category in ARXIV_FEEDS:
        url = f"http://export.arxiv.org/rss/{category}"

        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[WARN] arXiv 실패: {category} - {e}")
            continue

        count = 0

        for entry in feed.entries:

            # 🔥 필터 적용
            if not is_valid_arxiv(entry):
                continue
            
            published_at = entry.get("published")

            if not is_within_days(published_at, days=7):
                continue

            pdf_url = arxiv_pdf_url_from_entry_link(entry.link)
            pdf_excerpt = fetch_pdf_excerpt(pdf_url)

            items.append({
                "platform": "arxiv",
                "collection_mode": "rss",
                "topic": category,
                "source_account": "arXiv",
                "title": entry.title,
                "text": build_arxiv_text(entry.summary, pdf_excerpt),
                "url": entry.link,
                "author": entry.get("author", "arxiv"),
                "published_at": entry.get("published", None),
                "metrics": {},
                "media_urls": []
            })

            count += 1

            # 카테고리당 최대 10개
            if count >= 15:
                break

    return items
