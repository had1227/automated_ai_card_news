# AI News Agent Extended MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an extended MVP that runs the AI-news pipeline end to end, validates artifacts, extracts evidence-backed facts, renders richer card layouts, and exports a review page.

**Architecture:** Keep the current root-level scripts as pipeline stages and add focused helper modules beside them. `run_pipeline.py` orchestrates stages, `schemas.py` validates JSON artifacts, `source_utils.py` handles URL/source quality utilities, `fact_extractor.py` creates `data/news_facts.json`, and `review_exporter.py` creates `output/review.html`.

**Tech Stack:** Python 3, pathlib, json, argparse, requests, BeautifulSoup, Playwright, sentence-transformers, Ollama HTTP API, Pillow, pytest.

---

## File Structure

- Modify: `requirements.txt` to include missing runtime and test dependencies.
- Create: `schemas.py` for artifact validation.
- Create: `source_utils.py` for URL/domain normalization, source type, and history pruning helpers.
- Create: `run_pipeline.py` for orchestrating pipeline stages.
- Create: `fact_extractor.py` for fact extraction and conservative fallback facts.
- Modify: `card_writer.py` so it prefers `data/news_facts.json`.
- Modify: `card_renderer.py` so `visual_type` changes the rendered layout and invalid input fails clearly.
- Create: `review_exporter.py` for internal review HTML.
- Create: `tests/test_schemas.py`.
- Create: `tests/test_source_utils.py`.
- Create: `tests/test_card_writer_normalization.py`.
- Create: `tests/test_renderer_validation.py`.

---

### Task 1: Runtime Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Update dependencies**

Replace `requirements.txt` with:

```text
requests
beautifulsoup4
feedparser
PyYAML
python-dateutil
playwright
ddgs
openai
python-dotenv
tqdm
numpy
sentence-transformers
Pillow
pytest
```

- [ ] **Step 2: Verify dependency file**

Run:

```powershell
Get-Content requirements.txt
```

Expected: the file includes `numpy`, `sentence-transformers`, `Pillow`, and `pytest`.

- [ ] **Step 3: Commit**

```powershell
git add requirements.txt
git commit -m "chore: add extended pipeline dependencies"
```

---

### Task 2: Add Schema Validation Module

**Files:**
- Create: `schemas.py`
- Test: `tests/test_schemas.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_schemas.py`:

```python
import pytest

from schemas import (
    validate_cards,
    validate_fact_record,
    validate_item,
    validate_top_news_item,
)


def test_validate_item_accepts_minimal_valid_item():
    item = {
        "platform": "rss",
        "collection_mode": "source",
        "source_account": "OpenAI",
        "title": "New model",
        "text": "OpenAI announced a new model.",
        "url": "https://example.com/news",
        "published_at": "2026-05-09T00:00:00+00:00",
        "metrics": {},
        "media_urls": [],
    }

    validate_item(item)


def test_validate_item_rejects_missing_title():
    item = {"url": "https://example.com/news"}

    with pytest.raises(ValueError, match="title"):
        validate_item(item)


def test_validate_top_news_item_accepts_ranked_item():
    item = {
        "score": 91.0,
        "title": "Model release",
        "summary": "A model was released.",
        "reason": "Official announcement.",
        "category": "model_release",
        "url": "https://example.com/news",
        "source_count": 1,
        "cluster": [],
    }

    validate_top_news_item(item)


def test_validate_fact_record_requires_evidence():
    record = {
        "rank": 1,
        "title": "Model release",
        "url": "https://example.com/news",
        "source_domain": "example.com",
        "category": "model_release",
        "summary": "A model was released.",
        "facts": ["A model was released."],
        "evidence": [],
        "entities": ["Example AI"],
        "numbers": [],
        "confidence": 0.8,
    }

    with pytest.raises(ValueError, match="evidence"):
        validate_fact_record(record)


def test_validate_cards_accepts_valid_cards():
    data = {
        "issue_title": "Weekly AI News",
        "issue_summary": "Top AI stories.",
        "target_reader": "AI engineers",
        "cards": [
            {
                "slide": 1,
                "type": "cover",
                "headline": "WEEKLY AI NEWS",
                "body": ["2026.05.03 - 2026.05.09", "이번 주 AI 톱뉴스"],
                "image_hint": "abstract network",
                "visual_type": "abstract",
                "source_urls": [],
            },
            {
                "slide": 2,
                "type": "news",
                "headline": "새 모델 공개",
                "body": ["핵심 요약", "근거 있는 설명"],
                "image_hint": "model diagram",
                "visual_type": "diagram",
                "source_urls": ["https://example.com/news"],
            },
        ],
    }

    validate_cards(data)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/test_schemas.py -v
```

