# Day 1 — Dataset Exploration Notes (Member 1)

## Dataset chosen
IAM Handwriting Database — English, line-level images with ground-truth transcriptions.
- Source: https://fki.tic.heia-fr.ch/databases/iam-handwriting-database (registration required)
- Contains `lines.txt` (ground truth) and per-writer form images already segmented into lines.

## Action items before Day 2
1. Register and download the `lines` package (pre-segmented line images) — this lets us
   skip building our own segmentation for line-level training data and use full documents
   only later for the end-to-end demo (Day 8+).
2. Parse `lines.txt` format:
   ```
   line_id status graylevel components x y w h text
   ```
   `text` uses `|` in place of spaces — must convert back on load.
3. Parse `forms.txt` to get the actual writer ID per form, since line filenames only
   encode form ID, not writer ID directly. Writer ID is required for a writer-disjoint split.
4. Run `explore_dataset.py` once data lands to confirm resolution range and corrupt-file count.

## Known IAM quirks to watch for
- Some line images are near-blank or mislabeled (`status = err` in `lines.txt` — must be excluded).
- Resolution varies significantly per writer/scanner — confirms we need the resize/normalize
  step in `preprocess_image()` rather than assuming uniform input.
- Text ground truth may contain characters outside our locked `charset.json` (rare symbols) —
  flag any line whose text has out-of-vocabulary characters during split, don't silently keep them.

## Proposed split (writer-disjoint, pending real writer IDs)
- 80% writers → train
- 10% writers → validation
- 10% writers → test
- Target: no writer's handwriting appears in more than one split, per `config.yaml`.

## Status: BLOCKED on IAM registration/download
Everyone should treat `explore_dataset.py` output as the Day 2 gate — Member 2/3 do not
need this to proceed with skeleton work, but `load_dataset()` (Day 2) is blocked until
the raw files are in `data/raw/iam/`.
