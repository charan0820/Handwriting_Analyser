# Landing and transcription studio

Approved direction: the user's implementation plan in this chat. Code-led build, no reference comp. Landing mode: Persuade. Studio mode: Operate.

First viewport: asymmetric literal headline “Turn handwritten pages into editable documents.” next to real manuscript content and a clearly labeled illustrative transcript. The primary action opens the studio; Try a sample loads a real fixture for actual model processing. Paper-white, ink-dark, restrained blue, self-hosted Source Sans 3, and Phosphor icons govern both surfaces.

Signature interaction: detected manuscript-line outlines lead into a floating digital transcript. This is illustrative; no accuracy claim follows from the animation. Reduced motion removes loops. The operating workspace uses measured stage progress, selected-line synchronization, local persistence, correction, and export.

Responsive evidence required: 1440px desktop, 390px mobile, and the user's approximately 704px browser width. Source/transcript are tabs on mobile; manuscript art stacks below the headline at tablet width to prevent overlap. The studio must preserve keyboard access and clear disabled/setup/error states.

No account flow, cloud transcription, fabricated statistics, signatures, equations, tables, or multilingual claims. IAM sample reference is explicitly dataset ground truth; it is not a model prediction.

## Finished handoff — 2026-10-23

The finished implementation follows this direction. The landing pairs the editorial headline with actual IAM handwriting and an explicitly illustrative floating transcript, followed by three sequential steps, original/reference comparison, and closing transcription action. The 641–800px hero override stacks paper below copy; mobile stacks the remaining sections. The studio retains the palette and typography, adds history/settings, and connects detected image regions to editable transcript lines.

Checked source: `frontend/src/style.css`, `Landing.tsx`, `App.tsx`, and `main.tsx`. Source confirms self-hosted font weights, Phosphor icons, reduced motion, responsive rules, visible mobile New transcription, and shared muted metadata color. Root `DESIGN.md` captures observed tokens and behavior. `.impeccable/design.json` retains its existing version-1 shape and verified compact summary; its `surface` denotes white paper, while CSS `--surface` denotes a separate pale supporting fill.

Visually inspected supplied `.impeccable/review/` evidence: `desktop.png`, `mobile.png`, `user-704.png`, `studio-empty.png`, `studio-desktop.png`, `studio-mobile.png`, and `studio-mobile-text.png`. These cover the requested desktop, mobile, and approximately 704px browser conditions, plus empty/setup-needed and completed studio views, including both mobile tabs. Actual landing image widths are 1429px, 380px, and 693px; these are supplied captures, not newly measured viewport values.

The finish reviewer returned **Ship** after a focused verdict pass resolving two findings: labeled mobile New transcription remains visible, and line numbers/raw scores use `--muted`, approximately 5:1 on white and 4.7:1 on selected transcript rows. The earlier full review accepted world/layout. No automated detector ran because the CLI engine was unavailable. Screenshots provide visual evidence, not backend recognition accuracy or exhaustive interaction testing. This documentation pass ran no build or backend processing.

Pre-existing repository drift remains outside this handoff. This pass changes documentation only and preserves `PRODUCT.md` commitments.
