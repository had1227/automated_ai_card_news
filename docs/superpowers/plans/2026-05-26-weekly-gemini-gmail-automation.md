# Weekly Gemini Gmail Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the weekly AI news digest in GitHub Actions every Monday at 08:00 Asia/Seoul, generate Korean article summaries with Gemini API, and send the rendered HTML in the body of a personal Gmail message.

**Architecture:** Keep the root-level pipeline stages, but introduce `llm_client.py` as the single Gemini boundary and `send_email.py` as the Gmail delivery boundary. GitHub Actions executes `run_pipeline.py --all` and then sends `output/news.html`, with Gemini and Gmail credentials supplied only through repository secrets. The existing fact schema evolves to carry Korean headline and paragraph content used by an email-safe renderer.

**Tech Stack:** Python 3.11, `google-genai`, Gemini structured JSON outputs, `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, Gmail API OAuth refresh tokens, GitHub Actions scheduled workflows, pytest.

---

## File Structure

- Modify: `requirements.txt` to add Gemini and Gmail client dependencies.
- Modify: `.gitignore` to exclude local OAuth credentials and tokens.
- Create: `llm_client.py` for Gemini JSON generation and retries.
- Create: `tests/test_llm_client.py` for the provider boundary.
- Modify: `collectors/site_collector.py` to use Gemini for missing-date recency judgments.
- Modify: `tests/test_site_collector.py` to verify the Gemini boundary.
- Modify: `cluster_rank.py` to use Gemini for ranking and duplicate checks.
- Modify: `tests/test_cluster_rank.py` to verify Gemini calls and fallback behavior.
- Modify: `fact_extractor.py` to fetch article prose, call Gemini, and persist Korean email-ready fields.
- Modify: `schemas.py` to validate `korean_title`, `article_body`, and `published_at`.
- Modify: `tests/test_fact_extractor.py` and `tests/test_schemas.py`.
- Modify: `card_exporter.py` to render Gmail-friendly Korean prose HTML.
- Modify: `tests/test_card_exporter.py`.
- Create: `send_email.py` for Gmail API MIME creation and delivery.
- Create: `scripts/gmail_authorize.py` for the one-time personal Gmail authorization flow.
- Create: `tests/test_send_email.py`.
- Create: `.github/workflows/weekly-news-email.yml` for scheduling and manual delivery.
- Create: `docs/weekly-email-setup.md` for Google Cloud, GitHub Secrets, and first-run instructions.

## Dependency Order

Tasks 1-2 establish the provider and credential foundations. Tasks 3-5 replace the local Ollama runtime with Gemini and extend the news artifact. Task 6 renders that artifact as email HTML. Task 7 sends it. Tasks 8-9 install hosted execution and document/verify the operating procedure.

---

### Task 1: Add Hosted API Dependencies And Secret Hygiene

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Add a failing dependency/ignore contract test**

Create `tests/test_automation_configuration.py`:

```python
from pathlib import Path


def test_hosted_automation_dependencies_are_declared():
    dependencies = Path("requirements.txt").read_text(encoding="utf-8").splitlines()

    assert "google-genai" in dependencies
    assert "google-api-python-client" in dependencies
    assert "google-auth-httplib2" in dependencies
    assert "google-auth-oauthlib" in dependencies


def test_local_oauth_files_are_ignored():
    ignore = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert "credentials.json" in ignore
    assert "token.json" in ignore
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/test_automation_configuration.py -v
```

Expected: FAIL because the Google API packages and OAuth ignore entries are not yet present.

- [ ] **Step 3: Add runtime dependencies and ignored local credentials**

Append to `requirements.txt`:

```text
google-genai
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
```

Append to `.gitignore`:

```text
credentials.json
token.json
```

- [ ] **Step 4: Verify the test passes**

Run:

```powershell
python -m pytest tests/test_automation_configuration.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add requirements.txt .gitignore tests/test_automation_configuration.py
git commit -m "chore: add hosted automation dependencies"
```

---

### Task 2: Create A Gemini Structured JSON Client

**Files:**
- Create: `llm_client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Write tests for structured generation, retry, and configuration**

Create `tests/test_llm_client.py`:

