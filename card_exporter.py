import html
import json
from pathlib import Path
from urllib.parse import urlparse


INPUT_PATH = Path("data/news_facts.json")
OUTPUT_DIR = Path("output")
HTML_PATH = OUTPUT_DIR / "news.html"


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
    return (
        f'<a href="{safe_url}" target="_blank" '
        f'rel="noopener noreferrer">{safe_label}</a>'
    )


def render_list(items, class_name=""):
    values = [escape_text(item) for item in items or [] if str(item or "").strip()]
    if not values:
        return ""

    class_attr = f' class="{class_name}"' if class_name else ""
    lis = "\n".join(f"      <li>{value}</li>" for value in values)
    return f"    <ul{class_attr}>\n{lis}\n    </ul>"


def render_sources(record):
    url = record.get("url")
    if not url:
        return ""

    label = source_label(url, record.get("source_domain", "source"))
    return f"""
    <p class="source">
      출처: {render_link(url, label)}
    </p>"""


def display_rank(value, fallback_rank):
    try:
        rank = int(value)
    except (TypeError, ValueError):
        rank = fallback_rank
    return f"{max(rank, 1):02d}"


def render_record(record, fallback_rank):
    rank = record.get("rank") or fallback_rank
    title = record.get("title") or "Untitled news item"
    url = record.get("url")
    title_html = render_link(url, title) if url else escape_text(title)
    summary = escape_text(record.get("summary"))
    category = escape_text(record.get("category"))
    confidence = record.get("confidence")

    meta_parts = []
    if category:
        meta_parts.append(category)
    if confidence not in (None, ""):
        meta_parts.append(f"confidence {escape_text(confidence)}")
    meta = " · ".join(meta_parts)
    meta_html = f'      <p class="meta">{meta}</p>\n' if meta else ""

    return f"""
  <article class="news-item">
    <div class="rank">{display_rank(rank, fallback_rank)}</div>
    <div class="news-content">
      <h2>{title_html}</h2>
{meta_html}      <p class="summary">{summary}</p>
      <h3>핵심 사실</h3>
{render_list(record.get("facts", []), "facts")}
      <h3>근거</h3>
{render_list(record.get("evidence", []), "evidence")}
{render_sources(record)}
    </div>
  </article>"""


def render_records(records):
    return "\n".join(
        render_record(record, index)
        for index, record in enumerate(records or [], start=1)
        if isinstance(record, dict)
    )


def build_html(records):
    content = render_records(records)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Weekly AI News</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f1ea;
      --paper: #ffffff;
      --ink: #171717;
      --muted: #6b665f;
      --line: #ded8ce;
      --accent: #b85f42;
      --accent-soft: #f3dfd6;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Malgun Gothic", sans-serif;
    }}

    main {{
      width: min(900px, calc(100% - 40px));
      margin: 0 auto;
      padding: 56px 0 72px;
    }}

    header {{
      padding-bottom: 32px;
      border-bottom: 2px solid var(--ink);
      margin-bottom: 8px;
    }}

    .eyebrow {{
      margin: 0 0 12px;
      color: var(--accent);
      font-size: 15px;
      font-weight: 700;
    }}

    h1 {{
      margin: 0;
      font-size: 44px;
      line-height: 1.15;
    }}

    .lead {{
      margin: 16px 0 0;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.7;
    }}

    .news-item {{
      display: grid;
      grid-template-columns: 72px 1fr;
      gap: 20px;
      padding: 34px 0;
      border-bottom: 1px solid var(--line);
    }}

    .rank {{
      width: 52px;
      height: 52px;
      display: grid;
      place-items: center;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 800;
    }}

    h2 {{
      margin: 0 0 10px;
      font-size: 26px;
      line-height: 1.35;
    }}

    h2 a {{
      color: inherit;
      text-decoration-color: var(--accent);
      text-decoration-thickness: 2px;
      text-underline-offset: 5px;
    }}

    h3 {{
      margin: 22px 0 8px;
      font-size: 15px;
      color: var(--accent);
    }}

    .meta {{
      margin: 0 0 12px;
      color: var(--muted);
      font-size: 14px;
    }}

    .summary {{
      margin: 0;
      font-size: 17px;
      line-height: 1.7;
    }}

    ul {{
      margin: 0;
      padding-left: 22px;
    }}

    li {{
      margin: 7px 0;
      line-height: 1.7;
    }}

    a {{
      color: var(--accent);
      word-break: break-word;
    }}

    .source {{
      margin: 18px 0 0;
      color: var(--muted);
      font-size: 14px;
    }}

    @media (max-width: 640px) {{
      main {{
        width: min(100% - 28px, 900px);
        padding-top: 34px;
      }}

      h1 {{
        font-size: 34px;
      }}

      .news-item {{
        grid-template-columns: 1fr;
        gap: 14px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <p class="eyebrow">WEEKLY AI NEWS</p>
      <h1>Weekly AI News</h1>
      <p class="lead">수집, 랭킹, 팩트 추출 결과를 카드 생성 없이 바로 HTML로 정리했습니다.</p>
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