Expected: FAIL because `schemas.py` does not exist.

- [ ] **Step 3: Implement `schemas.py`**

Create `schemas.py`:

```python
from __future__ import annotations


VALID_VISUAL_TYPES = {"diagram", "chart", "timeline", "comparison", "abstract"}
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
        float(item["score"])
    except (TypeError, ValueError) as exc:
        raise ValueError("top_news_item.score must be numeric") from exc
    _require_list(item, "cluster", "top_news_item")


def validate_fact_record(record):
    required = [
        "rank",
        "title",
        "url",
        "source_domain",
        "category",
        "summary",
        "facts",
        "evidence",
        "entities",
        "numbers",
        "confidence",
    ]
    _require_fields(record, required, "fact_record")
    _require_non_empty_text(record, "title", "fact_record")
    _require_non_empty_text(record, "url", "fact_record")
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
        if card["visual_type"] not in VALID_VISUAL_TYPES:
            raise ValueError(f"{label}.visual_type is invalid: {card['visual_type']}")
        _require_non_empty_text(card, "headline", label)
        body = _require_list(card, "body", label)
        if not all(isinstance(line, str) for line in body):
            raise ValueError(f"{label}.body must contain only text")
        source_urls = _require_list(card, "source_urls", label)
        if card["type"] == "news" and not source_urls:
            raise ValueError(f"{label}.source_urls must not be empty for news cards")
```

- [ ] **Step 4: Run schema tests**

Run:

```powershell
python -m pytest tests/test_schemas.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add schemas.py tests/test_schemas.py
git commit -m "feat: add artifact schema validation"
```

---

### Task 3: Add Source Utility Module

**Files:**
- Create: `source_utils.py`
- Test: `tests/test_source_utils.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_source_utils.py`:

```python
from datetime import datetime, timedelta, timezone

from source_utils import (
    classify_source,
    clean_domain,
    is_google_news_url,
    prune_history,
    source_trust_score,
)


def test_clean_domain_removes_www_and_lowercases():
    assert clean_domain("https://www.OpenAI.com/news/") == "openai.com"


def test_is_google_news_url_detects_rss_article():
    url = "https://news.google.com/rss/articles/abc?oc=5"
    assert is_google_news_url(url)


def test_classify_source_detects_official_source():
    assert classify_source("https://openai.com/news/") == "official"


def test_classify_source_detects_code_source():
    assert classify_source("https://github.com/openai/example") == "code"


def test_source_trust_score_prefers_official():
    official = source_trust_score("https://anthropic.com/news")
    media = source_trust_score("https://example-news.com/article")
    assert official > media


def test_prune_history_keeps_recent_items_and_limits_count():
    now = datetime(2026, 5, 9, tzinfo=timezone.utc)
    recent = {
        "title": "recent",
        "published_at": (now - timedelta(days=1)).isoformat(),
    }
    old = {
        "title": "old",
        "published_at": (now - timedelta(days=90)).isoformat(),
    }

    assert prune_history([old, recent], keep_days=30, max_items=10, now=now) == [recent]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
python -m pytest tests/test_source_utils.py -v
```

Expected: FAIL because `source_utils.py` does not exist.

- [ ] **Step 3: Implement `source_utils.py`**

