import json
import re
from pathlib import Path

import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import requests
import time


INPUT_PATH = Path("data/items.json")
OUTPUT_PATH = Path("data/top_news.json")

TOP_N = 10
SIM_THRESHOLD = 0.78
MAX_EVALUATION_TEXT_CHARS = 1200

MODEL = "gemma4:e4b"
OLLAMA_URL = "http://localhost:11434/api/generate"

model = SentenceTransformer("all-MiniLM-L6-v2")


def load_items():
    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def save_items(items):
    OUTPUT_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def normalize(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9가-힣\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def text_of(item):
    return normalize(
        f"{item.get('title','')} {item.get('text','')[:500]}"
    )


def embed(items):
    texts = [text_of(i) for i in items]
    return model.encode(texts, normalize_embeddings=True)


def cluster(items, emb):
    used = set()
    clusters = []

    for i in tqdm(range(len(items)), desc="클러스터링"):
        if i in used:
            continue

        group = [i]
        used.add(i)

        sims = np.dot(emb[i], emb.T)

        for j in range(i + 1, len(items)):
            if j in used:
                continue

            if sims[j] >= SIM_THRESHOLD:
                group.append(j)
                used.add(j)

        clusters.append([items[k] for k in group])

    return clusters


def ollama_json(prompt, max_retries=2, timeout=120):
    for attempt in range(max_retries + 1):
        try:
            res = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1}
                },
                timeout=timeout,
            )
            res.raise_for_status()
            return json.loads(res.json()["response"])

        except Exception as e:
            if attempt >= max_retries:
                print(f"[WARN] Ollama 실패 - {e}")
                return None
            time.sleep(1.5 * (attempt + 1))


def ai_evaluate_cluster(cluster, max_retries=2):
    titles = "\n".join([f"- {i['title']}" for i in cluster[:5]])
    texts = "\n".join(
        [f"- {i.get('text','')[:MAX_EVALUATION_TEXT_CHARS]}" for i in cluster[:5]]
    )

    prompt = f"""
너는 엄격한 AI 뉴스 큐레이션 에디터다.

아래 항목이 주간 AI 카드뉴스 후보로 적합한지 판단하라.

판단 기준:
- AI 모델 출시, 제품 업데이트, 연구 성과, 오픈소스 공개, 대형 제휴, 정책/안전, 인프라 발표는 중요하다.
- 단순 문서, 채용, 가격 페이지, 로그인 페이지, 일반 마케팅 페이지, 튜토리얼성 글은 noise로 본다.
- 카드뉴스 가치가 있으려면 독자가 "이번 주 AI 업계에 무슨 일이 있었는지" 이해하는 데 도움이 되어야 한다.
- 추측하지 말고 주어진 정보만 기준으로 판단하라.

반드시 아래 JSON 형식만 출력하라:

{{
  "is_ai_news": true,
  "is_card_news_worthy": true,
  "category": "model_release",
  "importance": 10.0,
  "trending": 10.0,
  "novelty": 10.0,
  "confidence": 10.0,
  "reason": "판단 이유",
  "one_line_summary": "한 줄 요약"
}}

뉴스 묶음:
제목:
{titles}

내용:
{texts}
"""
    return ollama_json(prompt, max_retries=max_retries)


def representative(cluster):
    return max(cluster, key=lambda x: len(x.get("text", "")))


def ai_is_duplicate(candidate, selected_item, max_retries=1):
    prompt = f"""
너는 뉴스 편집장이다.

아래 두 뉴스가 주간 카드뉴스에서 "같은 사건"으로 봐야 하는지 판단하라.

같은 사건으로 판단해야 하는 경우:
- 같은 모델/제품 출시를 다룸
- 같은 회사의 같은 발표를 다룸
- 같은 연구/논문/오픈소스 공개를 다룸
- 제목이 달라도 핵심 사건이 동일함

다른 사건으로 판단해야 하는 경우:
- 같은 회사지만 다른 제품/모델/업데이트
- 같은 분야지만 별개의 발표
- 한쪽은 산업 뉴스, 다른 한쪽은 기술/연구 뉴스
- 같은 모델군이어도 버전/발표 내용이 명확히 다름

반드시 JSON만 출력하라:

{{
  "is_duplicate": true,
  "confidence": 0.0,
  "reason": "판단 이유"
}}

뉴스 A:
제목: {candidate.get("title")}
요약: {candidate.get("summary")}
카테고리: {candidate.get("category")}
이유: {candidate.get("reason")}

뉴스 B:
제목: {selected_item.get("title")}
요약: {selected_item.get("summary")}
카테고리: {selected_item.get("category")}
이유: {selected_item.get("reason")}
"""
    data = ollama_json(prompt, max_retries=max_retries, timeout=90)

    if not data:
        return False

    return bool(data.get("is_duplicate")) and float(data.get("confidence", 0)) >= 0.65


def is_duplicate_with_selected(candidate, selected):
    for existing in selected:
        if ai_is_duplicate(candidate, existing):
            print(f"[DUPLICATE SKIP] {candidate['title']}")
            print(f"  ↳ 기존: {existing['title']}")
            return True
    return False


def select_diverse_top(results, top_n=10):
    selected = []

    for candidate in tqdm(results, desc="AI 중복 검사 기반 TOP 선정"):
        if len(selected) >= top_n:
            break

        if is_duplicate_with_selected(candidate, selected):
            continue

        selected.append(candidate)

    return selected


def main():
    items = load_items()
    print(f"입력: {len(items)}")

    emb = embed(items)
    clusters = cluster(items, emb)

    print(f"클러스터 수: {len(clusters)}")

    results = []

    for c in tqdm(clusters, desc="AI 평가"):
        ai = ai_evaluate_cluster(c)

        if not ai:
            continue

        if not ai.get("is_ai_news"):
            continue

        if not ai.get("is_card_news_worthy"):
            continue

        rep = representative(c)

        score = (
            float(ai["importance"]) * 40 +
            float(ai["trending"]) * 30 +
            float(ai["novelty"]) * 20 +
            float(ai["confidence"]) * 10
        ) / 10.0

        results.append({
            "score": score,
            "title": rep["title"],
            "summary": ai["one_line_summary"],
            "reason": ai["reason"],
            "category": ai["category"],
            "importance": ai["importance"],
            "trending": ai["trending"],
            "novelty": ai["novelty"],
            "confidence": ai["confidence"],
            "url": rep.get("url"),
            "source_count": len(c),
            "cluster": c
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    top = select_diverse_top(results, TOP_N)

    save_items(top)

    print("\n🔥 TOP 뉴스\n")
    for i, r in enumerate(top, 1):
        print(f"{i}. [{r['score']}] {r['title']}")
        print(f"   - {r['summary']}\n")


if __name__ == "__main__":
    main()
