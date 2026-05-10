from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from urllib.parse import urlparse
import json

# =====================
# 기본 설정
# =====================

WIDTH, HEIGHT = 1080, 1080

BG = "#E9E3D7"
PRIMARY = "#D07452"
TEXT = "#111111"
SUBTEXT = "#555555"
BOX = "#DCD6CC"
TAG_BG = "#EFE8DC"

TITLE_SIZE = 56
BODY_SIZE = 34
LABEL_SIZE = 28
DATE_SIZE = 64
KEY_SIZE = 40
TAG_SIZE = 22

LINE_HEIGHT_TITLE = 70
LINE_HEIGHT_BODY = 55
LINE_HEIGHT_KEY = 62

FONT_REGULAR = "fonts/Pretendard-Regular.otf"
FONT_BOLD = "fonts/Pretendard-Bold.otf"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# =====================
# 폰트
# =====================

def load_font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)


# =====================
# 캔버스
# =====================

def create_base():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    return img, draw


# =====================
# 중앙 텍스트
# =====================

def draw_centered_multiline(draw, text, center_x, start_y, max_width, font, line_height, fill):
    words = text.split()
    lines = []
    current = ""

    for w in words:
        test = current + " " + w if current else w
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w

    if current:
        lines.append(current)

    y = start_y
    for line in lines:
        draw.text((center_x, y), line, anchor="mm", font=font, fill=fill)
        y += line_height

    return y


def draw_left_multiline(draw, text, x, y, max_width, font, line_height, fill):
    words = text.split()
    current = ""

    for w in words:
        test = current + " " + w if current else w
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                draw.text((x, y), current, font=font, fill=fill)
                y += line_height
            current = w

    if current:
        draw.text((x, y), current, font=font, fill=fill)
        y += line_height

    return y


# =====================
# BULLET
# =====================

def wrap_bullet_lines(draw, text, max_width, font):
    bullet = "•"
    gap = 18
    bullet_width = draw.textlength(bullet, font=font)
    text_width = max_width - bullet_width - gap

    words = text.split()
    current = ""
    wrapped = []

    for w in words:
        test = current + " " + w if current else w

        if draw.textlength(test, font=font) <= text_width:
            current = test
        else:
            if current:
                wrapped.append(current)
            current = w

    if current:
        wrapped.append(current)

    return wrapped


def measure_bullets(draw, lines, max_width, font, line_height, paragraph_gap):
    total = 0

    for line in lines:
        wrapped = wrap_bullet_lines(draw, line, max_width, font)
        total += len(wrapped) * line_height
        total += paragraph_gap

    return total


def draw_bullets(draw, lines, x, y, max_width, font, line_height, fill, paragraph_gap=12):
    bullet = "•"
    gap = 18
    bullet_width = draw.textlength(bullet, font=font)
    text_x = x + bullet_width + gap

    for line in lines:
        wrapped_lines = wrap_bullet_lines(draw, line, max_width, font)

        for i, wrapped in enumerate(wrapped_lines):
            if i == 0:
                draw.text((x, y), bullet, font=font, fill=fill)

            draw.text((text_x, y), wrapped, font=font, fill=fill)
            y += line_height

        y += paragraph_gap

    return y


def fit_bullet_font_for_box(draw, lines, max_width, max_height, base_size):
    size = base_size

    while size >= 24:
        font = load_font(size)
        line_height = int(size * 1.55)
        paragraph_gap = int(size * 0.35)

        height = measure_bullets(
            draw,
            lines,
            max_width,
            font,
            line_height,
            paragraph_gap
        )

        if height <= max_height:
            return font, line_height, paragraph_gap

        size -= 2

    font = load_font(24)
    return font, int(24 * 1.55), int(24 * 0.35)


# =====================
# TAG
# =====================

def draw_tag(draw, text, center_x, y):
    if not text:
        return y

    text = str(text).upper()
    font = load_font(TAG_SIZE, True)

    pad_x = 22
    pad_y = 10
    w = draw.textlength(text, font=font)
    box_w = int(w + pad_x * 2)
    box_h = 42

    x1 = int(center_x - box_w / 2)
    y1 = y
    x2 = x1 + box_w
    y2 = y1 + box_h

    draw.rounded_rectangle(
        [x1, y1, x2, y2],
        radius=20,
        fill=TAG_BG
    )

    draw.text(
        (center_x, y1 + box_h / 2),
        text,
        anchor="mm",
        font=font,
        fill=PRIMARY
    )

    return y2


# =====================
# COVER
# =====================

def render_cover(card):
    img, draw = create_base()

    draw.text(
        (WIDTH / 2, 300),
        "WEEKLY AI NEWS",
        anchor="mm",
        font=load_font(80, True),
        fill=PRIMARY
    )

    body = card.get("body", [])
    date_text = body[0] if len(body) > 0 else ""
    sub_text = body[1] if len(body) > 1 else ""

    draw.text(
        (WIDTH / 2, 620),
        date_text,
        anchor="mm",
        font=load_font(DATE_SIZE),
        fill=TEXT
    )

    draw.text(
        (WIDTH / 2, 720),
        sub_text,
        anchor="mm",
        font=load_font(50),
        fill=SUBTEXT
    )

    return img


