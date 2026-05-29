from datetime import datetime, timezone

from collectors import site_collector as collector
from collectors.site_collector import (
    is_noise_url,
    is_probably_recent_by_llm,
    is_valid_href,
    should_keep_article,
)


def test_is_noise_url_detects_privacy_and_terms_pages():
    assert is_noise_url("https://policies.google.com/privacy")
    assert is_noise_url("https://example.com/legal/terms-of-service")


def test_is_valid_href_rejects_policy_links():
    assert not is_valid_href("https://policies.google.com/privacy")
    assert not is_valid_href("/legal/terms")
    assert is_valid_href("/blog/new-model")


def test_should_keep_article_uses_structured_date_before_llm(monkeypatch):
    called = False

    def fake_llm(*args, **kwargs):
        nonlocal called
        called = True
        return False

    monkeypatch.setattr(collector, "is_probably_recent_by_llm", fake_llm)

    assert should_keep_article("2026-05-20", "Title", "Body", now=datetime(2026, 5, 21, tzinfo=timezone.utc))
    assert not called


def test_should_keep_article_rejects_old_structured_date():
    assert not should_keep_article(
        "2026-05-01",
        "Title",
        "Body",
        now=datetime(2026, 5, 21, tzinfo=timezone.utc),
    )


def test_should_keep_article_uses_llm_when_date_is_missing(monkeypatch):
    monkeypatch.setattr(collector, "is_probably_recent_by_llm", lambda title, text, now=None: False)

    assert not should_keep_article(
        None,
        "Old announcement",
        "The article says this was announced last month.",
        now=datetime(2026, 5, 21, tzinfo=timezone.utc),
    )


def test_call_recency_llm_uses_gemini_structured_json(monkeypatch):
    calls = []

    def fake_generate_json(prompt, response_schema, temperature=0.1):
        calls.append(
            {
                "prompt": prompt,
                "response_schema": response_schema,
                "temperature": temperature,
            }
        )
        return {
            "is_recent": True,
            "published_date": "2026-05-24",
            "confidence": 0.8,
            "reason": "Article mentions a May 24, 2026 release.",
        }

    monkeypatch.setattr(collector, "generate_json", fake_generate_json)

    result = collector.call_recency_llm("New model", "Released on May 24, 2026.")

    assert result == {
        "is_recent": True,
        "published_date": "2026-05-24",
        "confidence": 0.8,
        "reason": "Article mentions a May 24, 2026 release.",
    }
    assert len(calls) == 1
    assert "New model" in calls[0]["prompt"]
    assert "Released on May 24, 2026." in calls[0]["prompt"]
    assert calls[0]["response_schema"] == collector.RECENCY_SCHEMA
    assert calls[0]["temperature"] == 0.0
    confidence_schema = collector.RECENCY_SCHEMA["properties"]["confidence"]
    assert confidence_schema["minimum"] == 0.0
    assert confidence_schema["maximum"] == 1.0


def test_is_probably_recent_by_llm_keeps_uncertain_or_failed_judgments(monkeypatch):
    monkeypatch.setattr(collector, "call_recency_llm", lambda title, text, now=None: {"is_recent": False, "confidence": 0.4})

    assert is_probably_recent_by_llm("Title", "Body", now=datetime(2026, 5, 21, tzinfo=timezone.utc))


def test_is_probably_recent_by_llm_keeps_non_dict_judgment(monkeypatch):
    monkeypatch.setattr(collector, "call_recency_llm", lambda title, text, now=None: [])

    assert is_probably_recent_by_llm("Title", "Body", now=datetime(2026, 5, 21, tzinfo=timezone.utc))


def test_is_probably_recent_by_llm_rejects_confident_old_judgment(monkeypatch):
    monkeypatch.setattr(collector, "call_recency_llm", lambda title, text, now=None: {"is_recent": False, "confidence": 0.9})

    assert not is_probably_recent_by_llm("Title", "Body", now=datetime(2026, 5, 21, tzinfo=timezone.utc))


def test_is_probably_recent_by_llm_handles_string_boolean(monkeypatch):
    monkeypatch.setattr(collector, "call_recency_llm", lambda title, text, now=None: {"is_recent": "false", "confidence": 0.9})

    assert not is_probably_recent_by_llm("Title", "Body", now=datetime(2026, 5, 21, tzinfo=timezone.utc))
