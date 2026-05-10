import json
import time
import re
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

import requests
from bs4 import BeautifulSoup


INPUT_PATH = Path("data/top_news.json")
FACTS_PATH = Path("data/news_facts.json")
OUTPUT_PATH = Path("data/cards.json")

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/generate"

MAX_NEWS_ITEMS = 10
MAX_ARTICLE_CHARS = 3500
MAX_WORKERS = 2


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def load_top_news():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"{INPUT_PATH} 파일이 없습니다.")
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def load_news_facts():
    if not FACTS_PATH.exists():
        return None
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


def save_cards(cards):
    OUTPUT_PATH.write_text(
        json.dumps(cards, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def clean_text(text):
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def domain(url):
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def get_week_range():
    today = datetime.now()
    # 오늘로부터 7일 전(오늘 포함 시 days=6, 미포함 시 days=7)
    start_date = today - timedelta(days=6) 
    return f"{start_date.strftime('%Y.%m.%d')} – {today.strftime('%Y.%m.%d')}"


def extract_article_text_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        tag.decompose()

    selectors = [
        "article",
        "main",
        "[class*=article]",
        "[class*=post]",
        "[class*=content]",
        "[class*=body]",
    ]

    for selector in selectors:
        el = soup.select_one(selector)
        if el:
            text = clean_text(el.get_text(" ", strip=True))
            if len(text) > 400:
                return text[:MAX_ARTICLE_CHARS]

    text = clean_text(soup.get_text(" ", strip=True))
    return text[:MAX_ARTICLE_CHARS]


def fetch_article_text(url):
    if not url:
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="en-US",
            )

            page = context.new_page()

            # 사람이 보는 것처럼 로딩
            page.goto(url, timeout=30000, wait_until="domcontentloaded")

            # JS 렌더링 기다리기
            page.wait_for_timeout(2000)

            html = page.content()

            browser.close()

        return extract_article_text_from_html(html)

    except Exception as e:
        print(f"[WARN] 브라우저 fetch 실패: {url} - {e}")
        return ""


def fallback_article_text(item):
    texts = []

    if item.get("summary"):
        texts.append(item["summary"])

    if item.get("reason"):
        texts.append(item["reason"])

    for raw in item.get("cluster", [])[:3]:
        if raw.get("title"):
            texts.append(raw["title"])
        if raw.get("text"):
            texts.append(raw["text"][:1200])

    return "\n".join(texts).strip()


def enrich_top_news(top_news):
    enriched = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}

        for item in top_news[:MAX_NEWS_ITEMS]:
            url = item.get("url")
            futures[executor.submit(fetch_article_text, url)] = item

        for future in as_completed(futures):
            item = futures[future]
            article_text = future.result()

            if not article_text:
                article_text = fallback_article_text(item)

            enriched.append({
                **item,
                "article_text": article_text[:MAX_ARTICLE_CHARS],
                "article_domain": domain(item.get("url")),
            })

    enriched.sort(key=lambda x: x.get("score", 0), reverse=True)
    return enriched


