from collectors import arxiv_collector as collector


def test_arxiv_pdf_url_from_entry_link_handles_abs_and_pdf_links():
    assert (
        collector.arxiv_pdf_url_from_entry_link("https://arxiv.org/abs/2605.12345v1")
        == "https://arxiv.org/pdf/2605.12345v1"
    )
    assert (
        collector.arxiv_pdf_url_from_entry_link("https://arxiv.org/pdf/2605.12345")
        == "https://arxiv.org/pdf/2605.12345"
    )


def test_collect_arxiv_adds_pdf_excerpt_when_available(monkeypatch):
    class Entry(dict):
        def __init__(self):
            super().__init__(
                published="2026-05-19T00:00:00Z",
                author="Researcher",
            )
            self.title = "Agentic LLM system"
            self.summary = (
                "This paper introduces a language model agent with reasoning, "
                "planning, and multimodal tool use. " * 4
            )
            self.link = "https://arxiv.org/abs/2605.12345"

    class Feed:
        entries = [Entry()]

    monkeypatch.setattr(collector.feedparser, "parse", lambda url: Feed())
    monkeypatch.setattr(collector, "is_within_days", lambda published_at, days: True)
    monkeypatch.setattr(
        collector,
        "fetch_pdf_excerpt",
        lambda pdf_url: "Introduction: detailed method and experiment summary.",
    )

    items = collector.collect_arxiv()

    assert items
    assert "This paper introduces" in items[0]["text"]
    assert "Introduction: detailed method" in items[0]["text"]