```python
import json

import pytest

from llm_client import GeminiJsonClient


class Response:
    def __init__(self, text):
        self.text = text


class Models:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return Response(value)


class Client:
    def __init__(self, responses):
        self.models = Models(responses)


def test_generate_json_requests_gemini_structured_output():
    client = Client(['{"is_recent": true}'])
    schema = {
        "type": "object",
        "properties": {"is_recent": {"type": "boolean"}},
        "required": ["is_recent"],
    }

    result = GeminiJsonClient(client=client, model="gemini-2.5-flash").generate_json(
        "check article",
        schema,
        temperature=0.0,
    )

    assert result == {"is_recent": True}
    call = client.models.calls[0]
    assert call["model"] == "gemini-2.5-flash"
    assert call["contents"] == "check article"
    assert call["config"]["response_mime_type"] == "application/json"
    assert call["config"]["response_json_schema"] == schema


def test_generate_json_retries_transient_generation_failure():
    client = Client([RuntimeError("temporary"), '{"value": 7}'])
    gemini = GeminiJsonClient(client=client, sleep=lambda seconds: None)

    result = gemini.generate_json(
        "retry",
        {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
    )

    assert result == {"value": 7}
    assert len(client.models.calls) == 2


def test_generate_json_fails_after_invalid_json_responses():
    gemini = GeminiJsonClient(
        client=Client(["not json", "still not json", "bad"]),
        sleep=lambda seconds: None,
    )

    with pytest.raises(RuntimeError, match="Gemini JSON generation failed"):
        gemini.generate_json("invalid", {"type": "object"})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_llm_client.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'llm_client'`.

- [ ] **Step 3: Implement the provider boundary**

Create `llm_client.py`:

```python
from __future__ import annotations

import json
import os
import time

from google import genai


DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiJsonClient:
    def __init__(self, client=None, model=None, max_retries=3, sleep=time.sleep):
        self.client = client or genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.max_retries = max_retries
        self.sleep = sleep

    def generate_json(self, prompt, response_schema, temperature=0.1):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": temperature,
                        "response_mime_type": "application/json",
                        "response_json_schema": response_schema,
                    },
                )
                return json.loads(response.text)
            except (ValueError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    self.sleep(2**attempt)

        raise RuntimeError(f"Gemini JSON generation failed: {last_error}") from last_error


def generate_json(prompt, response_schema, temperature=0.1):
    return GeminiJsonClient().generate_json(prompt, response_schema, temperature)
```

- [ ] **Step 4: Verify tests pass**

Run:

```powershell
python -m pytest tests/test_llm_client.py -v
```

Expected: PASS for all three client tests.

- [ ] **Step 5: Commit**

```powershell
git add llm_client.py tests/test_llm_client.py
git commit -m "feat: add Gemini JSON client"
```

---

### Task 3: Replace Site Recency Ollama Calls With Gemini

**Files:**
- Modify: `collectors/site_collector.py`
- Modify: `tests/test_site_collector.py`

- [ ] **Step 1: Replace the recency boundary test with a Gemini expectation**

Add to `tests/test_site_collector.py`:

```python
def test_call_recency_llm_uses_gemini_structured_json(monkeypatch):
    captured = {}

    def fake_generate_json(prompt, response_schema, temperature=0.1):
        captured["prompt"] = prompt
        captured["schema"] = response_schema
        captured["temperature"] = temperature
        return {"is_recent": True, "published_date": "2026-05-24", "confidence": 0.9, "reason": "recent"}

    monkeypatch.setattr(collector, "generate_json", fake_generate_json)

    result = collector.call_recency_llm("New model", "Released on May 24, 2026.")

    assert result["is_recent"] is True
    assert captured["temperature"] == 0.0
    assert "New model" in captured["prompt"]
    assert captured["schema"]["required"] == [
        "is_recent",
        "published_date",
        "confidence",
        "reason",
    ]
```

- [ ] **Step 2: Run the site collector tests to verify the new test fails**

Run:

```powershell
python -m pytest tests/test_site_collector.py -v
```

Expected: FAIL because `collectors.site_collector` does not expose or call `generate_json`.

- [ ] **Step 3: Implement Gemini recency output**

In `collectors/site_collector.py`, remove `json`, `MODEL`, and `OLLAMA_URL` only if no longer used elsewhere in that module. Add:

