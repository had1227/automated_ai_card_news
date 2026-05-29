import cluster_rank


def test_ai_evaluate_cluster_uses_generate_json_with_extended_text_and_schema(monkeypatch):
    captured = {}
    expected = {
        "is_ai_news": True,
        "is_card_news_worthy": True,
        "category": "model_release",
    }

    def fake_generate_json(prompt, response_schema, temperature=0.1):
        captured["prompt"] = prompt
        captured["response_schema"] = response_schema
        captured["temperature"] = temperature
        return expected

    monkeypatch.setattr(cluster_rank, "generate_json", fake_generate_json)

    detailed_text = "x" * 250 + "README detail from later in the text"
    result = cluster_rank.ai_evaluate_cluster([{"title": "Repo", "text": detailed_text}])

    required = captured["response_schema"]["required"]
    properties = captured["response_schema"]["properties"]
    assert result == expected
    assert "README detail from later in the text" in captured["prompt"]
    assert "is_card_news_worthy" in required
    assert "is_card_news_worthy" in properties
    assert captured["temperature"] == 0.1


def test_ai_is_duplicate_uses_structured_confidence(monkeypatch):
    def fake_generate_json(prompt, response_schema, temperature=0.1):
        return {
            "is_duplicate": True,
            "confidence": 0.65,
            "reason": "Same launch announcement",
        }

    monkeypatch.setattr(cluster_rank, "generate_json", fake_generate_json)

    assert cluster_rank.ai_is_duplicate(
        {"title": "Gemini update", "summary": "Gemini launched", "category": "model_release"},
        {"title": "Google Gemini update", "summary": "Gemini launched", "category": "model_release"},
    )


def test_ai_is_duplicate_rejects_low_confidence(monkeypatch):
    def fake_generate_json(prompt, response_schema, temperature=0.1):
        return {
            "is_duplicate": True,
            "confidence": 0.64,
            "reason": "Related but not the same event",
        }

    monkeypatch.setattr(cluster_rank, "generate_json", fake_generate_json)

    assert not cluster_rank.ai_is_duplicate(
        {"title": "Gemini update", "summary": "Gemini launched", "category": "model_release"},
        {"title": "Google AI Studio update", "summary": "Studio changed", "category": "product_update"},
    )


def test_ai_is_duplicate_returns_false_when_generate_json_fails(monkeypatch):
    def fake_generate_json(prompt, response_schema, temperature=0.1):
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr(cluster_rank, "generate_json", fake_generate_json)

    assert not cluster_rank.ai_is_duplicate(
        {"title": "Gemini update", "summary": "Gemini launched", "category": "model_release"},
        {"title": "Google Gemini update", "summary": "Gemini launched", "category": "model_release"},
    )
