import numpy as np
import torch

from src.models.crnn import build_crnn

NUM_CLASSES = 68  # 67 chars + blank, charset.json


def run():
    dummy_preprocessed = np.random.rand(4, 64, 256, 1).astype(np.float32)  # (B,H,W,1)
    x = torch.from_numpy(dummy_preprocessed).permute(0, 3, 1, 2)  # -> (B,1,H,W)

    model = build_crnn(NUM_CLASSES)
    logits = model(x)
    print("input", x.shape, "-> output", logits.shape)
    assert logits.shape[1] == 4 and logits.shape[2] == NUM_CLASSES
    print("OK: preprocessing output shape is model-compatible")


if __name__ == "__main__":
    run()
