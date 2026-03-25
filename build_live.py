"""
Build live_ite/static/data.json from ite_data.json (optional --topic / --limit).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_SRC = ROOT / "ite_data.json"
OUT = ROOT / "live_ite" / "static" / "data.json"


def clean_text(s: str) -> str:
    if not s:
        return s
    # Strip replacement-char blocks and private-use glyphs from PDF extraction
    s = re.sub(r"[\uFFFD\uF000-\uF8FF]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description="Build live session data.json")
    ap.add_argument("--topic", help="Filter by topic (substring match, case-insensitive)")
    ap.add_argument("--year", type=int, help="Filter by exam year")
    ap.add_argument("--limit", type=int, help="Max questions (after filters)")
    args = ap.parse_args()

    raw = json.loads(DATA_SRC.read_text(encoding="utf-8"))
    rows = []
    for item in raw:
        if args.topic and args.topic.lower() not in (item.get("topic") or "").lower():
            continue
        if args.year is not None and item.get("year") != args.year:
            continue
        pid = f"y{item['year']}_n{item['number']}"
        opts = item.get("options") or {}
        letters = sorted(opts.keys())
        rows.append(
            {
                "poll_id": pid,
                "year": item["year"],
                "number": item["number"],
                "topic": clean_text(item.get("topic") or ""),
                "subtopic": clean_text(item.get("subtopic") or ""),
                "stem": clean_text(item.get("stem") or ""),
                "options": {k: clean_text(v) for k, v in opts.items()},
                "option_letters": letters,
                "answer": (item.get("answer") or "").strip().upper()[:1],
                "critique": clean_text(item.get("critique") or ""),
            }
        )
        if args.limit and len(rows) >= args.limit:
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {"title": "ITE Live Session", "questions": rows}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(rows)} questions -> {OUT}")


if __name__ == "__main__":
    main()
