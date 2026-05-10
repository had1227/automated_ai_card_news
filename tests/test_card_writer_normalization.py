import card_writer
import pytest
from card_writer import (
    compact_top_news,
    facts_to_top_news_like,
    normalize_cards,
    select_enriched_news,
    validate_cards,
)


def test_normalize_cards_defaults_optional_card_fields_and_body_string():
    data = {
        "cards": [
            {
                "headline": "A grounded AI update",
                "body": "One concise bullet",
            }
        ]
    }

    normalized = normalize_cards(data)
    card = normalized["cards"][0]

    assert normalized["issue_title"]
    assert normalized["issue_summary"] == ""
    assert normalized["target_reader"]
    assert card["slide"] == 1
    assert card["type"] == "news"
    assert card["body"] == ["One concise bullet"]
    assert card["image_hint"] == ""
    assert card["visual_type"] == "abstract"
    assert card["source_urls"] == []


def test_facts_to_top_news_like_preserves_grounding_fields():
    records = [
        {
            "title": "Model release",
            "summary": "A lab released a model.",
            "url": "https://example.com/model",
            "source_domain": "example.com",
            "category": "models",
            "facts": ["The model was released.", "It supports tool use."],
            "evidence": ["Release notes mention tool use."],
            "entities": ["Example Lab"],
            "numbers": ["2 benchmark results"],
            "confidence": 0.82,
            "rank": 3,
        }
    ]

    [item] = facts_to_top_news_like(records)

    assert item["rank"] == 3
    assert item["title"] == "Model release"
    assert item["reason"] == "The model was released.; It supports tool use."
    assert item["score"] == 997
    assert item["importance"] == 997
    assert item["impact"] == 997
    assert item["novelty"] == 997
    assert item["confidence"] == 0.82
    assert item["article_domain"] == "example.com"
    assert item["source_domain"] == "example.com"
    assert "The model was released." in item["article_text"]
    assert "Evidence:" in item["article_text"]
    assert item["facts"] == records[0]["facts"]
    assert item["evidence"] == records[0]["evidence"]
    assert item["entities"] == records[0]["entities"]
    assert item["numbers"] == records[0]["numbers"]


def test_facts_to_top_news_like_preserves_fact_order_and_scores_from_rank():
    records = [
        {
            "rank": 1,
            "title": "First ranked item",
            "summary": "First summary",
            "url": "https://example.com/first",
            "confidence": 0.2,
        },
        {
            "rank": 2,
            "title": "Second ranked item",
            "summary": "Second summary",
            "url": "https://example.com/second",
            "confidence": 0.99,
        },
    ]

    items = facts_to_top_news_like(records)
    compacted = compact_top_news(items)

    assert [item["title"] for item in items] == ["First ranked item", "Second ranked item"]
    assert [item["rank"] for item in items] == [1, 2]
    assert [item["score"] for item in items] == [999, 998]
    assert [item["confidence"] for item in items] == [0.2, 0.99]
    assert [item["rank"] for item in compacted] == [1, 2]


def test_validate_cards_rejects_news_card_without_source_urls():
    data = {
        "issue_title": "Issue",
        "issue_summary": "Summary",
        "cards": [
            {
                "slide": 1,
                "type": "cover",
                "headline": "WEEKLY AI NEWS",
                "body": ["2026.05.04 - 2026.05.10"],
                "image_hint": "",
                "visual_type": "abstract",
                "source_urls": [],
            },
            {
                "slide": 2,
                "type": "news",
                "headline": "A grounded AI update",
                "body": ["One concise bullet"],
                "image_hint": "",
                "visual_type": "abstract",
                "source_urls": [],
            },
        ],
    }

    with pytest.raises(ValueError, match="source_urls"):
        validate_cards(data)


def test_select_enriched_news_falls_back_when_truthy_facts_convert_empty(monkeypatch, capsys):
    monkeypatch.setattr(card_writer, "load_top_news", lambda: [{"title": "Fallback"}])
    monkeypatch.setattr(card_writer, "enrich_top_news", lambda top_news: top_news)

    enriched_news = select_enriched_news(["not a dict"])

    assert enriched_news == [{"title": "Fallback"}]
    assert "none were valid dicts" in capsys.readouterr().out


def test_main_warns_when_news_facts_missing(monkeypatch, capsys):
    monkeypatch.setattr(card_writer, "load_news_facts", lambda: None)
    monkeypatch.setattr(card_writer, "load_top_news", lambda: [{"title": "Fallback"}])
    monkeypatch.setattr(card_writer, "enrich_top_news", lambda top_news: top_news)
    monkeypatch.setattr(card_writer, "build_prompt", lambda enriched_news: "prompt")
    monkeypatch.setattr(
        card_writer,
        "call_ollama",
        lambda prompt: {
            "issue_title": "Issue",
            "issue_summary": "Summary",
            "cards": [
                {
                    "slide": 1,
                    "type": "cover",
                    "headline": "WEEKLY AI NEWS",
                    "body": ["Body"],
                    "image_hint": "",
                    "visual_type": "abstract",
                    "source_urls": [],
                },
                *[
                    {
                        "slide": index,
                        "type": "news",
                        "headline": f"Card {index}",
                        "body": ["Body"],
                        "image_hint": "",
                        "visual_type": "abstract",
                        "source_urls": [f"https://example.com/{index}"],
                    }
                    for index in range(2, 9)
                ],
            ],
        },
    )
    monkeypatch.setattr(card_writer, "save_cards", lambda cards: None)

    card_writer.main()

    assert "[WARN] data/news_facts.json is missing; falling back to top_news enrichment" in capsys.readouterr().out