Create `source_utils.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from dateutil import parser as date_parser


OFFICIAL_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "blog.google",
    "huggingface.co",
    "mistral.ai",
    "nvidia.com",
    "developer.nvidia.com",
    "research.nvidia.com",
    "moonshot.cn",
    "zhipuai.cn",
    "deepseek.com",
    "qwenlm.github.io",
}

RESEARCH_DOMAINS = {"arxiv.org", "export.arxiv.org", "paperswithcode.com"}
CODE_DOMAINS = {"github.com", "huggingface.co"}
SOCIAL_DOMAINS = {"x.com", "twitter.com", "threads.net"}


def clean_domain(url):
    if not url:
        return ""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    return domain.lower().replace("www.", "")


def is_google_news_url(url):
    return clean_domain(url) == "news.google.com"


def classify_source(url):
    domain = clean_domain(url)
    if domain in OFFICIAL_DOMAINS:
        return "official"
    if domain in RESEARCH_DOMAINS:
        return "research"
    if domain in CODE_DOMAINS:
        return "code"
    if domain in SOCIAL_DOMAINS:
        return "social"
    return "media"


def source_trust_score(url):
    source_type = classify_source(url)
    scores = {
        "official": 1.0,
        "research": 0.9,
        "code": 0.8,
        "media": 0.65,
        "social": 0.55,
    }
    return scores[source_type]


def parse_datetime(value):
    if not value:
        return None
    try:
        dt = date_parser.parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def prune_history(items, keep_days=45, max_items=5000, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=keep_days)

    kept = []
    for item in items:
        published_at = parse_datetime(item.get("published_at"))
        if published_at is None or published_at >= cutoff:
            kept.append(item)

    return kept[-max_items:]
```

- [ ] **Step 4: Run source utility tests**

Run:

```powershell
python -m pytest tests/test_source_utils.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add source_utils.py tests/test_source_utils.py
git commit -m "feat: add source quality utilities"
```

---

### Task 4: Add Pipeline Orchestrator

**Files:**
- Create: `run_pipeline.py`
- Modify: `collect.py`

- [ ] **Step 1: Implement `run_pipeline.py`**

Create `run_pipeline.py`:

```python
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from schemas import validate_cards, validate_fact_record, validate_item, validate_top_news_item


STAGES = {
    "collect": ["collect.py"],
    "rank": ["cluster_rank.py"],
    "facts": ["fact_extractor.py"],
    "write": ["card_writer.py"],
    "render": ["card_renderer.py"],
    "export": ["card_exporter.py"],
    "review": ["review_exporter.py"],
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_script(script):
    print(f"\n[RUN] python {script}")
    result = subprocess.run([sys.executable, script], check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def validate_stage(stage):
    if stage == "collect":
        items = load_json("data/items.json")
        for item in items:
            validate_item(item)
        print(f"[OK] validated {len(items)} collected items")
    elif stage == "rank":
        news = load_json("data/top_news.json")
        for item in news:
            validate_top_news_item(item)
        print(f"[OK] validated {len(news)} ranked news items")
    elif stage == "facts":
        facts = load_json("data/news_facts.json")
        for record in facts:
            validate_fact_record(record)
        print(f"[OK] validated {len(facts)} fact records")
    elif stage == "write":
        cards = load_json("data/cards.json")
        validate_cards(cards)
        print(f"[OK] validated {len(cards.get('cards', []))} cards")


def selected_stages(args):
    if args.all:
        return ["collect", "rank", "facts", "write", "render", "export", "review"]
    if args.render_only:
        return ["render", "export", "review"]
    stages = []
    for name in STAGES:
        if getattr(args, name):
            stages.append(name)
    return stages


def main():
    parser = argparse.ArgumentParser(description="Run the AI news card pipeline.")
    parser.add_argument("--all", action="store_true", help="Run every stage.")
    parser.add_argument("--render-only", action="store_true", help="Regenerate outputs from cards.json.")
    for stage in STAGES:
        parser.add_argument(f"--{stage}", action="store_true", help=f"Run {stage} stage.")

    args = parser.parse_args()
    stages = selected_stages(args)
    if not stages:
        parser.error("Select at least one stage, --all, or --render-only.")

    for stage in stages:
        run_script(STAGES[stage][0])
        validate_stage(stage)

    print("\n[DONE] pipeline stages completed:")
    for stage in stages:
        print(f"- {stage}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Modify `collect.py` to prune history**

In `collect.py`, add this import near the other imports:

```python
from source_utils import prune_history
```

Replace:

```python
updated_history = history_items + new_items
save_json(HISTORY_PATH, updated_history)
```

with:

```python
updated_history = prune_history(history_items + new_items)
save_json(HISTORY_PATH, updated_history)
```

- [ ] **Step 3: Run orchestrator help**

Run:

```powershell
python run_pipeline.py --help
```

Expected: usage text includes `--all`, `--render-only`, and each stage flag.

- [ ] **Step 4: Run render-only smoke command**

Run:

```powershell
python run_pipeline.py --render-only
```

Expected: PNG cards, `output/cards.html`, and later `output/review.html` are generated once `review_exporter.py` exists. Before Task 9, this command may fail at the `review` stage; use `python run_pipeline.py --render --export` until Task 9 is complete.

- [ ] **Step 5: Commit**

```powershell
git add run_pipeline.py collect.py
git commit -m "feat: add pipeline orchestrator"
```

---

### Task 5: Add Fact Extraction Stage

**Files:**
- Create: `fact_extractor.py`

- [ ] **Step 1: Implement `fact_extractor.py`**

Create `fact_extractor.py`:

```python
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from schemas import validate_fact_record
from source_utils import clean_domain


