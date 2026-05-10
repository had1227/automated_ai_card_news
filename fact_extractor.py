from __future__ import annotations

import json
import math
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

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def load_top_news():
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def save_facts(records):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _clean_text(value):
    return " ".join(str(value or "").split())


def _as_text_list(value, fallback=None):
    if isinstance(value, list):
        items = [_clean_text(item) for item in value]
    elif isinstance(value, str):
        items = [_clean_text(value)]
    else:
        items = []

    items = [item for item in items if item]
    if items:
        return items
    return list(fallback or [])


def compact_cluster_text(item):
    parts = []
    for idx, entry in enumerate(item.get("cluster", [])[:4], start=1):
        title = _clean_text(entry.get("title", ""))
        text = _clean_text(entry.get("text") or entry.get("summary") or "")
        url = _clean_text(entry.get("url", ""))

        section = f"Source {idx}\nTitle: {title}\nText: {text}"
        if url:
            section += f"\nURL: {url}"
        parts.append(section.strip())

    result = "\n\n".join(part for part in parts if part)
    return result[:MAX_CLUSTER_TEXT_CHARS]


def fallback_record(rank, item):
    title = _clean_text(item.get("title", ""))
    summary = _clean_text(item.get("summary", ""))
    reason = _clean_text(item.get("reason", ""))
    url = _clean_text(item.get("url", ""))
    category = _clean_text(item.get("category", ""))

    fact = summary or reason or title
    evidence = reason or summary or title

    return {
        "rank": rank,
        "title": title or "Untitled news item",
        "url": url,
        "source_domain": clean_domain(url),
        "category": category or "uncategorized",
        "summary": summary or fact,
        "facts": [fact],
        "evidence": [evidence],
        "entities": [],
        "numbers": [],
        "confidence": 0.55,
    }


def build_prompt(rank, item):
    cluster_text = compact_cluster_text(item)
    fallback = fallback_record(rank, item)
    return f"""
You are extracting verifiable facts for an AI news pipeline.

Rules:
- Use only the title, summary, reason, URL, category, and source snippets below.
- Extract only verifiable facts. Do not speculate, infer hidden motives, or add context that is not in the provided text.
- If evidence is weak, keep facts conservative and lower confidence.
- Return JSON only. Do not include markdown, comments, or prose outside JSON.
- The JSON object must contain exactly these keys:
  rank, title, url, source_domain, category, summary, facts, evidence, entities, numbers, confidence
- facts and evidence must be non-empty arrays of short strings.
- entities and numbers must be arrays. Put only explicit named entities or explicit numeric claims.
- confidence must be a number between 0 and 1.

Required fixed fields:
rank: {rank}
url: {json.dumps(fallback["url"], ensure_ascii=False)}
source_domain: {json.dumps(fallback["source_domain"], ensure_ascii=False)}

News item:
title: {json.dumps(fallback["title"], ensure_ascii=False)}
summary: {json.dumps(fallback["summary"], ensure_ascii=False)}
reason: {json.dumps(_clean_text(item.get("reason", "")), ensure_ascii=False)}
category: {json.dumps(fallback["category"], ensure_ascii=False)}
url: {json.dumps(fallback["url"], ensure_ascii=False)}

Source snippets:
{cluster_text}
""".strip()


def _extract_json_object(text):
    value = str(text or "").strip()
    if not value:
        raise ValueError("empty Ollama response")

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(value[start : end + 1])


def _call_ollama(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=180)
            response.raise_for_status()
            body = response.json()
            return _extract_json_object(body.get("response", ""))
        except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)

    raise RuntimeError(f"Ollama fact extraction failed: {last_error}") from last_error


def _as_confidence(value):
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.55

    if not math.isfinite(confidence):
        return 0.55
    if confidence < 0:
        return 0.0
    if confidence > 1:
        return 1.0
    return confidence


def normalize_record(rank, item, data):
    fallback = fallback_record(rank, item)
    llm_data = data if isinstance(data, dict) else {}
    record = {**fallback, **llm_data}

    record["rank"] = rank
    record["title"] = _clean_text(record.get("title")) or fallback["title"]
    record["url"] = fallback["url"]
    record["source_domain"] = clean_domain(fallback["url"])
    record["category"] = _clean_text(record.get("category")) or fallback["category"]
    record["summary"] = _clean_text(record.get("summary")) or fallback["summary"]
    record["facts"] = _as_text_list(record.get("facts"), fallback["facts"])
    record["evidence"] = _as_text_list(record.get("evidence"), fallback["evidence"])
    record["entities"] = _as_text_list(record.get("entities"), [])
    record["numbers"] = _as_text_list(record.get("numbers"), [])
    record["confidence"] = _as_confidence(record.get("confidence"))

    return record


def extract_fact_record(rank, item):
    prompt = build_prompt(rank, item)
    data = _call_ollama(prompt)
    record = normalize_record(rank, item, data)
    validate_fact_record(record)
    return record


def main():
    top_news = load_top_news()
    records = []
    fallback_count = 0

    for rank, item in enumerate(top_news, start=1):
        try:
            record = extract_fact_record(rank, item)
        except Exception as exc:
            print(f"[WARN] using fallback facts for rank {rank}: {exc}")
            record = fallback_record(rank, item)
            validate_fact_record(record)
            fallback_count += 1
        records.append(record)

    save_facts(records)
    print(
        f"saved fact records: {OUTPUT_PATH} "
        f"({len(records)} records, {fallback_count} fallback)"
    )


if __name__ == "__main__":
    main()
