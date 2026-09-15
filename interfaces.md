# Locked Interfaces — Day 1

These signatures are frozen for Week 1. Any change requires flagging to all three
members before editing, since each function is another member's dependency.

```python
# src/data/dataset.py  (Member 1)
def load_dataset(data_path: str) -> tuple[list[str], list[str]]:
    """Returns (image_paths, ground_truth_texts), aligned by index."""

# src/data/preprocessing.py  (Member 1)
def preprocess_image(image: "np.ndarray") -> "np.ndarray":
    """Returns a normalized (H=64, W=256, 1) float32 array in [0, 1]."""

# src/segmentation/line_segmentation.py  (Member 1)
def segment_text_lines(image: "np.ndarray") -> list["np.ndarray"]:
    """Returns line-crop images, ordered top-to-bottom."""

# src/models/crnn.py  (Member 2)
def build_crnn(num_classes: int) -> "nn.Module":
    """forward(x: (B, 1, 64, 256)) -> logits (T, B, num_classes)."""

# src/training/train.py  (Member 2)
def train_model(model, train_loader, val_loader, config: dict) -> dict:
    """Returns training history dict; saves best checkpoint to config path."""

# src/inference/predict.py  (Member 3)
def recognize_text(image: "np.ndarray", model) -> tuple[str, float]:
    """Returns (predicted_text, confidence_score in [0,1])."""

# src/models/decoder.py  (Member 3)
def decode_predictions(logits: "torch.Tensor", charset: dict) -> list[str]:
    """Greedy CTC decode. logits: (T, B, num_classes) -> batch of strings."""

# src/evaluation/metrics.py  (Member 3)
def calculate_cer(predicted: str, ground_truth: str) -> float:
def calculate_wer(predicted: str, ground_truth: str) -> float:
```

## Fixed decisions (do not revisit without team sign-off)
- Dataset: IAM Handwriting Database, English only
- Image size: 256 (W) x 64 (H), grayscale, normalized [0,1]
- Split strategy: writer-disjoint (no writer's samples span multiple splits)
- Vocabulary: see `charset.json` (67 chars + blank = 68 classes)
- Decoding: greedy CTC for Week 1; beam search is a stretch goal only
