import html
import json
from pathlib import Path
from urllib.parse import urlparse

from dateutil import parser


INPUT_PATH = Path("data/news_facts.json")
OUTPUT_DIR = Path("output")
HTML_PATH = OUTPUT_DIR / "news.html"
ISSUE_TITLE = "이번 주 AI 핵심 뉴스"


def load_records():
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def escape_text(value):
    return html.escape(str(value or ""))


def source_label(url, fallback=""):
    parsed = urlparse(str(url or ""))
    host = parsed.netloc or parsed.path
    label = host.replace("www.", "", 1).split("/")[0]
    return label or fallback or str(url)


def render_link(url, label):
    safe_url = html.escape(str(url or ""), quote=True)
    safe_label = escape_text(label)
    return f'<a href="{safe_url}" style="color:#b85f42;">{safe_label}</a>'


def render_sources(record):
    url = record.get("url")
    if not url:
        return ""

    label = source_label(url, record.get("source_domain", "source"))
    return (
        '<p style="margin:18px 0 0;color:#6b665f;font-size:14px;line-height:1.6;">'
        f"출처: {render_link(url, label)}"
        "</p>"
    )


def display_rank(value, fallback_rank):
    try:
        rank = int(value)
    except (TypeError, ValueError):
        rank = fallback_rank
    return f"{max(rank, 1):02d}"


def _record_date(record):
    value = str(record.get("published_at") or "").strip()
    if not value:
        return None
    try:
        return parser.parse(value).date()
    except (TypeError, ValueError, OverflowError):
        return None


def date_range_label(records):
    dates = [date for date in (_record_date(record) for record in records or []) if date]
    if not dates:
        return ""
    start = min(dates).strftime("%Y.%m.%d")
    end = max(dates).strftime("%Y.%m.%d")
    return f"{start} - {end}"


def render_record(record, fallback_rank):
    rank = display_rank(record.get("rank"), fallback_rank)
    title = escape_text(record.get("korean_title") or record.get("title") or "제목 없음")
    paragraphs = record.get("article_body") or [record.get("summary", "")]
    body_html = "".join(
        f'<p style="margin:12px 0 0;font-size:17px;line-height:1.7;color:#171717;">'
        f"{escape_text(paragraph)}</p>"
        for paragraph in paragraphs
        if str(paragraph or "").strip()
    )

    return f"""
    <article style="padding:34px 0;border-bottom:1px solid #ded8ce;">
      <p style="margin:0 0 12px;color:#b85f42;font-weight:700;font-size:15px;">{rank}</p>
      <h2 style="margin:0 0 10px;font-size:32px;line-height:1.3;color:#171717;">{title}</h2>
      {body_html}
      {render_sources(record)}
    </article>"""


def render_records(records):
    return "\n".join(
        render_record(record, index)
        for index, record in enumerate(records or [], start=1)
        if isinstance(record, dict)
    )


def build_html(records):
    date_range = date_range_label(records)
    date_html = (
        f'<p style="margin:12px 0 0;color:#6b665f;font-size:16px;">{date_range}</p>'
        if date_range
        else ""
    )
    content = render_records(records)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{ISSUE_TITLE}</title>
</head>
<body style="margin:0;background:#f4f1ea;color:#171717;font-family:-apple-system,BlinkMacSystemFont,'Malgun Gothic','Apple SD Gothic Neo',sans-serif;">
  <main style="max-width:860px;margin:0 auto;padding:48px 20px 64px;background:#ffffff;">
    <header style="padding-bottom:28px;border-bottom:2px solid #171717;">
      <h1 style="margin:0;font-size:40px;line-height:1.2;color:#171717;">{ISSUE_TITLE}</h1>
      {date_html}
    </header>
{content}
  </main>
</body>
</html>
"""


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    records = load_records()
    html_text = build_html(records)

    HTML_PATH.write_text(html_text, encoding="utf-8")

    print(f"HTML 저장 완료: {HTML_PATH}")


if __name__ == "__main__":
    main()
