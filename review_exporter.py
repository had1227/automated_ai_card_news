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
    by_rank = {}
    for record in facts:
        if not isinstance(record, dict):
            continue
        rank = record.get("rank")
        if rank is not None:
            by_rank[rank] = record
    return by_rank


def render_list(items):
    if not items:
        return '<span class="muted">None</span>'

    safe_items = []
    for item in items:
        text = str(item).strip()
        if text:
            safe_items.append(f"<li>{html.escape(text)}</li>")

    if not safe_items:
        return '<span class="muted">None</span>'
    return f"<ul>{''.join(safe_items)}</ul>"


def render_sources(urls):
    if not urls:
        return '<p class="warning">No source URLs</p>'

    links = []
    for url in urls:
        text = str(url).strip()
        if not text:
            continue
        safe_url = html.escape(text, quote=True)
        links.append(
            '<li>'
            f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">'
            f"{safe_url}</a>"
            "</li>"
        )

    if not links:
        return '<p class="warning">No source URLs</p>'
    return f"<ul>{''.join(links)}</ul>"


def _as_list(value):
    if isinstance(value, list):
        return value
    if value:
        return [value]
    return []


def _slide_label(slide):
    if isinstance(slide, int):
        return f"{slide:02d}.png"
    try:
        return f"{int(slide):02d}.png"
    except (TypeError, ValueError):
        return "card.png"


def _fact_rank_for_card(card):
    rank = card.get("rank")
    if rank is not None:
        return rank

    if card.get("type") != "news":
        return None

    slide = card.get("slide")
    try:
        slide_number = int(slide)
    except (TypeError, ValueError):
        return slide

    if slide_number > 1:
        return slide_number - 1
    return slide_number


def _confidence(record):
    try:
        return float(record.get("confidence"))
    except (AttributeError, TypeError, ValueError):
        return None


def _render_warnings(card, fact):
    warnings = []
    if card.get("type") == "news" and not card.get("source_urls"):
        warnings.append("Missing news source URLs")

    confidence = _confidence(fact)
    if confidence is not None and confidence < 0.65:
        warnings.append(f"Low confidence fact: {confidence:.2f}")

    if not warnings:
        return ""

    items = "".join(f"<li>{html.escape(warning)}</li>" for warning in warnings)
    return f'<div class="warnings"><strong>Warnings</strong><ul>{items}</ul></div>'


def _render_card(card, fact):
    slide = card.get("slide", "")
    card_type = card.get("type", "")
    headline = str(card.get("headline", ""))
    body = _as_list(card.get("body"))
    source_urls = _as_list(card.get("source_urls"))
    image_path = _slide_label(slide)
    facts = _as_list(fact.get("facts")) if isinstance(fact, dict) else []
    evidence = _as_list(fact.get("evidence")) if isinstance(fact, dict) else []

    meta = " / ".join(
        html.escape(str(value))
        for value in [f"slide {slide}", card_type]
        if str(value).strip()
    )

    return f"""
    <section class="card-review">
      <div class="preview">
        <img src="{html.escape(image_path, quote=True)}" alt="{html.escape(headline, quote=True)}">
      </div>
      <div class="content">
        <p class="meta">{meta}</p>
        <h2>{html.escape(headline)}</h2>
        <h3>Card body</h3>
        {render_list(body)}
        <h3>Sources</h3>
        {render_sources(source_urls)}
        <h3>Facts</h3>
        {render_list(facts)}
        <h3>Evidence</h3>
        {render_list(evidence)}
        {_render_warnings(card, fact)}
      </div>
    </section>
    """


def build_html(cards_data, facts):
    cards = cards_data.get("cards", []) if isinstance(cards_data, dict) else []
    facts_by_rank = fact_by_rank(facts if isinstance(facts, list) else [])
    title = (
        cards_data.get("issue_title", "Weekly AI News Review")
        if isinstance(cards_data, dict)
        else "Weekly AI News Review"
    )
    summary = cards_data.get("issue_summary", "") if isinstance(cards_data, dict) else ""

    card_blocks = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        fact = facts_by_rank.get(_fact_rank_for_card(card), {})
        card_blocks.append(_render_card(card, fact))

    if not card_blocks:
        card_blocks.append('<p class="muted">No cards found.</p>')

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(str(title))}</title>
  <style>
    body {{
      margin: 0;
      padding: 32px;
      background: #f4f1ea;
      color: #1f2328;
      font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Malgun Gothic", sans-serif;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
    }}
    header {{
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
    }}
    h2 {{
      margin: 6px 0 18px;
      font-size: 24px;
    }}
    h3 {{
      margin: 18px 0 8px;
      font-size: 15px;
      color: #555;
    }}
    .summary,
    .meta,
    .muted {{
      color: #6a737d;
    }}
    .card-review {{
      display: grid;
      grid-template-columns: minmax(220px, 360px) 1fr;
      gap: 24px;
      padding: 24px 0;
      border-top: 1px solid #d8d2c7;
    }}
    .preview img {{
      width: 100%;
      display: block;
      background: #fff;
      border: 1px solid #d8d2c7;
    }}
    ul {{
      margin: 0;
      padding-left: 22px;
    }}
    li {{
      margin: 6px 0;
      line-height: 1.55;
    }}
    a {{
      color: #9a4f34;
      word-break: break-all;
    }}
    .warning,
    .warnings {{
      color: #8a4b00;
      background: #fff4d6;
    }}
    .warning {{
      margin: 0;
      padding: 8px 10px;
    }}
    .warnings {{
      margin-top: 20px;
      padding: 12px 14px;
      border-left: 4px solid #d18b00;
    }}
    @media (max-width: 760px) {{
      body {{
        padding: 18px;
      }}
      .card-review {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{html.escape(str(title))}</h1>
      <p class="summary">{html.escape(str(summary))}</p>
    </header>
    {''.join(card_blocks)}
  </main>
</body>
</html>
"""


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    cards_data = load_json(CARDS_PATH, {"cards": []})
    facts = load_json(FACTS_PATH, [])
    REVIEW_PATH.write_text(build_html(cards_data, facts), encoding="utf-8")
    print(REVIEW_PATH)


if __name__ == "__main__":
    main()