INPUT_PATH = Path("data/top_news.json")
OUTPUT_PATH = Path("data/news_facts.json")
MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/generate"
MAX_CLUSTER_TEXT_CHARS = 2800


def load_top_news():
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def save_facts(records):
    OUTPUT_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def compact_cluster_text(item):
    parts = []
    for raw in item.get("cluster", [])[:4]:
        title = raw.get("title", "")
        text = re.sub(r"\s+", " ", raw.get("text", ""))
        parts.append(f"제목: {title}\n본문: {text[:900]}")
    return "\n\n".join(parts)[:MAX_CLUSTER_TEXT_CHARS]


def fallback_record(rank, item):
    evidence_text = item.get("summary") or item.get("reason") or item.get("title")
    return {
        "rank": rank,
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "source_domain": clean_domain(item.get("url", "")),
        "category": item.get("category", "unknown"),
        "summary": item.get("summary", ""),
        "facts": [item.get("summary") or item.get("title", "")],
        "evidence": [evidence_text],
        "entities": [],
        "numbers": [],
        "confidence": 0.55,
    }


def call_ollama(prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            res = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
                timeout=180,
            )
            res.raise_for_status()
            return json.loads(res.json()["response"])
        except Exception as exc:
            if attempt >= max_retries:
                print(f"[WARN] fact extraction failed: {exc}")
                return None
            time.sleep(1.5 * (attempt + 1))


def build_prompt(rank, item):
    source_text = compact_cluster_text(item)
    return f"""
너는 AI 뉴스 팩트체커다. 아래 뉴스 정보에서 카드뉴스에 사용할 수 있는 검증 가능한 사실만 추출하라.
추측, 전망, 과장 표현은 금지한다. 입력에 없는 숫자, 날짜, 성능, 가격을 만들지 마라.

반드시 JSON만 출력하라.

{{
  "rank": {rank},
  "title": "{item.get('title', '')}",
  "url": "{item.get('url', '')}",
  "source_domain": "{clean_domain(item.get('url', ''))}",
  "category": "{item.get('category', 'unknown')}",
  "summary": "짧은 요약",
  "facts": ["근거 있는 사실 1", "근거 있는 사실 2"],
  "evidence": ["입력 텍스트에서 가져온 근거 문장 또는 짧은 구절"],
  "entities": ["회사/모델/제품명"],
  "numbers": ["입력에 실제로 있는 숫자 정보"],
  "confidence": 0.0
}}

뉴스 요약:
{item.get('summary', '')}

선정 이유:
{item.get('reason', '')}

소스 텍스트:
{source_text}
""".strip()


