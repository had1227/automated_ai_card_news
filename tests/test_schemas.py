import pytest

from schemas import (
    validate_cards,
    validate_fact_record,
    validate_item,
    validate_top_news_item,
)


def test_validate_item_accepts_minimal_valid_item():
    item = {
        "platform": "rss",
        "collection_mode": "source",
        "source_account": "OpenAI",
        "title": "New model",
        "text": "OpenAI announced a new model.",
        "url": "https://example.com/news",
        "published_at": "2026-05-09T00:00:00+00:00",
        "metrics": {},
        "media_urls": [],
    }

    validate_item(item)


def test_validate_item_rejects_missing_title():
    item = {"url": "https://example.com/news"}

    with pytest.raises(ValueError, match="title"):
        validate_item(item)


def test_validate_top_news_item_accepts_ranked_item():
    item = {
        "score": 91.0,
        "title": "Model release",
        "summary": "A model was released.",
        "reason": "Official announcement.",
        "category": "model_release",
        "url": "https://example.com/news",
        "source_count": 1,
        "cluster": [],
    }

    validate_top_news_item(item)


def test_validate_fact_record_requires_evidence():
    record = {
        "rank": 1,
        "title": "Model release",
        "url": "https://example.com/news",
        "source_domain": "example.com",
        "category": "model_release",
        "summary": "A model was released.",
        "facts": ["A model was released."],
        "evidence": [],
        "entities": ["Example AI"],
        "numbers": [],
        "confidence": 0.8,
    }

    with pytest.raises(ValueError, match="evidence"):
        validate_fact_record(record)


def test_validate_cards_accepts_valid_cards():
    data = {
        "issue_title": "Weekly AI News",
        "issue_summary": "Top AI stories.",
        "target_reader": "AI engineers",
        "cards": [
            {
                "slide": 1,
                "type": "cover",
                "headline": "WEEKLY AI NEWS",
                "body": [
                    "2026.05.03 - 2026.05.09",
                    "Top AI updates for builders.",
                ],
                "image_hint": "abstract network",
                "visual_type": "abstract",
                "source_urls": [],
            },
            {
                "slide": 2,
                "type": "news",
                "headline": "New model announced",
                "body": ["Brief summary", "Evidence-backed explanation"],
                "image_hint": "model diagram",
                "visual_type": "diagram",
                "source_urls": ["https://example.com/news"],
            },
        ],
    }

    validate_cards(data)