```python
from llm_client import generate_json


RECENCY_SCHEMA = {
    "type": "object",
    "properties": {
        "is_recent": {"type": "boolean"},
        "published_date": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string"},
    },
    "required": ["is_recent", "published_date", "confidence", "reason"],
}
```

Replace `call_recency_llm` with:

```python
def call_recency_llm(title, text, now=None):
    return generate_json(
        build_recency_prompt(title, text, now=now),
        RECENCY_SCHEMA,
        temperature=0.0,
    )
```

Retain `is_probably_recent_by_llm` as the conservative error boundary: failed or low-confidence judgments retain the article.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_site_collector.py tests/test_collect_validation.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add collectors/site_collector.py tests/test_site_collector.py
git commit -m "feat: use Gemini for site recency filtering"
```

---

### Task 4: Replace Ranking And Deduplication Ollama Calls With Gemini

**Files:**
- Modify: `cluster_rank.py`
- Modify: `tests/test_cluster_rank.py`

- [ ] **Step 1: Write failing tests for the ranking provider boundary**

Replace `tests/test_cluster_rank.py` with:

```python
import cluster_rank


def test_ai_evaluate_cluster_uses_extended_item_text_and_schema(monkeypatch):
    captured = {}

    def fake_generate_json(prompt, response_schema, temperature=0.1):
        captured["prompt"] = prompt
        captured["schema"] = response_schema
        return {"is_ai_news": True}

    monkeypatch.setattr(cluster_rank, "generate_json", fake_generate_json)

    detailed_text = "x" * 250 + "README detail from later in the text"
    result = cluster_rank.ai_evaluate_cluster([{"title": "Repo", "text": detailed_text}])

    assert result == {"is_ai_news": True}
    assert "README detail from later in the text" in captured["prompt"]
    assert "is_card_news_worthy" in captured["schema"]["required"]


def test_ai_is_duplicate_uses_structured_gemini_confidence(monkeypatch):
    monkeypatch.setattr(
        cluster_rank,
        "generate_json",
        lambda prompt, response_schema, temperature=0.1: {
            "is_duplicate": True,
            "confidence": 0.9,
            "reason": "same release",
        },
    )

    assert cluster_rank.ai_is_duplicate(
        {"title": "A", "summary": "one", "category": "release"},
        {"title": "B", "summary": "two", "category": "release"},
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_cluster_rank.py -v
```

Expected: FAIL because `generate_json` is not imported by `cluster_rank.py`.

- [ ] **Step 3: Implement the ranking schemas and Gemini calls**

In `cluster_rank.py`, remove `requests`, `time`, `MODEL`, `OLLAMA_URL`, and `ollama_json`. Add:

```python
from llm_client import generate_json


CLUSTER_EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_ai_news": {"type": "boolean"},
        "is_card_news_worthy": {"type": "boolean"},
        "category": {"type": "string"},
        "importance": {"type": "number", "minimum": 0.0, "maximum": 10.0},
        "trending": {"type": "number", "minimum": 0.0, "maximum": 10.0},
        "novelty": {"type": "number", "minimum": 0.0, "maximum": 10.0},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 10.0},
        "reason": {"type": "string"},
        "one_line_summary": {"type": "string"},
    },
    "required": [
        "is_ai_news",
        "is_card_news_worthy",
        "category",
        "importance",
        "trending",
        "novelty",
        "confidence",
        "reason",
        "one_line_summary",
    ],
}