def normalize_record(rank, item, data):
    if not isinstance(data, dict):
        return fallback_record(rank, item)
    record = fallback_record(rank, item)
    for key in record:
        if key in data:
            record[key] = data[key]
    record["rank"] = rank
    record["url"] = item.get("url", record.get("url", ""))
    record["source_domain"] = clean_domain(record["url"])
    if isinstance(record.get("confidence"), (int, float)):
        record["confidence"] = max(0.0, min(1.0, float(record["confidence"])))
    else:
        record["confidence"] = 0.55
    return record


def extract_fact_record(rank, item):
    data = call_ollama(build_prompt(rank, item))
    record = normalize_record(rank, item, data)
    validate_fact_record(record)
    return record


def main():
    top_news = load_top_news()
    records = []
    for rank, item in enumerate(top_news, start=1):
        try:
            record = extract_fact_record(rank, item)
        except Exception as exc:
            print(f"[WARN] using fallback facts for rank {rank}: {exc}")
            record = fallback_record(rank, item)
            validate_fact_record(record)
        records.append(record)

    save_facts(records)
    print(f"saved fact records: {OUTPUT_PATH} ({len(records)})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run fact extraction on existing ranked news**

Run:

```powershell
python fact_extractor.py
```

Expected: `data/news_facts.json` exists and contains one record per top-news item.

- [ ] **Step 3: Validate facts through orchestrator**

Run:

```powershell
python run_pipeline.py --facts
```

Expected: fact extraction runs and validation prints `[OK] validated ... fact records`.

- [ ] **Step 4: Commit**

```powershell
git add fact_extractor.py data/news_facts.json
git commit -m "feat: add news fact extraction stage"
```

---

### Task 6: Update Card Writer to Prefer Facts

**Files:**
- Modify: `card_writer.py`
- Test: `tests/test_card_writer_normalization.py`

- [ ] **Step 1: Write normalization tests**

Create `tests/test_card_writer_normalization.py`:

```python
from card_writer import normalize_cards


def test_normalize_cards_defaults_missing_optional_card_fields():
    data = {
        "issue_title": "Weekly AI News",
        "issue_summary": "Summary",
        "cards": [
            {
                "slide": 1,
                "type": "cover",
                "headline": "WEEKLY AI NEWS",
                "body": "date range",
            }
        ],
    }

    normalized = normalize_cards(data)
    card = normalized["cards"][0]

    assert card["body"] == ["date range"]
    assert card["visual_type"] == "abstract"
    assert card["source_urls"] == []
```

- [ ] **Step 2: Run test**

Run:

```powershell
python -m pytest tests/test_card_writer_normalization.py -v
```

Expected: PASS with current normalization behavior.

- [ ] **Step 3: Add fact loading helpers**

In `card_writer.py`, add:

```python
FACTS_PATH = Path("data/news_facts.json")
```

Add these functions after `load_top_news()`:

```python
def load_news_facts():
    if not FACTS_PATH.exists():
        return None
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


def facts_to_top_news_like(facts):
    items = []
    for record in facts:
        evidence = "\n".join(record.get("evidence", []))
        facts_text = "\n".join(record.get("facts", []))
        items.append({
            "title": record.get("title"),
            "summary": record.get("summary"),
            "reason": facts_text,
            "category": record.get("category"),
            "score": record.get("confidence", 0) * 100,
            "importance": None,
            "impact": None,
            "novelty": None,
            "confidence": record.get("confidence"),
            "url": record.get("url"),
            "article_domain": record.get("source_domain"),
            "article_text": f"{facts_text}\n{evidence}".strip(),
            "facts": record.get("facts", []),
            "evidence": record.get("evidence", []),
            "entities": record.get("entities", []),
            "numbers": record.get("numbers", []),
        })
    return items
```

- [ ] **Step 4: Update `main()` to prefer facts**

In `card_writer.py`, replace:

```python
top_news = load_top_news()
print(f"TOP 뉴스 입력: {len(top_news)}개")

print("원문 URL fetch 중...")
enriched_news = enrich_top_news(top_news)
```

with:

```python
facts = load_news_facts()
if facts:
    enriched_news = facts_to_top_news_like(facts)
    print(f"팩트 입력: {len(enriched_news)}개")
else:
    top_news = load_top_news()
    print(f"TOP 뉴스 입력: {len(top_news)}개")
    print("[WARN] data/news_facts.json이 없어 원문 fetch 기반으로 진행합니다.")
    print("원문 URL fetch 중...")
    enriched_news = enrich_top_news(top_news)
```

- [ ] **Step 5: Strengthen prompt fact grounding**

In `build_prompt()`, add this rule near the existing writing rules:

```text
- facts/evidence/entities/numbers 필드가 있으면 그것만 우선 근거로 사용하라.
- source_urls가 없는 NEWS 카드는 만들지 마라.
- evidence에 없는 수치, 날짜, 벤치마크, 기능명을 새로 만들지 마라.
```

- [ ] **Step 6: Run tests**

Run:

```powershell
python -m pytest tests/test_card_writer_normalization.py tests/test_schemas.py -v
```

Expected: PASS.

- [ ] **Step 7: Run card writing smoke command**

Run:

```powershell
python card_writer.py
```

Expected: `data/cards.json` is regenerated and validated by:

```powershell
python run_pipeline.py --write
```

- [ ] **Step 8: Commit**

```powershell
git add card_writer.py tests/test_card_writer_normalization.py data/cards.json
git commit -m "feat: ground card writing in extracted facts"
```

---

### Task 7: Add Renderer Input Validation

**Files:**
- Modify: `card_renderer.py`
- Test: `tests/test_renderer_validation.py`

- [ ] **Step 1: Write failing renderer validation tests**

Create `tests/test_renderer_validation.py`:

```python
import pytest

from card_renderer import validate_render_card


def test_validate_render_card_rejects_missing_headline():
    with pytest.raises(ValueError, match="headline"):
        validate_render_card({"slide": 2, "type": "news", "body": []})


def test_validate_render_card_rejects_invalid_visual_type():
    card = {
        "slide": 2,
        "type": "news",
        "headline": "Title",
        "body": ["Body"],
        "visual_type": "unknown",
        "source_urls": ["https://example.com"],
    }

    with pytest.raises(ValueError, match="visual_type"):
        validate_render_card(card)
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
python -m pytest tests/test_renderer_validation.py -v
```

Expected: FAIL because `validate_render_card` does not exist.

- [ ] **Step 3: Implement renderer validation**

In `card_renderer.py`, add near the constants:

```python
VALID_VISUAL_TYPES = {"diagram", "chart", "timeline", "comparison", "abstract"}
```

Add before `render_card()`:

```python
def validate_render_card(card):
    for field in ["slide", "type", "headline", "body"]:
        if field not in card:
            raise ValueError(f"card missing required field: {field}")
    if not isinstance(card["body"], list):
        raise ValueError("card body must be a list")
    visual_type = card.get("visual_type", "abstract")
    if visual_type not in VALID_VISUAL_TYPES:
        raise ValueError(f"invalid visual_type: {visual_type}")
```

Update `render_card(card)` to start with:

```python
validate_render_card(card)
```

- [ ] **Step 4: Run renderer validation tests**

Run:

```powershell
python -m pytest tests/test_renderer_validation.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add card_renderer.py tests/test_renderer_validation.py
git commit -m "feat: validate renderer card input"
```

---

### Task 8: Add Visual-Type Rendering Templates

**Files:**
- Modify: `card_renderer.py`

- [ ] **Step 1: Add visual accent helpers**

In `card_renderer.py`, add helper functions before `render_news()`:

```python
def draw_source_label(draw, card):
    urls = card.get("source_urls", [])
    if not urls:
        return
    domain = urls[0].split("/")[2].replace("www.", "") if "://" in urls[0] else urls[0]
    font = load_font(22, True)
    draw.text((WIDTH - 80, HEIGHT - 70), domain[:36], anchor="ra", font=font, fill=SUBTEXT)


def draw_diagram_accent(draw):
    y = 840
    xs = [240, 540, 840]
    for x in xs:
        draw.rounded_rectangle([x - 70, y - 42, x + 70, y + 42], radius=22, outline=PRIMARY, width=4)
    draw.line([310, y, 470, y], fill=PRIMARY, width=5)
    draw.line([610, y, 770, y], fill=PRIMARY, width=5)


def draw_timeline_accent(draw):
    y = 850
    draw.line([180, y, 900, y], fill=PRIMARY, width=5)
    for x in [240, 420, 600, 780]:
        draw.ellipse([x - 14, y - 14, x + 14, y + 14], fill=PRIMARY)


def draw_comparison_accent(draw):
    draw.rounded_rectangle([130, 770, 500, 910], radius=24, outline=PRIMARY, width=4)
    draw.rounded_rectangle([580, 770, 950, 910], radius=24, outline=PRIMARY, width=4)
    font = load_font(28, True)
    draw.text((315, 840), "Before", anchor="mm", font=font, fill=PRIMARY)
    draw.text((765, 840), "After", anchor="mm", font=font, fill=PRIMARY)


def draw_chart_accent(draw):
    baseline = 910
    bars = [(230, 90), (390, 150), (550, 220), (710, 300)]
    for x, h in bars:
        draw.rounded_rectangle([x, baseline - h, x + 80, baseline], radius=18, fill=PRIMARY)
```

- [ ] **Step 2: Update `render_news()` to use visual type**

At the end of `render_news(card)`, before `return img`, add:

```python
    visual_type = card.get("visual_type", "abstract")
    if visual_type == "diagram":
        draw_diagram_accent(draw)
    elif visual_type == "timeline":
        draw_timeline_accent(draw)
    elif visual_type == "comparison":
        draw_comparison_accent(draw)
    elif visual_type == "chart":
        draw_chart_accent(draw)

    draw_source_label(draw, card)
```

- [ ] **Step 3: Render existing cards**

Run:

```powershell
python card_renderer.py
```

Expected: PNG files are regenerated in `output/`.

- [ ] **Step 4: Open or inspect output files**

Run:

```powershell
Get-ChildItem output -Filter *.png
```

Expected: one PNG file per card exists.

- [ ] **Step 5: Commit**

```powershell
git add card_renderer.py output
git commit -m "feat: render visual type accents"
```

---

### Task 9: Add Review Exporter

**Files:**
- Create: `review_exporter.py`

- [ ] **Step 1: Implement `review_exporter.py`**

Create `review_exporter.py`:

```python
from __future__ import annotations

import html
import json
from pathlib import Path


CARDS_PATH = Path("data/cards.json")
FACTS_PATH = Path("data/news_facts.json")
OUTPUT_DIR = Path("output")
REVIEW_PATH = OUTPUT_DIR / "review.html"


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def fact_by_rank(facts):
    return {record.get("rank"): record for record in facts}


def render_list(items):
    if not items:
        return "<p class=\"muted\">None</p>"
    return "<ul>" + "".join(f"<li>{html.escape(str(item))}</li>" for item in items) + "</ul>"


def render_sources(urls):
    if not urls:
        return "<p class=\"warn\">Missing source URL</p>"
    links = []
    for url in urls:
        safe = html.escape(url)
        links.append(f'<li><a href="{safe}" target="_blank" rel="noopener noreferrer">{safe}</a></li>')
    return "<ul>" + "".join(links) + "</ul>"


def build_html(cards_data, facts):
    facts_by_rank = fact_by_rank(facts)
    sections = []

    for card in cards_data.get("cards", []):
        slide = card.get("slide")
        fact = facts_by_rank.get(slide - 1, {})
        image_path = f"{slide:02d}.png"
        body = card.get("body", [])
        warnings = []
        if card.get("type") == "news" and not card.get("source_urls"):
            warnings.append("뉴스 카드에 source_urls가 없습니다.")
        if fact and float(fact.get("confidence", 1)) < 0.65:
            warnings.append("팩트 confidence가 낮습니다.")

        sections.append(f"""
        <section class="review-card">
          <div>
            <img src="{image_path}" alt="{html.escape(card.get('headline', 'card'))}">
          </div>
          <div>
            <p class="eyebrow">Slide {slide} · {html.escape(card.get('type', ''))} · {html.escape(card.get('visual_type', 'abstract'))}</p>
            <h2>{html.escape(card.get('headline', ''))}</h2>
            <h3>Card Body</h3>
            {render_list(body)}
            <h3>Sources</h3>
            {render_sources(card.get('source_urls', []))}
            <h3>Facts</h3>
            {render_list(fact.get('facts', []))}
            <h3>Evidence</h3>
            {render_list(fact.get('evidence', []))}
            {render_list(warnings) if warnings else ""}
          </div>
        </section>
        """)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>{html.escape(cards_data.get("issue_title", "AI News Review"))}</title>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      background: #f4efe6;
      color: #111;
      font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Malgun Gothic", sans-serif;
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
    }}
    .review-card {{
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 28px;
      padding: 28px 0;
      border-bottom: 1px solid #d8d0c3;
    }}
    img {{
      width: 360px;
      border-radius: 8px;
      display: block;
    }}
    h1, h2 {{
      color: #c9613f;
    }}
    h3 {{
      margin-bottom: 4px;
    }}
    li {{
      line-height: 1.55;
      margin: 4px 0;
    }}
    a {{
      color: #a84f34;
      word-break: break-all;
    }}
    .eyebrow, .muted {{
      color: #666;
    }}
    .warn {{
      color: #a33;
      font-weight: 700;
    }}
    @media (max-width: 760px) {{
      .review-card {{
        grid-template-columns: 1fr;
      }}
      img {{
        width: 100%;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(cards_data.get("issue_title", "AI News Review"))}</h1>
    <p>{html.escape(cards_data.get("issue_summary", ""))}</p>
    {''.join(sections)}
  </main>
</body>
</html>"""


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    cards_data = load_json(CARDS_PATH, {})
    facts = load_json(FACTS_PATH, [])
    REVIEW_PATH.write_text(build_html(cards_data, facts), encoding="utf-8")
    print(f"review HTML saved: {REVIEW_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run review export**

Run:

```powershell
python review_exporter.py
```

Expected: `output/review.html` exists.

- [ ] **Step 3: Run render-only pipeline**

Run:

```powershell
python run_pipeline.py --render-only
```

Expected: render, export, and review stages all complete.

- [ ] **Step 4: Commit**

```powershell
git add review_exporter.py output/review.html
git commit -m "feat: add card review export"
```

---

### Task 10: Final Verification

**Files:**
- No new files required

- [ ] **Step 1: Run network-free tests**

Run:

```powershell
python -m pytest tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run existing-data pipeline smoke test**

Run:

```powershell
python run_pipeline.py --render-only
```

Expected: PNG files, `output/cards.html`, and `output/review.html` are regenerated.

- [ ] **Step 3: Run fact/card stages if Ollama is available**

Run:

```powershell
python run_pipeline.py --facts --write --render --export --review
```

Expected: `data/news_facts.json`, `data/cards.json`, PNG files, `output/cards.html`, and `output/review.html` are regenerated.

- [ ] **Step 4: Inspect git status**

Run:

```powershell
git status --short
```

Expected: only intentional generated outputs are modified. Do not revert unrelated pre-existing files such as existing `data/`, `output/`, or `AGENTS.md` changes unless the user explicitly requests it.

- [ ] **Step 5: Commit final verification updates**

```powershell
git add docs/superpowers/specs/2026-05-09-ai-news-agent-extended-mvp-design.md docs/superpowers/plans/2026-05-09-ai-news-agent-extended-mvp.md
git commit -m "docs: plan extended ai news agent mvp"
```

---

## Self-Review

- Spec coverage: The plan covers orchestration, validation, source utilities, fact extraction, fact-grounded card writing, rendering templates, review output, and tests.
- Placeholder scan: No task contains placeholder implementation instructions.
- Type consistency: Validation functions, file paths, artifact names, and stage names are consistent across tasks.
- Scope check: The plan stays within the local script-based extended MVP and avoids hosted UI, database persistence, scheduling, and publishing.

