from datetime import datetime, timezone
from source_utils import (
    CODE_DOMAINS,
    OFFICIAL_DOMAINS,
    RESEARCH_DOMAINS,
    SOCIAL_DOMAINS,
    classify_source,
    clean_domain,
    is_google_news_url,
    parse_datetime,
    prune_history,
    source_trust_score,
)


def test_domain_sets_match_task_3_plan():
    assert OFFICIAL_DOMAINS == {
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
    assert RESEARCH_DOMAINS == {"arxiv.org", "export.arxiv.org", "paperswithcode.com"}
    assert CODE_DOMAINS == {"github.com", "huggingface.co"}
    assert SOCIAL_DOMAINS == {"x.com", "twitter.com", "threads.net"}


def test_unknown_news_domain_defaults_to_media():
    assert classify_source("https://example-news.com/article") == "media"


def test_clean_domain_lowercases_and_removes_www():
    assert clean_domain("https://www.OpenAI.com/news/") == "openai.com"


def test_clean_domain_supports_bare_domain_path():
    assert clean_domain("www.OpenAI.com/news/") == "openai.com"


def test_is_google_news_url_detects_news_google_domain():
    assert is_google_news_url("https://news.google.com/rss/articles/abc?oc=5")


def test_classify_source_detects_official_domain():
    assert classify_source("https://openai.com/news/") == "official"


def test_classify_source_treats_huggingface_as_official():
    assert classify_source("https://huggingface.co/blog/model-release") == "official"


def test_classify_source_detects_code_domain():
    assert classify_source("https://github.com/openai/example") == "code"


def test_source_trust_score_official_is_greater_than_media():
    assert source_trust_score("https://openai.com/news/") > source_trust_score(
        "https://theverge.com/ai"
    )


def test_parse_datetime_returns_utc_datetime():
    parsed = parse_datetime("2026-05-10T09:30:00+09:00")

    assert parsed == datetime(2026, 5, 10, 0, 30, tzinfo=timezone.utc)


def test_prune_history_keeps_recent_items_and_drops_old_items():
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    old = {"id": "old", "published_at": "2026-03-01T00:00:00Z"}
    recent = {"id": "recent", "published_at": "2026-05-01T00:00:00Z"}

    pruned = prune_history([old, recent], keep_days=30, max_items=10, now=now)

    assert pruned == [recent]


def test_prune_history_limits_to_newest_max_items():
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    oldest = {"id": "oldest", "published_at": "2026-05-01T00:00:00Z"}
    middle = {"id": "middle", "published_at": "2026-05-02T00:00:00Z"}
    newest = {"id": "newest", "published_at": "2026-05-03T00:00:00Z"}

    pruned = prune_history([oldest, middle, newest], keep_days=30, max_items=2, now=now)

    assert pruned == [middle, newest]


def test_prune_history_returns_empty_when_max_items_is_zero():
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    item = {"id": "recent", "published_at": "2026-05-01T00:00:00Z"}

    assert prune_history([item], keep_days=30, max_items=0, now=now) == []
