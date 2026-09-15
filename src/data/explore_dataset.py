"""
Day 1 — Dataset investigation (Member 1)

Run this against the raw IAM download to answer the questions the team
needs before Day 2's loader/split work:
  - How many line samples exist?
  - What's the image resolution range?
  - Are there corrupt or mislabeled entries?
  - What does the writer-ID distribution look like (for writer-disjoint splits)?

Usage:
    python explore_dataset.py --data_path data/raw/iam
"""

import argparse
import os
from collections import defaultdict
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None


def find_line_images(data_path: str) -> list[str]:
    """Recursively collect image file paths under data_path."""
    exts = {".png", ".jpg", ".jpeg"}
    paths = []
    for root, _, files in os.walk(data_path):
        for f in files:
            if Path(f).suffix.lower() in exts:
                paths.append(os.path.join(root, f))
    return paths


def inspect_images(paths: list[str], sample_limit: int = 500) -> dict:
    """Report resolution range and flag unreadable files, on a sample for speed."""
    if Image is None:
        return {"error": "Pillow not installed — run `pip install pillow --break-system-packages`"}

    widths, heights, corrupt = [], [], []
    for p in paths[:sample_limit]:
        try:
            with Image.open(p) as img:
                w, h = img.size
                widths.append(w)
                heights.append(h)
        except Exception as e:
            corrupt.append((p, str(e)))

    if not widths:
        return {"error": "No readable images found in sample"}

    return {
        "sampled": len(widths),
        "width_range": (min(widths), max(widths)),
        "height_range": (min(heights), max(heights)),
        "avg_width": sum(widths) / len(widths),
        "avg_height": sum(heights) / len(heights),
        "corrupt_count": len(corrupt),
        "corrupt_examples": corrupt[:5],
    }


def parse_iam_writer_ids(paths: list[str]) -> dict:
    """
    IAM filenames encode form/writer IDs, e.g. 'a01-000u-00.png'.
    The prefix before the first two segments maps to a form, which maps to a writer
    in the IAM metadata files (forms.txt). This is a placeholder grouping by
    filename prefix until forms.txt is parsed in the real run.
    """
    groups = defaultdict(int)
    for p in paths:
        stem = Path(p).stem
        prefix = stem.split("-")[0] if "-" in stem else stem
        groups[prefix] += 1
    return dict(groups)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", required=True, help="Path to raw IAM data")
    args = parser.parse_args()

    if not os.path.isdir(args.data_path):
        print(f"[!] Path not found: {args.data_path}")
        print("    Download IAM first (requires free registration at fki.tic.heia-fr.ch)")
        return

    paths = find_line_images(args.data_path)
    print(f"Total images found: {len(paths)}")

    stats = inspect_images(paths)
    print("Image stats (sampled):", stats)

    groups = parse_iam_writer_ids(paths)
    print(f"Distinct filename-prefix groups: {len(groups)}")
    print("Note: replace with real writer-ID parsing from IAM's forms.txt before Day 2 split.")


if __name__ == "__main__":
    main()
