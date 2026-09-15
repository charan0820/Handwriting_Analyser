# Day 1 — Application Architecture (Member 3)

## State flow (fixes the UI contract before Member 1/2 build the pipeline it wraps)

```
UploadedFile
    │
    ▼
PipelineState {
    original_image: np.ndarray
    preprocessed_image: np.ndarray | None
    line_crops: list[np.ndarray] | None
    line_texts: list[str] | None
    line_confidences: list[float] | None
    full_text: str | None
    cer: float | None          # only if ground truth provided
    wer: float | None          # only if ground truth provided
    inference_time_ms: float | None
    error: str | None
}
    │
    ▼
Rendered UI (original | recognized text | CER/WER | export button)
```

## Contract with Member 1 / Member 2
- The app calls `preprocess_image()`, `segment_text_lines()`, `recognize_text()`,
  `decode_predictions()` — never touches model internals or training code directly.
- `recognize_text()` returning `(text, confidence)` per line is the only handoff
  point between inference and UI — the app doesn't need to know CRNN/CTC exist.
- Errors (corrupt upload, blank page, no lines detected) populate `PipelineState.error`
  and short-circuit rendering — no exceptions should propagate to the UI layer.

## Day 1 deliverable
This is a design doc only — `app/app.py` implementation starts Day 14 per the
3-week plan. Nothing here blocks Member 1 or Member 2.
