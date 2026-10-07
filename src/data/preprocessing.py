import numpy as np
from PIL import Image

TARGET_W, TARGET_H = 256, 64


def preprocess_image(image) -> np.ndarray:
    """Accepts a PIL.Image or np.ndarray. Returns float32 array (H=64,W=256,1) in [0,1]."""
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    image = image.convert("L")  # grayscale

    # resize preserving aspect ratio, pad to target
    w, h = image.size
    scale = min(TARGET_W / w, TARGET_H / h)
    new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
    image = image.resize((new_w, new_h))

    canvas = Image.new("L", (TARGET_W, TARGET_H), color=255)  # white background
    canvas.paste(image, (0, 0))

    arr = np.asarray(canvas, dtype=np.float32) / 255.0
    arr = 1.0 - arr  # ink=high value, background=0 (helps CNN)
    return arr[..., np.newaxis]
