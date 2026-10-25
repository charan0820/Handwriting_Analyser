# Handwriting Analyser

An entirely local browser application for students and everyday note-taking. Primary job: photograph an English handwritten page, recognize all detected lines, review against the original, and export editable text. No accounts, cloud inference, fabricated quality claims, or automatic linguistic rewriting.

Platform: React browser UI with a FastAPI backend and separate local inference worker. WSL2/Linux is the preferred backend environment. Native Windows supports the explicit simple detector and local recognizers. Models are downloaded during setup and loaded offline during processing.

The landing page persuades through a labeled transformation demonstration. The studio operates: it prioritizes readable text, recoverable processing, source traceability, and fast corrections. Success is an editable, saved, exportable document with warnings for uncertain or incomplete results.