def facts_to_top_news_like(facts):
    top_news = []

    for record in facts:
        if not isinstance(record, dict):
            continue

        try:
            confidence = float(record.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0

        score = confidence * 100
        facts_list = record.get("facts") if isinstance(record.get("facts"), list) else []
        evidence_list = (
            record.get("evidence") if isinstance(record.get("evidence"), list) else []
        )
        reason = "; ".join(str(item) for item in facts_list if str(item).strip())
        source_domain = record.get("source_domain") or domain(record.get("url"))

        article_parts = []
        if facts_list:
            article_parts.append("Facts:")
            article_parts.extend(str(item) for item in facts_list if str(item).strip())
        if evidence_list:
            article_parts.append("Evidence:")
            article_parts.extend(str(item) for item in evidence_list if str(item).strip())

        top_news.append({
            "title": record.get("title"),
            "summary": record.get("summary"),
            "reason": reason,
            "category": record.get("category"),
            "score": score,
            "importance": score,
            "impact": score,
            "novelty": score,
            "confidence": confidence,
            "url": record.get("url"),
            "article_domain": source_domain,
            "source_domain": source_domain,
            "article_text": "\n".join(article_parts),
            "facts": facts_list,
            "evidence": evidence_list,
            "entities": record.get("entities", []),
            "numbers": record.get("numbers", []),
        })

    top_news.sort(key=lambda item: item.get("score", 0), reverse=True)
    return top_news


def compact_top_news(top_news, max_items=10):
    compacted = []

    for idx, item in enumerate(top_news[:max_items], start=1):
        compacted.append({
            "rank": idx,
            "title": item.get("title"),
            "summary": item.get("summary"),
            "reason": item.get("reason"),
            "category": item.get("category"),
            "score": item.get("score"),
            "importance": item.get("importance"),
            "impact": item.get("impact"),
            "novelty": item.get("novelty"),
            "confidence": item.get("confidence"),
            "url": item.get("url"),
            "source": item.get("article_domain") or domain(item.get("url")),
            "source_domain": item.get("source_domain"),
            "article_text": item.get("article_text", "")[:MAX_ARTICLE_CHARS],
            "facts": item.get("facts", []),
            "evidence": item.get("evidence", []),
            "entities": item.get("entities", []),
            "numbers": item.get("numbers", []),
        })

    return compacted


def build_prompt(top_news):
    top_news_json = json.dumps(
        compact_top_news(top_news),
        ensure_ascii=False,
        indent=2
    )

    return f"""
너는 AI 산업과 기술을 분석하는 테크 에디터다.

아래 뉴스 목록과 각 뉴스의 원문 기사 일부(article_text)를 기반으로,
AI 엔지니어·연구자·기술 기획자를 대상으로 하는
"주간 AI 카드뉴스 원고"를 작성하라.

중요 원칙:
- 각 뉴스를 독립적인 카드로 명확하게 설명하라.
- 뉴스마다 "무슨 일이 있었는지"와 "왜 중요한지"를 전달하라.
- 마지막 1장에만 전체 흐름을 요약하는 인사이트를 넣어라.
- 반드시 article_text와 입력 뉴스 정보에 근거해서 작성하라.
- 원문에 없는 수치, 벤치마크, 기능, 날짜, 기업 관계를 만들어내지 마라.
- article_text가 비어 있거나 부족하면 해당 뉴스의 summary/reason만 활용하되, 추측하지 마라.
- 불필요하게 뉴스를 서로 억지로 묶지 마라.

입력 뉴스:
Grounding rules:
- If facts, evidence, entities, or numbers fields exist, use them as the primary grounding.
- Do not create NEWS cards without source_urls.
- Do not invent numbers, dates, benchmarks, features, or comparisons absent from evidence.
- Every NEWS card source_urls field must include the source URL for that news item.

{top_news_json}

출력은 반드시 아래 JSON 형식만 사용하라.
마크다운, 설명 문장, 코드블록은 출력하지 마라.

{{
  "issue_title": "이번 주 AI 뉴스 핵심 제목",
  "issue_summary": "이번 주 주요 사건 요약 1~2문장",
  "target_reader": "AI 엔지니어, 연구자, 기술 기획자",
  "cards": [
    {{
      "slide": 1,
      "type": "cover",
      "headline": "WEEKLY AI NEWS",
      "body": [
        "YYYY.MM.DD – YYYY.MM.DD",
        "이번 주 AI 핵심 뉴스"
      ],
      "image_hint": "추상적인 AI 네트워크 패턴",
      "visual_type": "abstract",
      "source_urls": []
    }}
  ]
}}

슬라이드 구성:
- 총 8~10장으로 구성하라.
- slide 1: COVER. 첫 장은 코드에서 고정되므로 자유롭게 바꾸지 마라.
- slide 2~9: NEWS. 각 카드 = 하나의 뉴스. 중요도 순서대로 배치하라.
- slide 10: INSIGHT. 이번 주 뉴스들을 관통하는 기술/산업적 흐름 요약.
- 전체 구성이 9장 이하가 더 적절하면 8~9장으로 줄여도 된다.

각 NEWS 카드 내용:
- 무엇이 발표되었는가
- 핵심 기술 또는 변화
- 왜 중요한가
- 실무적으로 볼 포인트가 있으면 포함

작성 규칙:
- headline은 20자 이내.
- body는 3~4개 bullet.
- bullet 하나는 45자 이내.
- 문장은 짧고 명확하게 작성하며, 아이콘 사용 금지.
- "혁신적인", "놀라운", "게임체인저" 같은 과장 표현은 쓰지 마라.
- 가능한 경우 모델, 인프라, 비용, 추론, 멀티모달, 오픈소스, 배포 전략 같은 기술 키워드를 포함하라.
- 출처 URL은 카드 본문에 넣지 말고 source_urls 필드에 넣어라.
- 각 NEWS 카드의 source_urls에는 해당 뉴스의 URL을 반드시 포함하라.

visual_type은 아래 중 하나만 사용하라:
- diagram
- chart
- timeline
- comparison
- abstract
""".strip()


def call_ollama(prompt, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            res = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.2
                    }
                },
                timeout=240,
            )
            res.raise_for_status()

            raw = res.json().get("response", "").strip()
            return json.loads(raw)

        except Exception as e:
            if attempt >= max_retries:
                raise RuntimeError(f"Ollama 카드 원고 생성 실패: {e}")
            time.sleep(2 * (attempt + 1))


