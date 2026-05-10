import json
import hashlib
import time
from pathlib import Path

import yaml
from tqdm import tqdm

from source_utils import prune_history
from collectors.rss_collector import collect_rss
from collectors.site_collector import collect_site
from collectors.youtube_rss_collector import collect_youtube_channel_rss
from collectors.github_trending_collector import collect_github_trending
from collectors.google_news_collector import collect_google_news
from collectors.x_collector import collect_x_accounts
from collectors.threads_collector import collect_threads_accounts
from collectors.arxiv_collector import collect_arxiv
from collectors.huggingface_collector import collect_huggingface

DATA_PATH = Path("data/items.json")
HISTORY_PATH = Path("data/history_items.json")

DATA_PATH.parent.mkdir(exist_ok=True)


def log_step(title):
    print(f"\n{'=' * 50}")
    print(f"[STEP] {title}")
    print(f"{'=' * 50}")


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def make_hash(item):
    base = f"{item.get('platform')}|{item.get('url')}|{item.get('title')}|{item.get('text')}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def item_key(item):
    """
    URL이 있으면 URL 기준.
    URL이 없으면 platform + title + text 일부로 hash 생성.
    """
    url = item.get("url")

    if url:
        return f"url::{url}"

    base = f"{item.get('platform')}|{item.get('title')}|{item.get('text', '')[:300]}"
    return f"hash::{hashlib.sha256(base.encode('utf-8')).hexdigest()}"


def main():
    start_total = time.time()

    config = yaml.safe_load(
        Path("sources.yaml").read_text(encoding="utf-8")
    )

    collected = []

    log_step("RSS 수집")
    for source in tqdm(config.get("rss", []), desc="RSS"):
        start = time.time()
        try:
            items = collect_rss(source)
            collected.extend(items)
            print(f"  → {source['name']} : {len(items)}개 ({time.time() - start:.1f}s)")
        except Exception as e:
            print(f"[WARN] RSS 실패: {source.get('name')} - {e}")

    log_step("사이트 크롤링")
    for source in tqdm(config.get("sites", []), desc="SITE"):
        start = time.time()
        try:
            items = collect_site(source)
            collected.extend(items)
            print(f"  → {source['name']} : {len(items)}개 ({time.time() - start:.1f}s)")
        except Exception as e:
            print(f"[WARN] SITE 실패: {source.get('name')} - {e}")

    # log_step("YouTube RSS")
    # for channel in tqdm(config.get("youtube_channels", []), desc="YOUTUBE"):
    #     start = time.time()
    #     try:
    #         items = collect_youtube_channel_rss(channel)
    #         collected.extend(items)
    #         print(f"  → {channel['name']} : {len(items)}개 ({time.time() - start:.1f}s)")
    #     except Exception as e:
    #         print(f"[WARN] YOUTUBE 실패: {channel.get('name')} - {e}")
    
    log_step("GitHub Trending 수집")
    try:
        start = time.time()
        items = collect_github_trending()
        collected.extend(items)
        print(f"  → GitHub Trending : {len(items)}개 ({time.time() - start:.1f}s)")
    except Exception as e:
        print(f"[WARN] GitHub Trending 실패 - {e}")

    log_step("Google News 수집")
    for query in config.get("google_news", {}).get("queries", []):
        start = time.time()
        try:
            items = collect_google_news(query)
            collected.extend(items)
            print(f"  → {query} : {len(items)}개 ({time.time() - start:.1f}s)")
        except Exception as e:
            print(f"[WARN] Google News 실패: {query} - {e}")

    log_step("arXiv 논문 수집")
    try:
        items = collect_arxiv()
        collected.extend(items)
        print(f"  → arXiv : {len(items)}개")
    except Exception as e:
        print(f"[WARN] arXiv 실패 - {e}")

    # log_step("Hugging Face 수집")
    # try:
    #     items = collect_huggingface()
    #     collected.extend(items)
    #     print(f"  → HuggingFace : {len(items)}개")
    # except Exception as e:
    #     print(f"[WARN] HuggingFace 실패 - {e}")

    log_step("X 수집")
    try:
        items = collect_x_accounts(config.get("x_accounts", []))
        collected.extend(items)
        print(f"  → X : {len(items)}개")
    except Exception as e:
        print(f"[WARN] X 실패 - {e}")

    # log_step("Threads 수집")
    # try:
    #     items = collect_threads_accounts(config.get("threads_accounts", []))
    #     collected.extend(items)
    #     print(f"  → Threads : {len(items)}개")
    # except Exception as e:
    #     print(f"[WARN] Threads 실패 - {e}")

    history_items = load_json(HISTORY_PATH, [])
    history_keys = {item_key(item) for item in history_items}

    current_seen = set()
    new_items = []

    for item in tqdm(collected, desc="DEDUP"):
        item["hash"] = make_hash(item)
        key = item_key(item)

        # 이번 실행 안에서 중복 제거
        if key in current_seen:
            continue

        current_seen.add(key)

        # 과거에 이미 본 뉴스면 제거
        if key in history_keys:
            continue

        new_items.append(item)

    log_step("저장")

    # 이번 실행에서 새로 발견한 뉴스만 저장
    save_json(DATA_PATH, new_items)

    # 전체 히스토리는 누적 저장
    updated_history = prune_history(history_items + new_items)
    save_json(HISTORY_PATH, updated_history)

    print("\n📊 결과 요약")
    print(f"수집 전체: {len(collected)}")
    print(f"이번 실행 신규: {len(new_items)}")
    print(f"히스토리 전체: {len(updated_history)}")
    print(f"저장 파일: {DATA_PATH}")
    print(f"히스토리 파일: {HISTORY_PATH}")
    print(f"⏱ 총 실행 시간: {time.time() - start_total:.1f}초")


if __name__ == "__main__":
    main()