DUPLICATE_SCHEMA = {
    "type": "object",
    "properties": {
        "is_duplicate": {"type": "boolean"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string"},
    },
    "required": ["is_duplicate", "confidence", "reason"],
}
```

Change the last statement in `ai_evaluate_cluster` to:

```python
    return generate_json(prompt, CLUSTER_EVALUATION_SCHEMA, temperature=0.1)
```

Change the provider call in `ai_is_duplicate` to:

```python
    try:
        data = generate_json(prompt, DUPLICATE_SCHEMA, temperature=0.0)
    except RuntimeError as exc:
        print(f"[WARN] Gemini duplicate check failed - {exc}")
        return False
```

- [ ] **Step 4: Verify ranking tests pass**

Run:

```powershell
python -m pytest tests/test_cluster_rank.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add cluster_rank.py tests/test_cluster_rank.py
git commit -m "feat: use Gemini for news ranking"
```

---

### Task 5: Generate Korean Article-Based Records With Gemini

**Files:**
- Modify: `fact_extractor.py`
- Modify: `schemas.py`
- Modify: `tests/test_fact_extractor.py`
- Modify: `tests/test_schemas.py`

- [ ] **Step 1: Write failing artifact and extractor tests**

Add these fields to `_valid_fact_record` in `tests/test_schemas.py`:

```python
        "korean_title": "새 모델 공개",
        "article_body": ["새 모델이 공개됐다. 개발자는 API를 통해 사용할 수 있다."],
        "published_at": "2026-05-24T00:00:00+00:00",
```

Add to `tests/test_schemas.py`:

```python
def test_validate_fact_record_requires_korean_article_body():
    record = _valid_fact_record(article_body=[])

    with pytest.raises(ValueError, match="article_body"):
        validate_fact_record(record)
```

In `tests/test_fact_extractor.py`, add `import pytest`, import
`extract_fact_record` and `fetch_article_text`, and add:

```python
def test_fetch_article_text_extracts_article_paragraphs(monkeypatch):
    class Response:
        text = """
        <html><body>
          <script>ignore this</script>
          <article>
            <p>A new Gemini model was released with API availability for developers.</p>
            <p>The announcement describes pricing and supported context limits.</p>
          </article>
        </body></html>
        """

        def raise_for_status(self):
            return None

    monkeypatch.setattr(
        "fact_extractor.requests.get",
        lambda url, headers=None, timeout=None: Response(),
    )

    text = fetch_article_text("https://example.com/story")

    assert "Gemini model was released" in text
    assert "pricing and supported context limits" in text
    assert "ignore this" not in text


def test_build_prompt_includes_fetched_article_and_requests_korean_body(monkeypatch):
    monkeypatch.setattr(
        "fact_extractor.fetch_article_text",
        lambda url: "Full linked article content.",
    )
    item = {
        "title": "Model release",
        "summary": "Summary",
        "reason": "Reason",
        "url": "https://example.com/story",
        "category": "release",
        "cluster": [],
    }

    prompt = build_prompt(1, item)

    assert "Full linked article content." in prompt
    assert "korean_title" in prompt
    assert "article_body" in prompt


def test_fallback_record_propagates_cluster_publication_date():
    record = fallback_record(
        1,
        {
            "title": "Article",
            "summary": "Summary",
            "url": "https://example.com/story",
            "cluster": [{"published_at": "2026-05-24T03:00:00+00:00"}],
        },
    )

    assert record["published_at"] == "2026-05-24T03:00:00+00:00"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_schemas.py tests/test_fact_extractor.py -v
```

Expected: FAIL because the schema and extractor do not yet carry the email-ready Korean fields or article fetch.

- [ ] **Step 3: Extend the artifact schema**

In `schemas.py`, add required record fields:

```python
        "korean_title",
        "article_body",
        "published_at",
```

After the existing title/url checks, add:

```python
    _require_non_empty_text(record, "korean_title", "fact_record")
    article_body = _require_list(record, "article_body", "fact_record")
    if not article_body or not all(
        isinstance(paragraph, str) and paragraph.strip() for paragraph in article_body
    ):
        raise ValueError("fact_record.article_body must contain non-empty paragraphs")
```

- [ ] **Step 4: Add article fetching and Gemini article schema**

In `fact_extractor.py`, import:

```python
from bs4 import BeautifulSoup

from llm_client import generate_json
```

Add:

```python
MAX_ARTICLE_TEXT_CHARS = 5000
ARTICLE_SCHEMA = {
    "type": "object",
    "properties": {
        "rank": {"type": "integer"},
        "title": {"type": "string"},
        "korean_title": {"type": "string"},
        "url": {"type": "string"},
        "source_domain": {"type": "string"},
        "category": {"type": "string"},
        "summary": {"type": "string"},
        "article_body": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 4,
        },
        "facts": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "evidence": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "entities": {"type": "array", "items": {"type": "string"}},
        "numbers": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "published_at": {"type": "string"},
    },
    "required": [
        "rank",
        "title",
        "korean_title",
        "url",
        "source_domain",
        "category",
        "summary",
        "article_body",
        "facts",
        "evidence",
        "entities",
        "numbers",
        "confidence",
        "published_at",
    ],
}


