import numpy as np
from PIL import Image, ImageDraw


def draw_line_regions(image: np.ndarray, boundaries: list[tuple[int, int]], texts: list[str] = None) -> Image.Image:
    """image: grayscale np.ndarray (H,W). boundaries: (y_start,y_end) per line.
    Returns an RGB PIL image with boxes drawn and optional recognized text labels."""
    pil = Image.fromarray(image).convert("RGB")
    draw = ImageDraw.Draw(pil)
    w = pil.width
    for i, (y1, y2) in enumerate(boundaries):
        draw.rectangle([0, y1, w - 1, y2], outline=(255, 0, 0), width=2)
        if texts and i < len(texts):
            draw.text((2, max(0, y1 - 12)), texts[i], fill=(0, 128, 0))
    return pil


if __name__ == "__main__":
    img = np.full((150, 300), 255, dtype=np.uint8)
    img[10:30, :] = 0
    out = draw_line_regions(img, [(10, 30)], ["hello"])
    print("output size", out.size, out.mode)
    assert out.size == (300, 150)
    print("OK")
