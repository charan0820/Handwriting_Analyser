# Dataset

Use the **IAM Handwriting Database** (English, line-level, ~13,000 labeled line
images). Free registration required: https://fki.tic.heia-fr.ch/databases/iam-handwriting-database

Download the `lines` package. Place it so the structure matches:
```
data/raw/iam/
├── lines.txt        # annotations, IAM format
└── lines/
    ├── a01-000u-00.png
    ├── a01-000u-01.png
    └── ...
```
`load_dataset()` parses `lines.txt` directly (space-separated, `|` = space in the
transcription field, `status=err` rows are skipped).

# Setup

```bash
pip install torch pillow numpy pyyaml --break-system-packages
```

# Train

```bash
cd handwritten-text-recognition/
python -m src.training.train
```

This reads `config.yaml` (batch_size=32, lr=0.001, epochs=30, early stopping
patience=5), does a writer-disjoint 80/10/10 split, trains the CRNN with CTC
loss, and saves the best checkpoint (lowest validation CER) to
`models/best_model.pth`.

- **GPU recommended** — CPU training works but is slow for 30 epochs on full IAM.
- For a quick smoke test on CPU, point `dataset.raw_path` in `config.yaml` at a
  small subset (e.g. 50 lines) and drop `epochs` to 2–3.

# Run inference on a full document

```bash
python -m src.inference.pipeline path/to/document.jpg
```

Outputs `output.txt` (recognized text) and `annotated.png` (detected line boxes).

# Evaluate

```python
from src.evaluation.evaluate import evaluate_batch
evaluate_batch(predictions, ground_truths)  # -> {cer, wer, exact_match, n}
```
