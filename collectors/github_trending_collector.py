import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone


URL = "https://github.com/trending?since=weekly"
MAX_README_CHARS = 5000
README_BRANCHES = ["HEAD", "main", "master"]

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def raw_readme_urls(repo_url):
    path = repo_url.replace("https://github.com/", "", 1).strip("/")
    if path.count("/") < 1:
        return []

    owner, repo = path.split("/", 2)[:2]
    return [
        f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
        for branch in README_BRANCHES
    ]


def clean_readme_text(text):
    lines = []
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lines.append(stripped)
    return "\n".join(lines)[:MAX_README_CHARS]


def fetch_readme_text(repo_url):
    for readme_url in raw_readme_urls(repo_url):
        try:
            res = requests.get(readme_url, headers=HEADERS, timeout=15)
            res.raise_for_status()
        except Exception:
            continue

        text = clean_readme_text(res.text)
        if text:
            return text

    return ""


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

        readme_text = fetch_readme_text(repo_url)
        text_parts = [
            repo_name,
            description,
            f"Stars: {stars}",
        ]
        if readme_text:
            text_parts.append("README:")
            text_parts.append(readme_text)

        text = "\n".join(part for part in text_parts if part)

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