def normalize_cards(data):
    if not isinstance(data, dict):
        data = {}

    data.setdefault("issue_title", "이번 주 AI 뉴스")
    data.setdefault("issue_summary", "")
    data.setdefault("target_reader", "AI 엔지니어, 연구자, 기술 기획자")
    data.setdefault("cards", [])

    for idx, card in enumerate(data.get("cards", []), start=1):
        card.setdefault("slide", idx)
        card.setdefault("type", "news")
        card.setdefault("headline", "")
        card.setdefault("body", [])
        card.setdefault("image_hint", "")
        card.setdefault("visual_type", "abstract")
        card.setdefault("source_urls", [])

        if isinstance(card["body"], str):
            card["body"] = [card["body"]]

        if card["visual_type"] not in {
            "diagram", "chart", "timeline", "comparison", "abstract"
        }:
            card["visual_type"] = "abstract"

    return data


def enforce_cover_format(data):
    week_range = get_week_range()

    if not data.get("cards"):
        data["cards"] = []

    if not data["cards"]:
        data["cards"].append({})

    cover = data["cards"][0]

    cover["slide"] = 1
    cover["type"] = "cover"
    cover["headline"] = "WEEKLY AI NEWS"
    cover["body"] = [
        week_range,
        "이번 주 AI 핵심 뉴스"
    ]
    cover["image_hint"] = "크림 배경 위 추상적인 AI 네트워크 패턴"
    cover["visual_type"] = "abstract"
    cover["source_urls"] = []

    for idx, card in enumerate(data["cards"], start=1):
        card["slide"] = idx

    return data


def validate_cards(data):
    if not isinstance(data, dict):
        raise ValueError("cards 결과가 dict가 아닙니다.")

    required_top = ["issue_title", "issue_summary", "cards"]
    for key in required_top:
        if key not in data:
            raise ValueError(f"필수 필드 누락: {key}")

    if not isinstance(data["cards"], list):
        raise ValueError("cards 필드는 list여야 합니다.")

    if not 8 <= len(data["cards"]) <= 10:
        print(f"[WARN] 카드 수가 예상 범위와 다름: {len(data['cards'])}장")

    for idx, card in enumerate(data["cards"], start=1):
        required_card = [
            "slide",
            "type",
            "headline",
            "body",
            "image_hint",
            "visual_type",
            "source_urls",
        ]

        for key in required_card:
            if key not in card:
                raise ValueError(f"{idx}번 카드 필드 누락: {key}")

        if not isinstance(card["body"], list):
            raise ValueError(f"{idx}번 카드 body는 list여야 합니다.")

    return True


def main():
    facts = load_news_facts()
    if isinstance(facts, dict):
        facts = facts.get("records") or facts.get("facts") or []

    if facts:
        enriched_news = facts_to_top_news_like(facts)
        print(f"Using extracted facts for card writing: {len(enriched_news)} records")
    else:
        if facts is not None:
            print("[WARN] data/news_facts.json has no records; falling back to top_news enrichment")
        top_news = load_top_news()
        print(f"TOP 뉴스 입력: {len(top_news)}개")

        print("원문 URL fetch 중...")
        enriched_news = enrich_top_news(top_news)

        fetched_count = sum(1 for item in enriched_news if item.get("article_text"))
        print(f"원문/fallback 텍스트 확보: {fetched_count}/{len(enriched_news)}개")

    prompt = build_prompt(enriched_news)
    cards = call_ollama(prompt)

    cards = normalize_cards(cards)
    cards = enforce_cover_format(cards)
    validate_cards(cards)
    save_cards(cards)

    print(f"카드뉴스 원고 저장 완료: {OUTPUT_PATH}")
    print(f"제목: {cards.get('issue_title')}")
    print(f"카드 수: {len(cards.get('cards', []))}")

    print("\n카드 구성")
    for card in cards["cards"]:
        print(f"{card['slide']}. [{card['type']}] {card['headline']}")


if __name__ == "__main__":
    main()
