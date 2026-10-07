import numpy as np
from PIL import Image


def find_line_boundaries(image: np.ndarray, min_gap=4, min_height=8) -> list[tuple[int, int]]:
    """image: grayscale np.ndarray (H,W), ink=dark on light background.
    Returns list of (y_start, y_end) row ranges, one per text line."""
    gray = image if image.ndim == 2 else image.mean(axis=2)
    if np.issubdtype(gray.dtype, np.floating) and gray.max() <= 1.0:
        ink = 1.0 - gray
    else:
        ink = 255 - gray  # high value = ink
    row_density = ink.sum(axis=1)
    threshold = row_density.max() * 0.05 if row_density.max() > 0 else 0

    rows_with_text = row_density > threshold
    boundaries = []
    start = None
    gap = 0
    for y, has_text in enumerate(rows_with_text):
        if has_text:
            if start is None:
                start = y
            gap = 0
        else:
            if start is not None:
                gap += 1
                if gap > min_gap:
                    end = y - gap + 1
                    if end - start >= min_height:
                        boundaries.append((start, end))
                    start = None
                    gap = 0
    if start is not None:
        end = len(rows_with_text) - gap
        if end - start >= min_height:
            boundaries.append((start, end))
    return boundaries


def segment_text_lines(image: np.ndarray) -> list[np.ndarray]:
    """Locked interface. image: grayscale np.ndarray (H,W). Returns line crops, top-to-bottom."""
    boundaries = find_line_boundaries(image)
    return [image[y1:y2, :] for y1, y2 in boundaries]


if __name__ == "__main__":
    # synthetic smoke test: 3 dark horizontal bands on white background
    img = np.full((150, 300), 255, dtype=np.uint8)
    img[10:30, 20:280] = 0
    img[60:80, 20:280] = 0
    img[110:130, 20:280] = 0
    lines = segment_text_lines(img)
    print("lines found:", len(lines), [l.shape for l in lines])
    assert len(lines) == 3
    print("OK")
