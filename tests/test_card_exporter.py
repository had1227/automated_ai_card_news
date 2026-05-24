import card_exporter


def test_build_html_renders_fact_records_without_cards():
    records = [
        {
            "rank": 1,
            "title": "Open model ships",
            "summary": "A lab released a model.",
            "facts": ["Developers can test it today."],
            "evidence": ["Release notes mention availability."],
            "url": "https://example.com/model?ref=<ai>",
            "source_domain": "example.com",
            "category": "model_release",
            "confidence": 0.86,
        }
    ]

    html = card_exporter.build_html(records)

    assert "Weekly AI News" in html
    assert "<img" not in html
    assert "01.png" not in html
    assert "cards.json" not in html
    assert '<article class="news-item">' in html
    assert (
        '<a href="https://example.com/model?ref=&lt;ai&gt;" '
        'target="_blank" rel="noopener noreferrer">Open model ships</a>'
    ) in html
    assert "A lab released a model." in html
    assert "Developers can test it today." in html
    assert "Release notes mention availability." in html
