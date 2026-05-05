import feedparser
from datetime import datetime, timezone
from collectors.date_utils import is_within_days

ARXIV_FEEDS = [
    "cs.AI",
    "cs.LG",
    "cs.CL"
]


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

    # 3️⃣ 저가치 논문 제거
    LOW_VALUE = [
        "benchmark",
        "dataset",
        "survey",
        "review",
        "ablation",
        "evaluation only",
    ]

    if any(k in text for k in LOW_VALUE):
        return False

    return True


# --------------------------
# 메인 collector
# --------------------------

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

            items.append({
                "platform": "arxiv",
                "collection_mode": "rss",
                "topic": category,
                "source_account": "arXiv",
                "title": entry.title,
                "text": entry.summary,
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