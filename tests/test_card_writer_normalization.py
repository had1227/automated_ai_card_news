import card_writer
from card_writer import facts_to_top_news_like, normalize_cards


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
        }
    ]

    [item] = facts_to_top_news_like(records)

    assert item["title"] == "Model release"
    assert item["reason"] == "The model was released.; It supports tool use."
    assert item["score"] == 82.0
    assert item["importance"] == 82.0
    assert item["impact"] == 82.0
    assert item["novelty"] == 82.0
    assert item["article_domain"] == "example.com"
    assert item["source_domain"] == "example.com"
    assert "The model was released." in item["article_text"]
    assert "Evidence:" in item["article_text"]
    assert item["facts"] == records[0]["facts"]
    assert item["evidence"] == records[0]["evidence"]
    assert item["entities"] == records[0]["entities"]
    assert item["numbers"] == records[0]["numbers"]


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
            "issue_summary": "",
            "cards": [
                {
                    "slide": index,
                    "type": "news",
                    "headline": f"Card {index}",
                    "body": ["Body"],
                    "image_hint": "",
                    "visual_type": "abstract",
                    "source_urls": [],
                }
                for index in range(1, 9)
            ],
        },
    )
    monkeypatch.setattr(card_writer, "save_cards", lambda cards: None)

    card_writer.main()

    assert "[WARN] data/news_facts.json is missing; falling back to top_news enrichment" in capsys.readouterr().out
