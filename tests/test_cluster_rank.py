import cluster_rank


def test_ai_evaluate_cluster_uses_extended_item_text(monkeypatch):
    captured = {}

    def fake_ollama_json(prompt, max_retries=2, timeout=120):
        captured["prompt"] = prompt
        return {"is_ai_news": True}

    monkeypatch.setattr(cluster_rank, "ollama_json", fake_ollama_json)

    detailed_text = "x" * 250 + "README detail from later in the text"
    cluster_rank.ai_evaluate_cluster([{"title": "Repo", "text": detailed_text}])

    assert "README detail from later in the text" in captured["prompt"]
