# collectors/threads_collector.py

import re
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright


MAX_POSTS_PER_ACCOUNT = 10
KEEP_DAYS = 7


def extract_threads_date_from_text(text):
    """
    Threads article 텍스트에서 날짜/시간 문자열 추출.
    지원:
    - 2m, 3h, 4d
    - 2w
    - Apr 10
    - Aug 6, 2025
    """

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    for line in lines:
        # 2m / 3h / 4d / 2w
        if re.fullmatch(r"\d+[mhdw]", line):
            return line

        # Apr 10
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}", line):
            return line

        # Aug 6, 2025
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", line):
            return line

    return None


def parse_threads_date(date_str):
    if not date_str:
        return None

    now = datetime.now(timezone.utc)

    try:
        if re.fullmatch(r"\d+m", date_str):
            return (now - timedelta(minutes=int(date_str[:-1]))).isoformat()

        if re.fullmatch(r"\d+h", date_str):
            return (now - timedelta(hours=int(date_str[:-1]))).isoformat()

        if re.fullmatch(r"\d+d", date_str):
            return (now - timedelta(days=int(date_str[:-1]))).isoformat()

        if re.fullmatch(r"\d+w", date_str):
            return (now - timedelta(weeks=int(date_str[:-1]))).isoformat()

        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", date_str):
            dt = datetime.strptime(date_str, "%b %d, %Y")
            return dt.replace(tzinfo=timezone.utc).isoformat()

        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}", date_str):
            dt = datetime.strptime(date_str, "%b %d")
            dt = dt.replace(year=now.year, tzinfo=timezone.utc)

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

    skip_exact = {
        "Follow",
        "Reply",
        "Repost",
        "Share",
        "Like",
        "View replies",
        "Translate",
        "See more",
    }

    cleaned = []

    for line in lines:
        if line in skip_exact:
            continue

        if line == "·":
            continue

        # 날짜/시간 제거
        if re.fullmatch(r"\d+[mhdw]", line):
            continue
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}", line):
            continue
        if re.fullmatch(r"[A-Z][a-z]{2} \d{1,2}, \d{4}", line):
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def extract_post_url(article, fallback_url):
    try:
        links = article.query_selector_all("a[href*='/@']")
        for link in links:
            href = link.get_attribute("href")
            if not href:
                continue

            if "/post/" in href or "/t/" in href:
                if href.startswith("http"):
                    return href
                return "https://www.threads.net" + href
    except Exception:
        pass

    return fallback_url


def collect_threads_accounts(accounts):
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

                    date_str = extract_threads_date_from_text(raw_text)
                    published_at = parse_threads_date(date_str)

                    if published_at and not is_within_days(published_at, KEEP_DAYS):
                        continue

                    text = clean_post_text(raw_text)

                    if len(text) < 30:
                        continue

                    post_url = extract_post_url(article, account_url)

                    items.append({
                        "platform": "threads",
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
                print(f"[WARN] Threads 실패: {name} - {e}")

        context.close()
        browser.close()

    return items