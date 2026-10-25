# Handwriting Analyser

A local application for converting photographs of English handwritten notes into editable TXT and DOCX documents. The React landing page opens a review studio with page correction, automatic line detection, model inference, synchronized line overlays, autosaved edits, and local history.

## Quick start: Windows + WSL2

Use Ubuntu 22.04/24.04 in WSL2 and Python 3.10–3.12. Keep the checkout in the Linux filesystem for better model performance. The Windows checkout is also accessible under `/mnt/c/Users/chara/OneDrive/Documents/VASAVI/Projects/SEM5/Handwriting_Analyser` (quote the path if it contains spaces). The supplied WSL scripts keep Python packages in the Linux filesystem even when the checkout is on Windows. Default document storage also lives outside the checkout and OneDrive.

```bash
sudo apt update
sudo apt install python3-venv
bash scripts/setup_wsl.sh
cd frontend
npm ci
npm run build
cd ..
bash scripts/start_wsl.sh
```

Install Node.js 22 or 24 in WSL before running `npm`, or build the frontend with Windows Node and then run the backend in WSL. Open [the local application](http://localhost:8000) in your Windows browser. The server binds to loopback only. The WSL setup installs `requirements-wsl.lock`, captured from the validated environment; `requirements-wsl.txt` lists the direct dependency constraints for intentional upgrades. Kraken 6.0 ships its default learned segmentation model with the package; TrOCR downloads explicitly during `setup_models.py`. Processing thereafter uses cached models without cloud calls. The application does not automatically install WSL, change Windows features, or download weights while processing.

On this computer the validated environment is in **Ubuntu-22.04**. From PowerShell in the project folder, restart it with `wsl -d Ubuntu-22.04 -- bash scripts/start_wsl.sh`. Its Python environment is under `/root/.local/share/handwriting-analyser/venv` in that distribution.

For GPU recognition, the WSL distribution must see the NVIDIA device (`nvidia-smi`). If PyTorch reports no CUDA device, the app runs on CPU. Recognition runs one line segment at a time; CUDA out-of-memory triggers a CPU retry. Detection uses CPU to conserve GPU memory. First model load can take time.

### Native Windows baseline

```powershell
python -m pip install -r requirements.txt
cd frontend
npm.cmd ci
npm.cmd run build
cd ..
python scripts/serve.py
```

Select **Project CRNN** and **Simple straight lines (baseline)** explicitly in the studio. The baseline needs `models/best_model.pth` and `charset.json`. TrOCR can also run on Windows after model setup; Kraken is intended for WSL/Linux. The simple detector is useful for clean straight lines and does not offer Kraken's learned segmentation quality.

### Development

Run `python scripts/serve.py` in one terminal and `cd frontend && npm run dev` in another. Open Vite's printed localhost URL. Its proxy keeps API requests on the same browser origin. Use `127.0.0.1:5173` rather than a LAN address. For production, build first and restart the backend so it mounts `frontend/dist`.

## Using the studio

1. Choose, drop, or paste a PNG/JPEG. Defaults permit 50 MiB and 100 megapixels; corrupt images are rejected. EXIF rotation and transparent backgrounds are normalized.
2. Set the title, recognition engine, detector, contrast preset, and output layout. Missing models are visibly labeled. Advanced controls are limited to options supported by that engine.
3. Use the crop tool to drag the four page corners (or focus a corner and use arrow keys). Crop coordinates refer to the original unrotated page. Rotate after cropping; automatic deskew is also available.
4. Transcribe. The progress bar reports real stages and recognized-line counts. Cancel between line segments; completed lines remain available. Jobs survive page refresh, and interrupted jobs can be retried after a server restart.
5. Select a source region or text line, edit its transcription, mark it reviewed, or change its paragraph boundary. Edits autosave after a short pause. Save conflicts return an explicit error instead of overwriting newer revisions.
6. Use + on the prepared page to draw a missing region. Adjust its bounds, change reading order, delete it, or rerun the selected line. A rerun replaces that line's text, so save any desired version first. Raw model output is retained separately from user corrections.
7. Copy, download TXT, or download DOCX. Downloads wait for pending edits to save. Find/replace, reference evaluation, model details, and deletion are below the editor.

Model scores are uncalibrated signals for prioritizing review, not accuracy percentages. CER/WER appear only when reference text is supplied. No spelling rewriting or external language model is applied.

## Storage and interfaces

Default storage is `%LOCALAPPDATA%/handwriting-analyser/documents` on Windows or `~/.local/share/handwriting-analyser/documents` in WSL/Linux: SQLite jobs/revisions plus original upload bytes, EXIF-normalized original image, prepared page, and line crops. Deleting a document removes its job, revisions, and artifacts. These defaults avoid the repository's OneDrive location. If you override storage to a synced directory, the operating system's sync software may still copy it.

Environment options:

| Variable | Default | Purpose |
| --- | --- | --- |
| `HTR_DATA_DIR` | OS local application-data directory | Database and image storage; use a nonsynced location for privacy |
| `HTR_MODEL_DIR` | `models/trocr-base-handwritten` | Local TrOCR model and processor |
| `HTR_MAX_UPLOAD_MB` | `50` | Backend compressed upload limit in MiB |
| `HTR_MAX_MEGAPIXELS` | `100` | Decoded image safety limit |

API documentation is at [localhost:8000/docs](http://localhost:8000/docs). Jobs expose list/create/detail, SSE progress, cancel/retry, revision-checked document edits, selected-line rerun, image retrieval, TXT/DOCX export, and deletion. `/api/models` reports actual engine availability. Document results use `schema_version: 1`; polygons are in prepared-page pixels and the 3×3 transform maps EXIF-normalized original pixels to that page. The `lines` array defines reading order. Revision history stores user edits; raw model output is maintained on each line. The SQLite queue has one separately spawned worker process; run a single API instance and do not enable Uvicorn multiworker mode.

## Evaluation and training integrity

```bash
python scripts/audit_dataset.py
python -m pytest tests -q
python scripts/benchmark.py /path/to/held-out-pages.json
```

The benchmark manifest is an array such as:

```json
[{"image":"page01.png","text":"Verified reference transcription"}]
```

Images resolve relative to the manifest. The command runs both recognizers against the same pages and records CER, WER, timing, peak GPU allocation, detected-line counts, and warnings. Add `regions`, an array of original-image line polygons in reading order, to measure line recall, precision, and reading-order inversions. Each polygon is an array of `[x,y]` points in EXIF-normalized original-image pixels. Evaluation maps these through page correction, matches polygons one-to-one at IoU ≥ 0.5 using a bounded raster, and reports the matching parameters. Layout metrics remain absent without annotations. Do not use the bundled sample for a claimed generalization score.

The dataset audit records source partition counts, unsupported characters, impossible CTC labels, and missing image files. Training preserves the downloaded source partitions. For official IAM filenames, use `dataset.split_strategy: verified_writer` plus `dataset.writer_metadata`, a JSON object mapping each sample stem to its authoritative writer ID. The old `writer_disjoint_split` function remains for interface compatibility but is a form grouping heuristic, not verified writer separation.

The fixed CRNN has 63 output timesteps. A CTC target needs `len(text)` plus one timestep for each adjacent repeated character. Training now rejects impossible targets and unsupported characters instead of silently dropping evidence. To retrain on all lines, implement variable-width padded training or explicitly prepare labeled shorter segments; merely ignoring invalid targets is not a model improvement. The previous checkpoint is preserved. Its stored validation CER (~0.247) predates corrected split handling and is not an application quality claim.

## Bundled sample and limitations

`frontend/public/sample.png` assembles six real IAM test-line crops. `sample.json` contains their dataset reference and identifiers. It is a demonstration fixture, not a model prediction or an unseen full-page benchmark. `scripts/prepare_sample.py` regenerates it from local IAM data. IAM's research-use terms apply; review them before redistributing the sample or deploying beyond the student/research setting. TrOCR weights are published under MIT; Kraken is Apache-2.0. See their upstream distributions for license texts.

First release targets English, predominantly single-column notes. Low resolution, blur, touching lines, curved pages, and unusual handwriting can reduce quality. Long lines are split near low-ink columns with no pixels discarded and joins are flagged for review. Paragraph boundaries are heuristic and editable. Multi-column layout, multilingual scripts, equations, tables, multipage PDF import, batch processing, and searchable PDF export remain future work. A completed job means processing finished, not that every word is verified.

Wide, already-segmented uploads with one clear text band go directly to line recognition. Other landscape inputs receive white padding on the detection canvas before Kraken's fixed-height resize; this bounds internal tensor width without stretching the original text. Detection coordinates are mapped back through that padding and the preview scale. This prevents thin line images from expanding into extremely wide page-detection tensors.
