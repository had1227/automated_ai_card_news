import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone


URL = "https://github.com/trending?since=weekly"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def collect_github_trending():
    items = []

    res = requests.get(URL, headers=HEADERS, timeout=20)
    res.raise_for_status()

    soup = BeautifulSoup(res.text, "html.parser")

    repos = soup.select("article.Box-row")

    for repo in repos:
        # repo name
        title_tag = repo.select_one("h2 a")
        if not title_tag:
            continue

        repo_name = title_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
        repo_url = "https://github.com" + title_tag["href"]

        # description
        desc_tag = repo.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # stars (optional)
        star_tag = repo.select_one("a[href$='/stargazers']")
        stars = star_tag.get_text(strip=True) if star_tag else ""

        text = f"{repo_name}\n{description}\nStars: {stars}"

        items.append({
            "platform": "github_trending",
            "collection_mode": "trending",
            "topic": "github_trending",
            "source_account": "GitHub Trending",
            "title": repo_name,
            "text": text,
            "url": repo_url,
            "author": "GitHub",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "stars": stars
            },
            "media_urls": []
        })

    return items