import review_exporter


def test_fact_by_rank_maps_ranked_records_and_ignores_missing_rank():
    facts = [
        {"rank": 2, "title": "Second"},
        {"title": "No rank"},
        {"rank": 1, "title": "First"},
    ]

    assert review_exporter.fact_by_rank(facts) == {
        1: {"rank": 1, "title": "First"},
        2: {"rank": 2, "title": "Second"},
    }


def test_render_helpers_escape_content_and_handle_empty_values():
    assert review_exporter.render_list(["<fact>", "evidence"]) == (
        "<ul><li>&lt;fact&gt;</li><li>evidence</li></ul>"
    )
    assert 'class="muted">None</span>' in review_exporter.render_list([])

    sources_html = review_exporter.render_sources(['https://example.com/?q=<x>'])

    assert 'href="https://example.com/?q=&lt;x&gt;"' in sources_html
    assert 'target="_blank" rel="noopener noreferrer"' in sources_html
    assert "&lt;x&gt;" in sources_html
    assert "No source URLs" in review_exporter.render_sources([])


def test_load_json_returns_default_for_missing_path(tmp_path):
    default = {"cards": []}

    assert review_exporter.load_json(tmp_path / "missing.json", default) is default


def test_build_html_includes_card_fact_context_and_review_warnings():
    cards_data = {
        "issue_title": "Weekly <AI>",
        "cards": [
            {
                "slide": 1,
                "type": "cover",
                "visual_type": "abstract",
                "headline": "Cover <Title>",
                "body": ["Safe <Body>"],
                "source_urls": [],
            },
            {
                "slide": 2,
                "type": "news",
                "visual_type": "product",
                "headline": "News headline",
                "body": ["Card body"],
                "source_urls": [],
            },
        ],
    }
    facts = [
        {
            "rank": 1,
            "facts": ["Fact one"],
            "evidence": ["Evidence one"],
            "confidence": 0.64,
        },
        {
            "rank": 2,
            "facts": ["Fact two"],
            "evidence": ["Evidence two"],
            "confidence": 0.91,
            "url": "https://example.com/fact",
        },
    ]

    html = review_exporter.build_html(cards_data, facts)

    assert "&lt;AI&gt;" in html
    assert "&lt;Title&gt;" in html
    assert "&lt;Body&gt;" in html
    assert 'src="01.png"' in html
    assert "slide 1" in html
    assert "cover" in html
    assert "abstract" in html
    assert "Missing news source URLs" in html
    assert "Low confidence fact: 0.64" in html
    assert "Fact one" in html
    assert "Evidence one" in html
