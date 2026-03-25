"""
Write a Windows shortcut file (.url) so others can double-click ONE file to open the quiz.

This does NOT host the app — it only opens a link. The link must work at the time they click:
  - trycloudflare: only while your start_public_poll.py / run_live.py session is running
  - Render (or similar): works anytime if you deployed there

Usage:
  python make_share_link.py --url https://abc.trycloudflare.com/
  python make_share_link.py --url https://your-app.onrender.com/
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a .url shortcut for sharing")
    ap.add_argument("--url", required=True, help="Public https URL (no trailing path required)")
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "Share_ITE_Presentation.url",
        help="Output .url path",
    )
    args = ap.parse_args()

    base = args.url.rstrip("/")
    text = "[InternetShortcut]\n"
    text += f"URL={base}/\n"
    text += "IconIndex=0\n"

    out = Path(args.out)
    out.write_text(text, encoding="utf-8")
    print(f"Wrote: {out}")
    print("Share that file — others double-click it to open the presenter index.")
    print("Audience topic links still need ?audience on the topic page.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
