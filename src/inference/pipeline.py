import numpy as np
from PIL import Image

from src.segmentation.line_segmentation import find_line_boundaries, segment_text_lines
from src.inference.predict import recognize_text, load_model
from src.evaluation.metrics import calculate_cer, calculate_wer
from src.visualization.visualize import draw_line_regions


def process_document(image_path: str, model, charset=None, ground_truth: str = None) -> dict:
    """Day 13 milestone: document -> segmentation -> recognition -> reconstruction."""
    pil_img = Image.open(image_path).convert("L")
    gray = np.asarray(pil_img)

    boundaries = find_line_boundaries(gray)
    line_crops = [gray[y1:y2, :] for y1, y2 in boundaries]

    texts, confidences = [], []
    for crop in line_crops:
        text, conf = recognize_text(Image.fromarray(crop), model, charset)
        texts.append(text)
        confidences.append(conf)

    full_text = "\n".join(texts)
    annotated = draw_line_regions(gray, boundaries, texts)

    result = {
        "full_text": full_text,
        "line_texts": texts,
        "line_confidences": confidences,
        "annotated_image": annotated,
    }
    if ground_truth is not None:
        result["cer"] = calculate_cer(full_text.replace("\n", " "), ground_truth)
        result["wer"] = calculate_wer(full_text.replace("\n", " "), ground_truth)
    return result


def export_txt(result: dict, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result["full_text"])


if __name__ == "__main__":
    import os
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.inference.pipeline <path_to_document_image>")
        sys.exit(1)

    doc_path = sys.argv[1]
    doc_stem = os.path.splitext(os.path.basename(doc_path))[0]

    out_vis_dir = os.path.join("outputs", "visualizations")
    out_pred_dir = os.path.join("outputs", "predictions")
    os.makedirs(out_vis_dir, exist_ok=True)
    os.makedirs(out_pred_dir, exist_ok=True)

    out_img_path = os.path.join(out_vis_dir, f"{doc_stem}_annotated.png")
    out_txt_path = os.path.join(out_pred_dir, f"{doc_stem}_transcription.txt")

    model, charset = load_model("models/best_model.pth")
    result = process_document(doc_path, model, charset)
    print("--- Recognized Text ---")
    print(result["full_text"])

    export_txt(result, out_txt_path)
    result["annotated_image"].save(out_img_path)
    print(f"\n[+] Saved transcription to: {out_txt_path}")
    print(f"[+] Saved annotated visualization to: {out_img_path}")
