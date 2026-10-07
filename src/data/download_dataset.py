"""
Download and prepare Teklia/IAM-line dataset from Hugging Face.

Saves line images and an annotations file matching the project format:
    data/raw/
    ├── lines.txt
    └── lines/
        ├── train_00000.png
        └── ...

Usage:
    # Full dataset download (~265 MB total across all splits)
    python -m src.data.download_dataset

    # Download subset for quick test/verification (e.g. 100 samples)
    python -m src.data.download_dataset --sample-limit 100
"""

import argparse
import io
import os
import pandas as pd
from PIL import Image

PARQUET_URLS = {
    "train": "https://huggingface.co/datasets/Teklia/IAM-line/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet",
    "validation": "https://huggingface.co/datasets/Teklia/IAM-line/resolve/refs%2Fconvert%2Fparquet/default/validation/0000.parquet",
    "test": "https://huggingface.co/datasets/Teklia/IAM-line/resolve/refs%2Fconvert%2Fparquet/default/test/0000.parquet",
}


def download_and_extract(output_dir: str = "data/raw", splits: list[str] = None, sample_limit: int = None):
    splits = splits or ["train", "validation", "test"]
    lines_dir = os.path.join(output_dir, "lines")
    os.makedirs(lines_dir, exist_ok=True)
    ann_path = os.path.join(output_dir, "lines.txt")

    total_saved = 0
    with open(ann_path, "w", encoding="utf-8") as f_ann:
        f_ann.write("# IAM format lines.txt generated from Teklia/IAM-line\n")

        for split in splits:
            url = PARQUET_URLS.get(split)
            if not url:
                print(f"[!] Unknown split '{split}', skipping.")
                continue

            print(f"[*] Downloading {split} split from Hugging Face...")
            df = pd.read_parquet(url)
            print(f"    Loaded {len(df)} entries for {split}.")

            if sample_limit:
                df = df.iloc[:sample_limit]
                print(f"    Using sample limit: {len(df)} entries.")

            for i, row in df.iterrows():
                text = str(row["text"]).strip()
                img_data = row["image"]
                img_bytes = img_data["bytes"] if isinstance(img_data, dict) else img_data

                line_id = f"{split}_{i:05d}"
                img_filename = f"{line_id}.png"
                img_path = os.path.join(lines_dir, img_filename)

                # Save line image
                img = Image.open(io.BytesIO(img_bytes)).convert("L")
                img.save(img_path)

                # Format matching IAM lines.txt: line_id status ... text_with_pipe
                pipe_text = text.replace(" ", "|")
                f_ann.write(f"{line_id} ok 0 0 0 0 0 JJ {pipe_text}\n")
                total_saved += 1

    print(f"[+] Finished! Saved {total_saved} line images to '{lines_dir}'")
    print(f"[+] Annotation file saved to '{ann_path}'")


def main():
    parser = argparse.ArgumentParser(description="Download Teklia/IAM-line dataset.")
    parser.add_argument("--output_dir", default="data/raw", help="Output directory (default: data/raw)")
    parser.add_argument("--splits", nargs="+", default=["train", "validation", "test"],
                        help="Splits to download: train validation test")
    parser.add_argument("--sample-limit", type=int, default=None,
                        help="Maximum samples to download per split (optional, for quick testing)")
    args = parser.parse_args()

    download_and_extract(output_dir=args.output_dir, splits=args.splits, sample_limit=args.sample_limit)


if __name__ == "__main__":
    main()
