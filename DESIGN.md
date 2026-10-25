---
name: Handwriting Analyser
description: An editorial document tool for local handwriting transcription.
colors:
  background: "#f8f9fc"
  paper: "#ffffff"
  ink: "#202b3d"
  muted: "#637087"
  blue: "#355ce7"
  blue-hover: "#254bcf"
  line: "#dce2eb"
  surface: "#f0f3f9"
  selected-line: "#f6f8ff"
  selected-line-border: "#d9e2fb"
  selected-history: "#edf2ff"
typography:
  display:
    fontFamily: '"Source Sans 3", sans-serif'
    fontSize: "58px"
    fontWeight: 500
    lineHeight: 1.08
    letterSpacing: "-2.2px"
  headline:
    fontFamily: '"Source Sans 3", sans-serif'
    fontSize: "41px"
    fontWeight: 500
    lineHeight: 1.14
    letterSpacing: "-1.1px"
  title:
    fontFamily: '"Source Sans 3", sans-serif'
    fontSize: "30px"
    fontWeight: 500
    letterSpacing: "-0.7px"
  body:
    fontFamily: '"Source Sans 3", sans-serif'
    fontSize: "16px"
    lineHeight: 1.5
  label:
    fontFamily: '"Source Sans 3", sans-serif'
    fontSize: "13px"
    fontWeight: 500
rounded:
  field: "5px"
  icon: "6px"
  control: "7px"
  editor: "9px"
  settings: "10px"
  upload: "12px"
spacing:
  gutter-desktop: "56px"
  gutter-compact: "35px"
  gutter-mobile: "24px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "15px 23px"
  button-primary-hover:
    backgroundColor: "{colors.blue-hover}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "15px 23px"
  field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "10px 11px"
---

# Design System: Handwriting Analyser

## Overview

The approved direction is an editorial document tool: paper-white surfaces, ink-dark text, restrained blue, and document content as the focal material. Spacious storytelling introduces the product; the studio uses a denser working rhythm within the same identity. Source Sans 3 and Phosphor icons connect both surfaces.

Local processing, checking, and correction constrain the visual language: distinguish illustrative transformation, dataset reference, and actual recognition output. Surface-specific composition lives in `.impeccable/surfaces/landing.md`.

**Key Characteristics:**

- Paper and text provide the main visual material.
- Blue marks actions, selection, and source-to-text relationships.
- Quiet dividers organize working controls.
- Motion explains transformation and respects reduced motion.

## Colors

The frontmatter records reusable colors observed in `frontend/src/style.css`; that stylesheet remains the implementation source. The palette uses one primary accent and cool neutrals.

### Primary

Restrained blue marks primary actions, active tabs, image regions, and focus. Its deeper hover shade gives actions a clear response. Selected transcript lines and history items use pale blue surfaces rather than saturated fills.

### Neutral

Paper white carries documents, fields, and studio panels. Cool background separates working surfaces. Ink is the reading color; muted serves hints, line numbers, and raw model scores. Line separates regions without competing with the page. The supporting surface token is pale; contextual fills also include the studio background (`#f7f9fc`) and source panel (`#f0f2f7`).

**The Readable Metadata Rule.** Line numbers and scores use the shared muted color, including selected lines. Final reviewed contrast is approximately 5:1 on white and 4.7:1 on the selected-line fill; preserve these pairings.

## Typography

Source Sans 3 is self-hosted through the local font package: Latin weights 400, 500, 600, and 700 are loaded in `frontend/src/main.tsx`. The fallback is sans-serif. Use Phosphor consistently; default icons are 20px, with contextual size variants.

The frontmatter captures desktop hierarchy. Display and section headlines use medium weight and tight spacing; studio titles are smaller to prioritize working content. Action labels generally use 600. Landing display changes to 49px at 1150px and 44px at 900px; the 641–800px override uses 55px. Mobile display is 47px, section headlines 34px, and the closing title 31px. Transcript editing remains 16px with 1.6 line height. Metadata ranges from 10–13px; preserve its contrast and grouping.

## Layout

The landing container is capped at 1320px including gutters. Gutters step to compact at 1150px and mobile at 640px. The first composition is asymmetric; the 641–800px override stacks manuscript below copy. At 640px and below, storytelling sections stack and the workflow becomes one column. Navigation links hide at 900px while the workspace action remains. At 1600px the hero and backdrop grow.