def fetch_article_text(url):
    if not str(url or "").startswith(("http://", "https://")):
        return ""
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[WARN] article fetch failed: {url} - {exc}")
        return ""
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    paragraphs = [
        _clean_text(tag.get_text(" ", strip=True))
        for tag in soup.find_all("p")
        if len(_clean_text(tag.get_text(" ", strip=True))) >= 40
    ]
    return "\n".join(paragraphs)[:MAX_ARTICLE_TEXT_CHARS]
```

Add this helper before `fallback_record`:

```python
def _first_published_at(item):
    top_level = _clean_text(item.get("published_at", ""))
    if top_level:
        return top_level
    for entry in _cluster_entries(item):
        value = _clean_text(entry.get("published_at", ""))
        if value:
            return value
    return ""
```

Inside `fallback_record`, set `published_at = _first_published_at(item)` next
to `cluster_text`, then add these properties to its `record` dictionary:

```python
        "korean_title": title,
        "article_body": [summary or fact],
        "published_at": published_at,
```

Update `build_prompt` to add `article_text = fetch_article_text(fallback["url"])` to source material and require Korean `korean_title`, Korean `summary`, and `article_body` paragraphs without unsupported claims.

Update `normalize_record`:

```python
    record["korean_title"] = _clean_text(record.get("korean_title")) or fallback["korean_title"]
    record["article_body"] = _as_text_list(record.get("article_body"), fallback["article_body"])
    record["published_at"] = _clean_text(record.get("published_at")) or fallback["published_at"]
```

Replace the provider call in `extract_fact_record` with:

```python
    data = generate_json(prompt, ARTICLE_SCHEMA, temperature=0.1)
```

Remove the per-record exception fallback in `main`: failures from
`extract_fact_record` must stop the stage so a workflow never emails an
untranslated fallback record. The article HTTP fetch fallback above still
permits Gemini to write a conservative Korean brief from collected snippets.

Add to `tests/test_fact_extractor.py`:

```python
def test_extract_fact_record_propagates_generation_failure(monkeypatch):
    monkeypatch.setattr(
        "fact_extractor.generate_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Gemini unavailable")),
    )
    monkeypatch.setattr("fact_extractor.fetch_article_text", lambda url: "")

    with pytest.raises(RuntimeError, match="Gemini unavailable"):
        extract_fact_record(
            1,
            {
                "title": "Article",
                "summary": "Summary",
                "url": "https://example.com/story",
                "category": "release",
                "cluster": [],
            },
        )
```

- [ ] **Step 5: Verify extractor and schema tests pass**

Run:

```powershell
python -m pytest tests/test_schemas.py tests/test_fact_extractor.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add fact_extractor.py schemas.py tests/test_fact_extractor.py tests/test_schemas.py
git commit -m "feat: generate Korean article brief records"
```

---

### Task 6: Render An Email-Safe Korean HTML Digest

**Files:**
- Modify: `card_exporter.py`
- Modify: `tests/test_card_exporter.py`

- [ ] **Step 1: Write the final email presentation contract**

Replace `tests/test_card_exporter.py` with:

```python
import card_exporter


def test_build_html_renders_korean_email_digest_without_internal_metadata():
    records = [
        {
            "rank": 1,
            "title": "Open model ships",
            "korean_title": "오픈 모델 출시",
            "summary": "한국어 요약",
            "article_body": [
                "한 연구소가 새 오픈 모델을 공개했고 개발자는 API에서 사용할 수 있다.",
                "공식 발표는 가격 정책과 지원 범위를 함께 제시했다.",
            ],
            "facts": ["compatibility fact"],
            "evidence": ["compatibility evidence"],
            "url": "https://example.com/model?ref=<ai>",
            "source_domain": "example.com",
            "category": "model_release",
            "confidence": 0.86,
            "published_at": "2026-05-24T09:00:00+09:00",
        }
    ]

    html = card_exporter.build_html(records)

    assert "<title>이번 주 AI 핵심 뉴스</title>" in html
    assert "<h1" in html and "이번 주 AI 핵심 뉴스" in html
    assert "2026.05.24 - 2026.05.24" in html
    assert "오픈 모델 출시" in html
    assert "<h2" in html and "<h2><a " not in html
    assert "한 연구소가 새 오픈 모델을 공개했고" in html
    assert "model_release" not in html
    assert "confidence" not in html
    assert "핵심 사실" not in html
    assert "근거" not in html
    assert 'href="https://example.com/model?ref=&amp;&lt;ai&gt;"' in html
    assert "font-size:32px" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_card_exporter.py -v
