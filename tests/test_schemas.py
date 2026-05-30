import pytest

from schemas import (
    validate_cards,
    validate_fact_record,
    validate_item,
    validate_top_news_item,
)


def _valid_top_news_item(**overrides):
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
    item.update(overrides)
    return item


def _valid_fact_record(**overrides):
    record = {
        "rank": 1,
        "title": "Model release",
        "url": "https://example.com/news",
        "source_domain": "example.com",
        "category": "model_release",
        "summary": "A model was released.",
        "korean_title": "새 모델 공개",
        "article_body": ["새 모델이 공개됐다. 개발자는 API를 통해 사용할 수 있다."],
        "published_at": "2026-05-24T00:00:00+00:00",
        "facts": ["A model was released."],
        "evidence": ["https://example.com/news"],
        "entities": ["Example AI"],
        "numbers": [],
        "confidence": 0.8,
    }
    record.update(overrides)
    return record


def _valid_cards_data(**card_overrides):
    card = {
        "slide": 2,
        "type": "news",
        "headline": "New model announced",
        "body": ["Brief summary", "Evidence-backed explanation"],
        "image_hint": "model diagram",
        "visual_type": "diagram",
        "source_urls": ["https://example.com/news"],
    }
    card.update(card_overrides)
    return {
        "issue_title": "Weekly AI News",
        "issue_summary": "Top AI stories.",
        "cards": [card],
    }


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
    item = {
        "platform": "rss",
        "collection_mode": "source",
        "source_account": "OpenAI",
        "text": "OpenAI announced a new model.",
        "url": "https://example.com/news",
        "published_at": "2026-05-09T00:00:00+00:00",
        "metrics": {},
        "media_urls": [],
    }

    with pytest.raises(ValueError, match="title"):
        validate_item(item)


def test_validate_top_news_item_accepts_ranked_item():
    item = _valid_top_news_item()

    validate_top_news_item(item)


@pytest.mark.parametrize("score", [float("nan"), "inf", "-inf"])
def test_validate_top_news_item_rejects_non_finite_score(score):
    item = _valid_top_news_item(score=score)

    with pytest.raises(ValueError, match="finite"):
        validate_top_news_item(item)


def test_validate_fact_record_requires_evidence():
    record = _valid_fact_record(evidence=[])

    with pytest.raises(ValueError, match="evidence"):
        validate_fact_record(record)


def test_validate_fact_record_requires_korean_article_body():
    record = _valid_fact_record(article_body=[])

    with pytest.raises(ValueError, match="article_body"):
        validate_fact_record(record)


def test_validate_fact_record_rejects_more_than_four_article_body_paragraphs():
    record = _valid_fact_record(article_body=["one", "two", "three", "four", "five"])

    with pytest.raises(ValueError, match="article_body"):
        validate_fact_record(record)


def test_validate_fact_record_requires_korean_title():
    record = _valid_fact_record(korean_title=" ")

    with pytest.raises(ValueError, match="korean_title"):
        validate_fact_record(record)


def test_validate_fact_record_requires_korean_text_in_title_and_body():
    title_record = _valid_fact_record(korean_title="Open model release")
    with pytest.raises(ValueError, match="korean_title"):
        validate_fact_record(title_record)

    body_record = _valid_fact_record(article_body=["A model was released."])
    with pytest.raises(ValueError, match="article_body"):
        validate_fact_record(body_record)


def test_validate_fact_record_requires_published_at_field():
    record = _valid_fact_record()
    del record["published_at"]

    with pytest.raises(ValueError, match="published_at"):
        validate_fact_record(record)


@pytest.mark.parametrize("confidence", [float("nan"), "inf", "-inf"])
def test_validate_fact_record_rejects_non_finite_confidence(confidence):
    record = _valid_fact_record(confidence=confidence)

    with pytest.raises(ValueError, match="finite"):
        validate_fact_record(record)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_validate_fact_record_rejects_out_of_range_confidence(confidence):
    record = _valid_fact_record(confidence=confidence)

    with pytest.raises(ValueError, match="between 0 and 1"):
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


def test_validate_cards_rejects_invalid_card_type():
    data = _valid_cards_data(type="feature")

    with pytest.raises(ValueError, match="type is invalid"):
        validate_cards(data)


def test_validate_cards_allows_visual_type_as_ignored_metadata():
    data = _valid_cards_data(visual_type="photo")

    validate_cards(data)


def test_validate_cards_rejects_news_card_empty_source_urls():
    data = _valid_cards_data(source_urls=[])

    with pytest.raises(ValueError, match="source_urls"):
        validate_cards(data)


def test_validate_cards_rejects_non_list_body():
    data = _valid_cards_data(body="Brief summary")

    with pytest.raises(ValueError, match="body must be a list"):
        validate_cards(data)
