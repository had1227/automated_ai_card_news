import card_exporter


def test_build_html_renders_korean_email_digest_without_internal_metadata():
    records = [
        {
            "rank": 1,
            "title": "Open model ships",
            "korean_title": "오픈 모델 출시",
            "summary": "한국어 요약",
            "article_body": [
                "한 연구소가 오픈 모델을 공개했고 개발자는 API에서 사용할 수 있다.",
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
    assert "한 연구소가 오픈 모델을 공개했고" in html
    assert "model_release" not in html
    assert "confidence" not in html
    assert "핵심사실" not in html
    assert "근거" not in html
    assert 'href="https://example.com/model?ref=&lt;ai&gt;"' in html
    assert "font-size:32px" in html


def test_date_range_label_uses_min_and_max_record_dates():
    records = [
        {"published_at": "2026-05-24T09:00:00+09:00"},
        {"published_at": "2026-05-18T00:30:00+00:00"},
        {"published_at": ""},
    ]

    assert card_exporter.date_range_label(records) == "2026.05.18 - 2026.05.24"


def test_render_record_uses_plain_korean_title_and_source_link():
    html = card_exporter.render_record(
        {
            "rank": "2",
            "korean_title": "제목 <확인>",
            "article_body": ["본문 <내용>"],
            "url": "https://example.com/story?a=<b>",
        },
        1,
    )

    assert "제목 &lt;확인&gt;" in html
    assert "<h2><a " not in html
    assert "본문 &lt;내용&gt;" in html
    assert 'href="https://example.com/story?a=&lt;b&gt;"' in html
