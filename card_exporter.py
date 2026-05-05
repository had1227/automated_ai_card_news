import json
import html
import re
from pathlib import Path

INPUT_PATH = Path("data/cards.json")
OUTPUT_DIR = Path("output")
HTML_PATH = OUTPUT_DIR / "cards.html"


def load_cards():
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def card_to_markdown(card):
    slide = card.get("slide", "")
    card_type = card.get("type", "")
    headline = card.get("headline", "")
    body = card.get("body", [])
    source_urls = card.get("source_urls", [])

    md = []

    if card_type == "cover":
        md.append(f"# {headline}")
    elif card_type in ["insight", "summary", "actionable"]:
        md.append(f"## {headline}")
    else:
        md.append(f"## {slide - 1}. {headline}")

    md.append("")

    if card_type == "cover":
        for line in body:
            md.append(f"{line}")
    else:
        for line in body:
            md.append(f"- {line}")

    if source_urls:
        md.append("")
        md.append("**출처:**")
        for url in source_urls:
            md.append(f"- {url}")

    md.append("")
    md.append("---")
    md.append("")

    return "\n".join(md)


def cards_to_markdown(data):
    md = []

    for card in data.get("cards", []):
        md.append(card_to_markdown(card))

    return "\n".join(md)


def linkify(text):
    url_pattern = r"(https?://[^\s<]+)"

    def repl(match):
        url = match.group(1)
        safe_url = html.escape(url)
        return f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{safe_url}</a>'

    return re.sub(url_pattern, repl, text)


def markdown_to_html_text(md):
    lines = md.splitlines()
    html_lines = []
    in_list = False

    for raw_line in lines:
        line = raw_line.strip()

        # 리스트 처리
        if line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True

            item = line[2:].strip()
            item = linkify(html.escape(item))

            html_lines.append(f"<li>{item}</li>")
            continue

        # 리스트 종료
        if in_list:
            html_lines.append("</ul>")
            in_list = False

        safe = html.escape(line)

        if line.startswith("# "):
            html_lines.append(f"<h1>{safe[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{safe[3:]}</h2>")
        elif line == "---":
            html_lines.append("<hr>")
        elif line.startswith("**") and line.endswith("**"):
            html_lines.append(f"<p><strong>{safe[2:-2]}</strong></p>")
        elif line == "":
            html_lines.append("")
        else:
            html_lines.append(f"<p>{linkify(safe)}</p>")

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def build_html(data, markdown_text):
    cards = data.get("cards", [])
    md_html = markdown_to_html_text(markdown_text)

    image_blocks = []

    for card in cards:
        slide = card.get("slide")
        headline = html.escape(card.get("headline", ""))
        img_path = f"{slide:02d}.png"

        image_blocks.append(f"""
        <section class="card-image">
          <img src="{img_path}" alt="{headline}">
        </section>
        """)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>{html.escape(data.get("issue_title", "Weekly AI News"))}</title>
  <style>
    body {{
      margin: 0;
      padding: 40px;
      background: #E9E3D7;
      color: #111;
      font-family: -apple-system, BlinkMacSystemFont, "Pretendard", "Malgun Gothic", sans-serif;
    }}

    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}

    .section {{
      background: #F7F3EA;
      border-radius: 28px;
      padding: 36px;
      margin-bottom: 40px;
    }}

    .image-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 28px;
      align-items: start;
    }}

    .card-image img {{
      width: 100%;
      border-radius: 24px;
      display: block;
    }}

    h1 {{
      color: #D07452;
      font-size: 42px;
      margin-top: 0;
    }}

    h2 {{
      margin-top: 48px;
      color: #D07452;
      font-size: 30px;
    }}

    ul {{
      padding-left: 24px;
    }}

    li {{
      margin: 8px 0;
      line-height: 1.7;
    }}

    p {{
      line-height: 1.7;
    }}

    a {{
      color: #D07452;
      word-break: break-all;
    }}

    hr {{
      border: none;
      border-top: 1px solid #DCD6CC;
      margin: 36px 0;
    }}

    @media (max-width: 800px) {{
      body {{
        padding: 20px;
      }}

      .image-grid {{
        grid-template-columns: 1fr;
      }}

      .section {{
        padding: 24px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="section">
      <div class="image-grid">
        {''.join(image_blocks)}
      </div>
    </div>

    <div class="section">
      {md_html}
    </div>
  </div>
</body>
</html>
"""


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    data = load_cards()

    markdown_text = cards_to_markdown(data)
    html_text = build_html(data, markdown_text)

    HTML_PATH.write_text(html_text, encoding="utf-8")

    print(f"HTML 저장 완료: {HTML_PATH}")


if __name__ == "__main__":
    main()