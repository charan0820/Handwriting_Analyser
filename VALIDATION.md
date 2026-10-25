# Implementation validation — 23 October 2026

## Automated checks

- Windows / Python 3.12: 24 tests passed.
- Ubuntu 22.04 WSL2 / Python 3.10: 24 tests passed; after adding the final GPU-exhaustion recovery case, all 10 application tests passed (25 distinct tests verified in total; one upstream AnyIO deprecation warning).
- TypeScript checks and Vite production build passed.
- npm dependency audit after patching Vite: zero reported vulnerabilities.
- Dataset audit: 10,373 samples; 6,482 source train, 976 validation, 2,915 test; 856 labels with unsupported characters or impossible fixed-width CTC targets; no missing image files. Writer separation remains unverified without authoritative writer metadata.

Tests cover existing interfaces, decoding and metrics, EXIF/alpha handling, invalid uploads, settings validation, coordinate transforms, deskew array compatibility, long-line pixel coverage, partition preservation, missing writer IDs, reference metrics, revision conflicts, persistent edits, raw evidence preservation, TXT/DOCX exports, cancellation/deletion, invalid regions, selective rerun, partial processing, and annotated layout recall/order metrics.

## Real-model integration smoke test

Hardware: NVIDIA GeForce RTX 4050 Laptop GPU, 6 GiB. Both local recognizers processed the same assembled six-line IAM sample with Kraken learned detection and baseline rectification in WSL2.

| Recognizer | Detected lines | CER | WER | End-to-end seconds | Peak allocated GPU memory |
| --- | ---: | ---: | ---: | ---: | ---: |
| Project CRNN | 6 | 0.4523 | 0.8491 | 29.766 | 67,781,120 bytes |
| TrOCR handwritten | 6 | 0.0498 | 0.2170 | 49.873 | 1,396,218,368 bytes |

These are integration measurements on one artificial page assembled from dataset line crops. They are **not** generalization accuracy, latency guarantees, or a benchmark of unseen photographed pages. Times include model loading and processing. Both runs flagged segmented long-line joins for review. Line-detection recall/order metrics were not claimed for this fixture because it lacks independent page-layout annotations. Raw run reports are in `.local/wsl-smoke-results.json` and `.local/smoke-results.json`.

## Browser verification

Verified the landing actions, real sample upload, baseline processing, editing a line, explicit save, restoration after refresh, and TXT download through the browser. The full learned engine pipeline was also exercised through the WSL background-job service. API tests separately inspect DOCX archive contents and prove that exports contain the latest edits.

Responsive review captures are in `.impeccable/review/`: 1440px desktop, 390px mobile, approximately 704px browser width, upload studio, and source/text studio views. Initial review found tablet overlap; confirmation captures show the stacked tablet composition. An independent Impeccable finish review requested a persistent mobile upload action and darker small operational text; the verdict pass returned **Ship**, scoring both fixes resolved. That verdict covers those fixes; the earlier full review supplies the broader visual evidence. The Impeccable command-line detector was unavailable; source inspection and screenshot review were used instead.

## Remaining evaluation work

Collect a consented, manually transcribed set of genuine unseen English page photographs covering blur, low resolution, perspective, ruled paper, uneven lighting, and handwriting variation. Annotate line polygons and order where layout metrics are needed, then run `scripts/benchmark.py`. This is required before making broad recognition-quality claims. Tables, equations, multiple scripts, multipage PDFs, batch processing, and searchable PDF exports are deliberately outside the first release.

## Wide-image allocation regression

`train_00761.png` (1398 × 128) exposed an unbounded Kraken internal resize: the default model fixes height at 1800 while retaining aspect ratio. The old longest-edge limit did not prevent a roughly 19,660-pixel-wide tensor and a failed 15,524,944,280-byte allocation. Landscape detection canvases are now padded before that resize, and clear isolated wide text bands bypass page segmentation. Original pixels and detection-to-page coordinates are preserved.

The exact image completed as one line: `people " on no pretext whatsoever , except`. Measured peak process RSS was 2034 MiB, including model loading. All 13 application tests passed, including new checks for extreme-aspect tensor bounds, padding/scale coordinate mapping, and distinguishing single-line from multiline uploads.
