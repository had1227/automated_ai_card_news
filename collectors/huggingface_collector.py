import requests
from datetime import datetime, timezone


API_URL = "https://huggingface.co/api/models?sort=downloads&direction=-1&limit=30"


def is_ai_model(model):
    tags = model.get("tags", [])

    KEYWORDS = [
        "llm",
        "text-generation",
        "transformer",
        "diffusion",
        "vision",
        "multimodal"
    ]

    text = " ".join(tags).lower()

    return any(k in text for k in KEYWORDS)


def collect_huggingface():
    items = []

    try:
        res = requests.get(API_URL, timeout=10)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        print(f"[WARN] HuggingFace API 실패 - {e}")
        return items

    for model in data:

        # 🔥 AI 모델 필터
        if not is_ai_model(model):
            continue

        name = model.get("modelId")
        url = f"https://huggingface.co/{name}"

        tags = model.get("tags", [])

        items.append({
            "platform": "huggingface",
            "collection_mode": "api",
            "topic": "models",
            "source_account": "Hugging Face",
            "title": name,
            "text": f"{name} | tags: {', '.join(tags)}",
            "url": url,
            "author": "HF",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0)
            },
            "media_urls": []
        })

        if len(items) >= 15:
            break

    return items