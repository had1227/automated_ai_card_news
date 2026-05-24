from collectors import github_trending_collector as collector


class Response:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("request failed")


def test_fetch_readme_text_tries_common_default_branches(monkeypatch):
    requested_urls = []

    def fake_get(url, headers=None, timeout=None):
        requested_urls.append(url)
        if "/main/" in url:
            return Response("# Demo\n\nDetailed project capabilities.")
        return Response("missing", status_code=404)

    monkeypatch.setattr(collector.requests, "get", fake_get)

    readme = collector.fetch_readme_text("https://github.com/acme/demo")

    assert "Detailed project capabilities." in readme
    assert requested_urls[0].endswith("/HEAD/README.md")
    assert requested_urls[1].endswith("/main/README.md")


def test_collect_github_trending_includes_readme_details(monkeypatch):
    trending_html = """
    <article class="Box-row">
      <h2><a href="/acme/demo"> acme / demo </a></h2>
      <p>Short repo description.</p>
      <a href="/acme/demo/stargazers">1,234</a>
    </article>
    """

    monkeypatch.setattr(collector.requests, "get", lambda *args, **kwargs: Response(trending_html))
    monkeypatch.setattr(
        collector,
        "fetch_readme_text",
        lambda repo_url: "README details explain setup, features, and usage.",
    )

    [item] = collector.collect_github_trending()

    assert item["title"] == "acme/demo"
    assert "Short repo description." in item["text"]
    assert "README details explain setup" in item["text"]
    assert item["metrics"]["stars"] == "1,234"