```

Expected: FAIL because the current renderer links headlines and exposes facts/evidence layout instead of Korean paragraph-only email HTML.

- [ ] **Step 3: Implement the email HTML contract**

In `card_exporter.py`:

- Import `dateutil.parser` for record date parsing.
- Add `date_range_label(records)` which returns `YYYY.MM.DD - YYYY.MM.DD`.
- Render `korean_title` as escaped `<h2>` text with no hyperlink.
- Render `article_body` entries as paragraphs.
- Keep a separate escaped source hyperlink.
- Replace the page title and black main heading with `이번 주 AI 핵심 뉴스`.
- Remove category, confidence, facts, and evidence output.
- Use inline heading styles, including `font-size:32px`, so Gmail preserves headline visibility.

The central record renderer must have this structure:

```python
def render_record(record, fallback_rank):
    rank = display_rank(record.get("rank"), fallback_rank)
    title = escape_text(record.get("korean_title") or record.get("title") or "제목 없음")
    paragraphs = record.get("article_body") or [record.get("summary", "")]
    body_html = "".join(
        f'<p style="margin:12px 0 0;font-size:17px;line-height:1.7;">'
        f"{escape_text(paragraph)}</p>"
        for paragraph in paragraphs
        if str(paragraph or "").strip()
    )
    return f"""
    <article style="padding:34px 0;border-bottom:1px solid #ded8ce;">
      <p style="margin:0 0 12px;color:#b85f42;font-weight:700;">{rank}</p>
      <h2 style="margin:0 0 10px;font-size:32px;line-height:1.3;color:#171717;">{title}</h2>
      {body_html}
      {render_sources(record)}
    </article>
    """
```

- [ ] **Step 4: Verify renderer tests pass**

Run:

```powershell
python -m pytest tests/test_card_exporter.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add card_exporter.py tests/test_card_exporter.py
git commit -m "feat: render Gmail-ready Korean digest HTML"
```

---

### Task 7: Send The HTML Digest Through Personal Gmail OAuth

**Files:**
- Create: `send_email.py`
- Create: `scripts/gmail_authorize.py`
- Create: `tests/test_send_email.py`

- [ ] **Step 1: Write failing Gmail message and delivery tests**

Create `tests/test_send_email.py`:

```python
import base64
from email import message_from_bytes

import send_email


def test_build_message_contains_html_digest_and_utf8_subject():
    raw = send_email.build_message(
        "sender@gmail.com",
        "reader@gmail.com",
        "[이번 주 AI 핵심 뉴스] 2026.05.18 - 2026.05.24",
        "<h1>이번 주 AI 핵심 뉴스</h1>",
    )
    decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
    message = message_from_bytes(decoded)

    assert message["From"] == "sender@gmail.com"
    assert message["To"] == "reader@gmail.com"
    assert "이번 주 AI 핵심 뉴스" in str(message["Subject"])
    assert "text/html" in message.as_string()