# =====================
# NEWS
# =====================

def draw_source_label(draw, card):
    source_urls = card.get("source_urls") or []
    if not source_urls:
        return

    parsed = urlparse(str(source_urls[0]))
    domain = parsed.netloc or parsed.path
    domain = domain.replace("www.", "", 1).split("/")[0]
    if not domain:
        return

    draw.text(
        (WIDTH - 90, HEIGHT - 62),
        domain,
        anchor="rb",
        font=load_font(20),
        fill=SUBTEXT
    )


def render_news(card):
    img, draw = create_base()

    label = f"News {card['slide'] - 1}"

    draw.rounded_rectangle(
        [430, 120, 650, 200],
        radius=40,
        fill=PRIMARY
    )

    draw.text(
        (540, 160),
        label,
        anchor="mm",
        font=load_font(LABEL_SIZE, True),
        fill="white"
    )

    y = draw_centered_multiline(
        draw,
        card["headline"],
        WIDTH / 2,
        300,
        WIDTH - 200,
        load_font(TITLE_SIZE, True),
        LINE_HEIGHT_TITLE,
        PRIMARY
    )

    body = card.get("body", [])
    key_line = body[0] if body else ""
    bullet_lines = body[1:] if len(body) > 1 else []

    y += 34

    if key_line:
        y = draw_left_multiline(
            draw,
            key_line,
            140,
            y,
            WIDTH - 280,
            load_font(KEY_SIZE, True),
            LINE_HEIGHT_KEY,
            TEXT
        )
        y += 24

    if bullet_lines:
        accent_top = 760
        max_body_height = max(0, accent_top - y)
        body_font, line_height, paragraph_gap = fit_bullet_font_for_box(
            draw,
            bullet_lines,
            WIDTH - 280,
            max_body_height,
            BODY_SIZE
        )

        y = draw_bullets(
            draw,
            bullet_lines,
            140,
            y,
            WIDTH - 280,
            body_font,
            line_height,
            TEXT,
            paragraph_gap
        )

    draw_source_label(draw, card)

    return img


# =====================
# INSIGHT
# =====================

def render_insight(card):
    img, draw = create_base()

    draw.text(
        (WIDTH / 2, 190),
        card["headline"],
        anchor="mm",
        font=load_font(TITLE_SIZE, True),
        fill=PRIMARY
    )

    # 아래쪽으로 더 키움: 820 -> 880
    box = [120, 300, 960, 880]
    draw.rounded_rectangle(box, radius=30, fill=BOX)

    padding = 60
    inner_x = box[0] + padding
    inner_y = box[1] + padding
    inner_width = (box[2] - box[0]) - padding * 2
    inner_height = (box[3] - box[1]) - padding * 2

    body_font, line_height, paragraph_gap = fit_bullet_font_for_box(
        draw,
        card["body"],
        inner_width,
        inner_height,
        BODY_SIZE
    )

    draw_bullets(
        draw,
        card["body"],
        inner_x,
        inner_y,
        inner_width,
        body_font,
        line_height,
        TEXT,
        paragraph_gap
    )

    return img


# =====================
# SUMMARY
# =====================

def render_summary(card):
    img, draw = create_base()

    draw.text(
        (WIDTH / 2, 190),
        card["headline"],
        anchor="mm",
        font=load_font(TITLE_SIZE, True),
        fill=PRIMARY
    )

    # 아래쪽으로 더 키움: 820 -> 880
    box = [120, 300, 960, 880]
    draw.rounded_rectangle(box, radius=30, fill=BOX)

    padding = 60
    inner_x = box[0] + padding
    inner_y = box[1] + padding
    inner_width = (box[2] - box[0]) - padding * 2
    inner_height = (box[3] - box[1]) - padding * 2

    body_font, line_height, paragraph_gap = fit_bullet_font_for_box(
        draw,
        card["body"],
        inner_width,
        inner_height,
        BODY_SIZE
    )

    draw_bullets(
        draw,
        card["body"],
        inner_x,
        inner_y,
        inner_width,
        body_font,
        line_height,
        TEXT,
        paragraph_gap
    )

    return img


# =====================
# ROUTER
# =====================

def validate_render_card(card):
    required_fields = ("slide", "type", "headline", "body")

    for field in required_fields:
        if field not in card:
            raise ValueError(f"missing field: {field}")

    if not isinstance(card["body"], list):
        raise ValueError("body must be a list")

    card.setdefault("visual_type", "abstract")


def render_card(card):
    validate_render_card(card)

    if card["type"] == "cover":
        return render_cover(card)
    elif card["type"] == "news":
        return render_news(card)
    else:
        return render_insight(card)


# =====================
# MAIN
# =====================

def render_all(cards):
    for card in cards:
        img = render_card(card)
        path = OUTPUT_DIR / f"{card['slide']:02d}.png"
        img.save(path)
        print("saved:", path)


# =====================
# ENTRY
# =====================

if __name__ == "__main__":
    with open("data/cards.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    render_all(data["cards"])
