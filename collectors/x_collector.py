# collectors/x_collector.py

import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright


MAX_POSTS_PER_ACCOUNT = 10
KEEP_DAYS = 7


def extract_x_date_from_text(text):
    """
    X article 텍스트에서 날짜/시간 문자열 추출.
    지원:
    - 2m, 3h, 4d
    - Apr 10
    - Aug 6, 2025
    """

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines:
        # 2m / 3h / 4d
        if re.fullmatch(r"\d+[mhd]", line):
            return line

        # Apr 10
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}", line):
            return line

        # Aug 6, 2025
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", line):
            return line

    return None


def parse_x_date(date_str):
    if not date_str:
        return None

    now = datetime.now(timezone.utc)

    try:
        # 상대 시간: 5m, 2h, 3d
        if re.fullmatch(r"\d+m", date_str):
            minutes = int(date_str[:-1])
            return (now - timedelta(minutes=minutes)).isoformat()

        if re.fullmatch(r"\d+h", date_str):
            hours = int(date_str[:-1])
            return (now - timedelta(hours=hours)).isoformat()

        if re.fullmatch(r"\d+d", date_str):
            days = int(date_str[:-1])
            return (now - timedelta(days=days)).isoformat()

        # 연도 있는 날짜: Aug 6, 2025
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", date_str):
            dt = datetime.strptime(date_str, "%b %d, %Y")
            return dt.replace(tzinfo=timezone.utc).isoformat()

        # 연도 없는 날짜: Apr 10
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}", date_str):
            dt = datetime.strptime(date_str, "%b %d")
            dt = dt.replace(year=now.year, tzinfo=timezone.utc)

            # 예: 현재 1월인데 Dec 30이 나오면 작년으로 보정
            if dt > now:
                dt = dt.replace(year=now.year - 1)

            return dt.isoformat()

    except Exception:
        return None

    return None


def is_within_days(iso_date, days=7):
    if not iso_date:
        return True

    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return dt >= cutoff
    except Exception:
        return True


def clean_post_text(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    cleaned = []

    skip_exact = {
        "Pinned",
        "Show this thread",
        "Translate post",
    }

    for line in lines:
        if line in skip_exact:
            continue

        # 날짜/시간 라인 제거
        if re.fullmatch(r"\d+[mhd]", line):
            continue
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}", line):
            continue
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", line):
            continue

        # 메타 구분자 제거
        if line == "·":
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def extract_post_url(article, fallback_url):
    try:
        links = article.query_selector_all("a[href*='/status/']")
        for link in links:
            href = link.get_attribute("href")
            if href:
                if href.startswith("http"):
                    return href
                return "https://x.com" + href
    except Exception:
        pass

    return fallback_url


def collect_x_accounts(accounts):
    items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
        )

        page = context.new_page()

        for acc in accounts:
            name = acc["name"]
            account_url = acc["url"]

            try:
                page.goto(account_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(4000)

                articles = page.query_selector_all("article")
                count = 0

                for article in articles:
                    if count >= MAX_POSTS_PER_ACCOUNT:
                        break

                    raw_text = article.inner_text().strip()

                    if not raw_text:
                        continue

                    # 고정글은 오래된 경우가 많아서 제거
                    if raw_text.startswith("Pinned"):
                        continue

                    date_str = extract_x_date_from_text(raw_text)
                    published_at = parse_x_date(date_str)

                    # 날짜가 있으면 7일 이내만 유지
                    if published_at and not is_within_days(published_at, KEEP_DAYS):
                        continue

                    text = clean_post_text(raw_text)

                    if len(text) < 30:
                        continue

                    post_url = extract_post_url(article, account_url)

                    items.append({
                        "platform": "x",
                        "collection_mode": "account",
                        "topic": name,
                        "source_account": name,
                        "title": text[:100],
                        "text": text,
                        "url": post_url,
                        "author": name,
                        "published_at": published_at,
                        "metrics": {},
                        "media_urls": [],
                    })

                    count += 1

            except Exception as e:
                print(f"[WARN] X 실패: {name} - {e}")

        context.close()
        browser.close()

    return items