def test_send_digest_calls_gmail_messages_send():
    calls = {}

    class Request:
        def execute(self):
            return {"id": "message-123"}

    class Messages:
        def send(self, userId, body):
            calls["userId"] = userId
            calls["body"] = body
            return Request()

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    result = send_email.send_digest(
        Service(),
        "sender@gmail.com",
        "reader@gmail.com",
        "subject",
        "<p>body</p>",
    )

    assert result == {"id": "message-123"}
    assert calls["userId"] == "me"
    assert "raw" in calls["body"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_send_email.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'send_email'`.

- [ ] **Step 3: Implement Gmail delivery**

Create `send_email.py`:

```python
from __future__ import annotations

import base64
import os
from email.message import EmailMessage
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from card_exporter import date_range_label, load_records


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
HTML_PATH = Path("output/news.html")


def build_message(sender, recipient, subject, html_body):
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content("HTML 메일을 표시할 수 있는 메일 클라이언트에서 확인해 주세요.")
    message.add_alternative(html_body, subtype="html")
    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def create_gmail_service():
    credentials = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def send_digest(service, sender, recipient, subject, html_body):
    raw = build_message(sender, recipient, subject, html_body)
    return service.users().messages().send(userId="me", body={"raw": raw}).execute()


def main():
    sender = os.environ["MAIL_FROM"]
    recipient = os.environ["MAIL_TO"]
    records = load_records()
    date_range = date_range_label(records)
    subject = f"[이번 주 AI 핵심 뉴스] {date_range}"
    html_body = HTML_PATH.read_text(encoding="utf-8")
    result = send_digest(
        create_gmail_service(),
        sender,
        recipient,
        subject,
        html_body,
    )
    print(f"sent weekly digest: {result.get('id', 'unknown')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Implement the one-time OAuth authorization script**

Create `scripts/gmail_authorize.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CLIENT_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")


def main():
    if not CLIENT_FILE.exists():
        raise SystemExit("Place the downloaded OAuth desktop credential at credentials.json.")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
    token_data = json.loads(credentials.to_json())
    print("GMAIL_CLIENT_ID=" + token_data["client_id"])
    print("GMAIL_CLIENT_SECRET=" + token_data["client_secret"])
    print("GMAIL_REFRESH_TOKEN=" + token_data["refresh_token"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Verify Gmail tests pass**

Run:

```powershell
python -m pytest tests/test_send_email.py -v
```

Expected: PASS without contacting Gmail.

- [ ] **Step 6: Commit**

```powershell
git add send_email.py scripts/gmail_authorize.py tests/test_send_email.py
git commit -m "feat: send weekly digest through Gmail API"
```

---

### Task 8: Add Scheduled GitHub Actions Execution

**Files:**
- Create: `.github/workflows/weekly-news-email.yml`
- Modify: `tests/test_automation_configuration.py`

- [ ] **Step 1: Write a workflow configuration test**

Append to `tests/test_automation_configuration.py`:

```python
def test_weekly_workflow_runs_pipeline_and_sends_html_email():
    workflow = Path(".github/workflows/weekly-news-email.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "cron: '0 8 * * 1'" in workflow
    assert "timezone: 'Asia/Seoul'" in workflow
    assert "python run_pipeline.py --all" in workflow
    assert "python send_email.py" in workflow
    assert "GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}" in workflow
    assert "GMAIL_REFRESH_TOKEN: ${{ secrets.GMAIL_REFRESH_TOKEN }}" in workflow
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
python -m pytest tests/test_automation_configuration.py -v
```

Expected: FAIL because the workflow does not exist.

- [ ] **Step 3: Create the scheduled workflow**

Create `.github/workflows/weekly-news-email.yml`:

```yaml
name: Weekly AI news email

on:
  workflow_dispatch:
  schedule:
    - cron: '0 8 * * 1'
      timezone: 'Asia/Seoul'

jobs:
  send-weekly-digest:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    env:
      GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      GEMINI_MODEL: gemini-2.5-flash
      GMAIL_CLIENT_ID: ${{ secrets.GMAIL_CLIENT_ID }}
      GMAIL_CLIENT_SECRET: ${{ secrets.GMAIL_CLIENT_SECRET }}
      GMAIL_REFRESH_TOKEN: ${{ secrets.GMAIL_REFRESH_TOKEN }}
      MAIL_FROM: ${{ secrets.MAIL_FROM }}
      MAIL_TO: ${{ secrets.MAIL_TO }}
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt
          python -m playwright install --with-deps chromium

      - name: Run tests
        run: python -m pytest -q

      - name: Build weekly news HTML
        run: python run_pipeline.py --all

      - name: Send Gmail digest
        run: python send_email.py

      - name: Upload generated diagnostics
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: weekly-news-output-${{ github.run_id }}
          path: |
            data/items.json
            data/top_news.json
            data/news_facts.json
            output/news.html
          if-no-files-found: warn
          retention-days: 7
```

- [ ] **Step 4: Verify workflow contract tests pass**

Run:

```powershell
python -m pytest tests/test_automation_configuration.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add .github/workflows/weekly-news-email.yml tests/test_automation_configuration.py
git commit -m "ci: schedule weekly AI news email"
```

---

### Task 9: Document Setup And Validate The Full Hosted Path

**Files:**
- Create: `docs/weekly-email-setup.md`

- [ ] **Step 1: Write the operations guide**

Create `docs/weekly-email-setup.md`:

```markdown
# Weekly Email Setup

## Google Services

1. Create or select a Google Cloud project.
2. Enable the Gmail API.
3. Create a Gemini API key in Google AI Studio.
4. Configure an External OAuth consent screen and add the sender Gmail account as a test user while the app remains in testing mode.
5. Create an OAuth client of type Desktop app and download it as `credentials.json` in the repository root.

## Obtain Gmail Send Authorization

Install dependencies and perform the one-time authorization from a trusted local machine:

```powershell
python -m pip install -r requirements.txt
python scripts/gmail_authorize.py
```

Sign into the Gmail account that should send the digest and approve only Gmail send access. Copy the printed client ID, client secret, and refresh token into GitHub repository secrets. Delete local `credentials.json` and `token.json` after the secrets have been registered.

## GitHub Repository Secrets

Create these Actions secrets under repository Settings > Secrets and variables > Actions:

| Secret | Value |
| --- | --- |
| `GEMINI_API_KEY` | Gemini API key |
| `GMAIL_CLIENT_ID` | Value printed by authorization script |
| `GMAIL_CLIENT_SECRET` | Value printed by authorization script |
| `GMAIL_REFRESH_TOKEN` | Value printed by authorization script |
| `MAIL_FROM` | Authorized sender Gmail address |
| `MAIL_TO` | Recipient Gmail address |

## First Delivery

1. Open Actions > Weekly AI news email.
2. Choose Run workflow.
3. Confirm the run completes successfully.
4. Open the received email and confirm Korean titles, article paragraphs, source links, and the issue date range are readable.
5. Keep the schedule enabled for Monday 08:00 Asia/Seoul delivery.

## Failure Recovery

- Open the failed Actions run and inspect the failing pipeline step.
- If content generation failed transiently, rerun the workflow.
- If Gmail authorization fails, run `python scripts/gmail_authorize.py` again and replace the three Gmail OAuth secrets.
- Generated JSON and HTML diagnostics remain attached to each workflow run for seven days.
```

- [ ] **Step 2: Run all unit tests in a provisioned Python environment**

Run:

```powershell
python -m pytest -q
```

Expected: all tests PASS.

- [ ] **Step 3: Run a local dry generation when API credentials are available**

Run:

```powershell
# Run this after GEMINI_API_KEY has been loaded into this local shell securely.
python run_pipeline.py --all
```

Expected: `output/news.html` exists and contains `이번 주 AI 핵심 뉴스`, a weekly date range, and Korean article paragraphs.

- [ ] **Step 4: Commit the operations guide**

```powershell
git add docs/weekly-email-setup.md
git commit -m "docs: add weekly email setup guide"
```

- [ ] **Step 5: Manually validate hosted delivery**

After pushing the implementation branch and registering secrets, use GitHub Actions `workflow_dispatch`.

Expected:

- The test, pipeline, send, and artifact-upload steps complete.
- The configured personal Gmail account sends one message with subject prefix `[이번 주 AI 핵심 뉴스]`.
- The recipient reads the digest directly in the email body.

---

## Final Verification Checklist

- [ ] `rg "OLLAMA_URL|gemma4:e4b|ollama_json|call_ollama" cluster_rank.py fact_extractor.py collectors/site_collector.py` produces no matches.
- [ ] `python -m pytest -q` passes in the GitHub Actions Python environment.
- [ ] GitHub Actions manual run completes with generated artifacts attached.
- [ ] The received Gmail body shows Korean article paragraphs and source links, with no category or confidence metadata.
- [ ] The scheduled workflow is configured for Monday 08:00 `Asia/Seoul`.
- [ ] No OAuth credential files, refresh tokens, or API keys are tracked by Git.

## Primary References

- Gemini structured outputs: <https://ai.google.dev/gemini-api/docs/structured-output>
- Gmail Python quickstart and OAuth libraries: <https://developers.google.com/workspace/gmail/api/quickstart/python>
- Gmail MIME sending flow: <https://developers.google.com/gmail/api/guides/sending>
- GitHub Actions schedule syntax: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule>
