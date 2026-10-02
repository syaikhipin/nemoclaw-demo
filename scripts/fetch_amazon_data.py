"""Fetch the Amazon fashion metadata slice used by the Reflex demo.

Source: the same dataset as qdrant-labs/demo-ecommerce-search —
McAuley-Lab/Amazon-Reviews-2023, raw/meta_categories/meta_Clothing_Shoes_and_Jewelry.jsonl
(5.8M real Amazon fashion products). We stream only the first N lines so the
demo stays light; the file is git-ignored, re-fetch anytime.

Usage: .venv/bin/python -m scripts.fetch_amazon_data [--lines 40000]
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

URL = ("https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main"
       "/raw/meta_categories/meta_Clothing_Shoes_and_Jewelry.jsonl")
DEST = Path(__file__).resolve().parent.parent / "data" / "amazon_fashion.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=40000)
    ap.add_argument("--dest", type=Path, default=DEST)
    args = ap.parse_args()

    req = urllib.request.Request(URL, headers={"User-Agent": "reflex-demo/0.1"})
    n = 0
    args.dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=120) as r, open(args.dest, "w") as f:
        for line in r:
            f.write(line.decode("utf-8", "replace"))
            n += 1
            if n >= args.lines:
                break
    print(f"[fetch] wrote {n} lines -> {args.dest}")


if __name__ == "__main__":
    main()
