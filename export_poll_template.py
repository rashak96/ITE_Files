"""
Emit a CSV template of all (year, question) rows with A–E columns set to 0.
Fill in vote counts after your session, then run apply_poll_results.py.

Usage:
  python export_poll_template.py
  python export_poll_template.py -o my_polls.csv
"""

import argparse
import csv
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA = SCRIPT_DIR / "ite_data.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--output", default="poll_results_template.csv")
    args = ap.parse_args()

    if not DATA.exists():
        print(f"Missing {DATA}; run extract_ite.py first.")
        return 1

    rows = json.loads(DATA.read_text(encoding="utf-8"))
    out = Path(args.output)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "number", "A", "B", "C", "D", "E"])
        for q in sorted(rows, key=lambda x: (x.get("year", 0), x.get("number", 0))):
            y, n = q.get("year"), q.get("number")
            w.writerow([y, n, 0, 0, 0, 0, 0])
    print(f"Wrote {len(rows)} rows to {out.resolve()}")
    print("Fill in vote counts, then: python apply_poll_results.py --csv", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
