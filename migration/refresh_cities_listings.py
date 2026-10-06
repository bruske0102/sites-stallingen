#!/usr/bin/env python3
"""Refresh src/data/cities.json listing counts from scraped content (actief only)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "src" / "content" / "stallingen"
CITIES = ROOT / "src" / "data" / "cities.json"


def main() -> None:
    counts: Counter[str] = Counter()
    for path in CONTENT.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") != "actief":
            continue
        key = f"{data['provincie']}/{data['plaats']}"
        counts[key] += 1

    cities = json.loads(CITIES.read_text(encoding="utf-8"))
    for c in cities:
        c["listings"] = counts.get(c["key"], 0)
    CITIES.write_text(json.dumps(cities, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"updated {len(cities)} cities; total actief counted {sum(counts.values())}")
    top = counts.most_common(10)
    print("top:", top)


if __name__ == "__main__":
    main()
