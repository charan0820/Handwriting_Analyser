# Dataset

We use the line-level **IAM Handwriting Database**.

### Option A: Automatic Download via Hugging Face (`Teklia/IAM-line`) — Recommended
You can download the dataset directly without registration using the built-in downloader script:

```bash
# Full dataset download (~265 MB, ~10,300 line images across train/val/test)
python -m src.data.download_dataset

# Quick download for smoke testing (e.g., 200 samples per split)
python -m src.data.download_dataset --sample-limit 200
```

### Option B: Official IAM Manual Download
Download the official `lines` package from: https://fki.tic.heia-fr.ch/databases/iam-handwriting-database
Place it so the structure matches:
```
data/raw/
├── lines.txt        # annotations, IAM format
└── lines/
    ├── a01-000u-00.png
    └── ...
```
`load_dataset()` parses `lines.txt` directly (space-separated, `|` = space in the transcription field, `status=err` rows are skipped).

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

Outputs transcription to `outputs/predictions/<name>_transcription.txt` and annotated visualization to `outputs/visualizations/<name>_annotated.png`.

# Evaluate

```python
from src.evaluation.evaluate import evaluate_batch
evaluate_batch(predictions, ground_truths)  # -> {cer, wer, exact_match, n}
```