The studio has a 76px header and a 245px history sidebar, falling to 205px at 1150px and 175px at 900px. Workspace width is capped at 1600px, with desktop padding of 35px 38px 60px. Source and transcript share equal-width panels, stacking at 900px. At 640px, the header is 65px, history scrolls horizontally, settings become one column, and Original/Transcript tabs show one panel at a time. Workspace padding becomes 25px 18px 45px.

**The Reachable Restart Rule.** Keep the labeled New transcription action visible above mobile history, including when a completed document is open. Source zoom scrolls inside its panel without expanding page width.

## Elevation & Depth

Working panels use white surfaces, cool fills, and fine borders. Soft shadows chiefly describe document material: manuscript `0 12px 45px #263a6510`, floating transcript `0 20px 60px #263a651c`, comparison page `0 12px 35px #263a6508`, and source preview `0 3px 14px #263a650e`. The secondary action's inset stroke is `inset 0 0 0 1px var(--line)`. Do not spread the floating-paper treatment into every studio container.

## Shapes

Controls have gently rounded corners, with observed role-specific radii in frontmatter. Editor panels share a bordered shell with clipped contents; settings and upload surfaces are slightly rounder. The upload target uses a 1.5px dashed border. Manuscript sheets remain rectangular and slightly rotated. Circles serve small status dots, slider thumbs, and the hero backdrop rather than general controls.

## Components

### Buttons and focus

Primary actions use white on blue, medium-bold labels, and a 14px icon gap. Small buttons use 10px 15px padding, 14px type, and an 8px gap. Secondary actions use paper, ink, and the inset stroke, changing to `#edf1fa` on hover. Text actions become blue on hover. Icon buttons are normally 34px square, with a pale blue hover/pressed fill. Disabled buttons use 0.45 opacity and a not-allowed cursor.

Primary hover darkens the fill and moves upward 1px; background and transform transition over 180ms. Focus-visible controls, links, summaries, and keyboard targets use a 3px blue outline offset by 4px; line-editing textareas use a closer offset.

### Fields and settings

Fields are white with a fine `#d6deeb` border and the frontmatter field shape/padding. Labels sit above inputs; checkboxes use blue. Advanced settings disclose below a divider. Setup-needed notices sit beside affected settings. Error alerts use warm fill/text (`#fff0ec`, `#873c30`); informational notices use blue (`#eaf0ff`, `#304e92`).

### History and view navigation

History rows combine document icon, ellipsized title, and date/status metadata. Hover and selection share selected-history fill and deep blue text. The landing comparison uses a compact segmented control with a white selected segment. Mobile studio tabs have a blue 2px underline and blue text for the active view, retaining explicit labels.

### Source and transcript

Selected image polygons use blue strokes and translucent fills; selected transcript rows use the selected-line fill and border. Selection links image coordinates to editable text. Image polygons and crop corners support keyboard access. The source owns scrolling/zoom; the transcript has its own scrolling region and export footer. Scores remain explicitly uncalibrated, with review hints and split-line warnings where relevant.

Editing supports local autosave, undo/redo, revision checks, and save-before-export ordering. Empty, processing, setup-needed, failed, partial, and completed states remain explicit. Processing uses actual stages; indeterminate progress uses a moving band rather than a fabricated percentage.

### Motion

Landing/studio fades use 180ms. Illustrative line detection and floating transcript each loop over 7 seconds; detections stagger by 300ms and the transcript moves 5px vertically. The caret cycles every 1.5 seconds. Progress uses a 2-second indeterminate cycle and 300ms determinate-width transition; source zoom width transitions over 150ms.

MotionConfig respects user preferences, landing loops consult useReducedMotion, and the CSS reduced-motion query removes animations, transitions, and smooth scrolling. Essential status text remains understandable with animation removed.

## Do's and Don'ts

- **Do** preserve paper/ink/blue across storytelling and working views.
- **Do** keep mobile New transcription visible and metadata readable on white and selected rows.
- **Do** use real image coordinates and linked source/transcript selection.
- **Do** retain illustrative/reference labels and honest readiness states.
- **Don't** imply calibrated accuracy from raw scores or illustration.
- **Don't** introduce competing icons, remote fonts, or heavy studio-panel shadows.
- **Don't** depend on motion alone to communicate processing or selection.

Documentation handoff: merged from the approved direction and finished source on 2026-10-23. The existing version-1 `.impeccable/design.json` summary is verified and retained without assuming a different project schema. Its white `surface` means paper; CSS `--surface` means the supporting pale fill recorded above. Pre-existing repository drift outside this handoff is not repaired. Evidence and review limitations are recorded in the surface brief.
