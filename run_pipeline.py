from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from schemas import (
    validate_cards,
    validate_fact_record,
    validate_item,
    validate_top_news_item,
)


STAGES = {
    "collect": "collect.py",
    "rank": "cluster_rank.py",
    "facts": "fact_extractor.py",
    "write": "card_writer.py",
    "render": "card_renderer.py",
    "export": "card_exporter.py",
    "review": "review_exporter.py",
}

ALL_STAGES = ["collect", "rank", "facts", "write", "render", "export", "review"]
RENDER_ONLY_STAGES = ["render", "export", "review"]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_stage(stage):
    script = STAGES[stage]
    print(f"\n[RUN] {script}")
    result = subprocess.run([sys.executable, script], check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def validate_stage(stage):
    if stage == "collect":
        items = load_json("data/items.json")
        for item in items:
            validate_item(item)
        print(f"[OK] validated {len(items)} collected items")
    elif stage == "rank":
        items = load_json("data/top_news.json")
        for item in items:
            validate_top_news_item(item)
        print(f"[OK] validated {len(items)} ranked items")
    elif stage == "facts":
        records = load_json("data/news_facts.json")
        for record in records:
            validate_fact_record(record)
        print(f"[OK] validated {len(records)} fact records")
    elif stage == "write":
        cards = load_json("data/cards.json")
        validate_cards(cards)
        print(f"[OK] validated {len(cards.get('cards', []))} cards")


def selected_stages(args):
    if args.all:
        return ALL_STAGES
    if args.render_only:
        return RENDER_ONLY_STAGES
    return [stage for stage in STAGES if getattr(args, stage)]


def build_parser():
    parser = argparse.ArgumentParser(description="Run the AI news pipeline.")
    parser.add_argument("--all", action="store_true", help="Run all stages.")
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="Run render, export, and review stages.",
    )
    for stage in STAGES:
        parser.add_argument(f"--{stage}", action="store_true", help=f"Run {stage}.")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    stages = selected_stages(args)

    if not stages:
        parser.error("select at least one stage, --all, or --render-only")

    for stage in stages:
        run_stage(stage)
        validate_stage(stage)


if __name__ == "__main__":
    main()
