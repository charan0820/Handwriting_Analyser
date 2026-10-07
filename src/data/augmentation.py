import numpy as np
from PIL import Image


def augment_image(image: np.ndarray, seed=None) -> np.ndarray:
    """Takes (H,W,1) float32 [0,1] array, applies light rotation/brightness, returns same shape."""
    if image.ndim == 2:
        image = image[..., np.newaxis]
    rng = np.random.RandomState(seed)
    h, w = image.shape[:2]

    pil = Image.fromarray((image[..., 0] * 255).astype(np.uint8))

    angle = rng.uniform(-3, 3)
    pil = pil.rotate(angle, fillcolor=0, expand=False)

    brightness = rng.uniform(0.9, 1.1)
    arr = np.asarray(pil, dtype=np.float32) * brightness
    arr = np.clip(arr, 0, 255) / 255.0

    noise = rng.normal(0, 0.02, arr.shape)
    arr = np.clip(arr + noise, 0, 1)

    return arr[..., np.newaxis].astype(np.float32)
