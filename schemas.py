from __future__ import annotations

import math


VALID_CARD_TYPES = {"cover", "news", "insight", "summary", "actionable"}


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")


def _require_fields(data, fields, label):
    _require_mapping(data, label)
    for field in fields:
        if field not in data:
            raise ValueError(f"{label} missing required field: {field}")


def _require_non_empty_text(data, field, label):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}.{field} must be non-empty text")


def _contains_hangul(value):
    return any("\uac00" <= char <= "\ud7a3" for char in str(value or ""))


def _require_list(data, field, label):
    value = data.get(field)
    if not isinstance(value, list):
        raise ValueError(f"{label}.{field} must be a list")
    return value


def validate_item(item):
    required = [
        "platform",
        "collection_mode",
        "source_account",
        "title",
        "text",
        "url",
        "published_at",
        "metrics",
        "media_urls",
    ]
    _require_fields(item, required, "item")
    _require_non_empty_text(item, "title", "item")
    _require_non_empty_text(item, "url", "item")
    if not isinstance(item.get("metrics"), dict):
        raise ValueError("item.metrics must be an object")
    _require_list(item, "media_urls", "item")


def validate_top_news_item(item):
    required = [
        "score",
        "title",
        "summary",
        "reason",
        "category",
        "url",
        "source_count",
        "cluster",
    ]
    _require_fields(item, required, "top_news_item")
    _require_non_empty_text(item, "title", "top_news_item")
    _require_non_empty_text(item, "summary", "top_news_item")
    _require_non_empty_text(item, "url", "top_news_item")
    try:
        score = float(item["score"])
    except (TypeError, ValueError) as exc:
        raise ValueError("top_news_item.score must be numeric") from exc
    if not math.isfinite(score):
        raise ValueError("top_news_item.score must be finite")
    _require_list(item, "cluster", "top_news_item")


def validate_fact_record(record):
    required = [
        "rank",
        "title",
        "url",
        "source_domain",
        "category",
        "summary",
        "korean_title",
        "article_body",
        "published_at",
        "facts",
        "evidence",
        "entities",
        "numbers",
        "confidence",
    ]
    _require_fields(record, required, "fact_record")
    _require_non_empty_text(record, "title", "fact_record")
    _require_non_empty_text(record, "korean_title", "fact_record")
    if not _contains_hangul(record["korean_title"]):
        raise ValueError("fact_record.korean_title must contain Korean text")
    _require_non_empty_text(record, "url", "fact_record")
    article_body = _require_list(record, "article_body", "fact_record")
    if not article_body or not all(
        isinstance(paragraph, str) and paragraph.strip()
        for paragraph in article_body
    ):
        raise ValueError("fact_record.article_body must contain non-empty paragraphs")
    if len(article_body) > 4:
        raise ValueError("fact_record.article_body must contain at most 4 paragraphs")
    if not all(_contains_hangul(paragraph) for paragraph in article_body):
        raise ValueError("fact_record.article_body must contain Korean text")
    facts = _require_list(record, "facts", "fact_record")
    evidence = _require_list(record, "evidence", "fact_record")
    _require_list(record, "entities", "fact_record")
    _require_list(record, "numbers", "fact_record")
    if not facts:
        raise ValueError("fact_record.facts must not be empty")
    if not evidence:
        raise ValueError("fact_record.evidence must not be empty")
    try:
        confidence = float(record["confidence"])
    except (TypeError, ValueError) as exc:
        raise ValueError("fact_record.confidence must be numeric") from exc
    if not math.isfinite(confidence):
        raise ValueError("fact_record.confidence must be finite")
    if confidence < 0 or confidence > 1:
        raise ValueError("fact_record.confidence must be between 0 and 1")


def validate_cards(data):
    _require_fields(data, ["issue_title", "issue_summary", "cards"], "cards_data")
    cards = _require_list(data, "cards", "cards_data")
    if not cards:
        raise ValueError("cards_data.cards must not be empty")

    for idx, card in enumerate(cards, start=1):
        label = f"card[{idx}]"
        _require_fields(
            card,
            [
                "slide",
                "type",
                "headline",
                "body",
                "image_hint",
                "visual_type",
                "source_urls",
            ],
            label,
        )
        if card["type"] not in VALID_CARD_TYPES:
            raise ValueError(f"{label}.type is invalid: {card['type']}")
        _require_non_empty_text(card, "headline", label)
        body = _require_list(card, "body", label)
        if not all(isinstance(line, str) for line in body):
            raise ValueError(f"{label}.body must contain only text")
        source_urls = _require_list(card, "source_urls", label)
        if card["type"] == "news" and not source_urls:
            raise ValueError(f"{label}.source_urls must not be empty for news cards")
