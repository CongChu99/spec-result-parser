---
source: Adapted from Impeccable (github.com/pbakaus/impeccable) — Apache 2.0 License
---

# Design Principles

## Context Gathering Protocol

Design skills produce generic output without project context. Before any design work, confirm:

- **Target audience**: Who uses this product and in what context?
- **Use cases**: What jobs are they trying to get done?
- **Brand personality/tone**: How should the interface feel?

**You cannot infer this from the codebase.** Code tells you what was built, not who it's for.

Context sources (in order):
1. Current session context (spec.md, design.md, proposal.md)
2. User Q&A during Step 1.1 screen analysis
3. If still unclear, ask the user directly before proceeding

## Design Direction

Commit to a BOLD aesthetic direction. Pick an extreme and execute it with precision:
- Brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined
- Playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel
- Industrial/utilitarian, geometric precision, warm humanist, cold corporate, etc.

Bold maximalism and refined minimalism both work — the key is **intentionality**, not intensity.

**Ask yourself**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

## The AI Slop Test

**Critical quality check before presenting any work to the user.**

If you showed this interface to someone and said "AI made this," would they believe you immediately? If yes, that's the problem.

A distinctive interface should make someone ask "how was this made?" not "which AI made this?"

## Typography DO/DON'T

**DO**: Use a modular type scale with 5 levels max (caption, secondary, body, subheading, heading)
**DO**: Pair fonts with genuine contrast (serif + sans, geometric + humanist)
**DO**: Vary font weights and sizes to create clear visual hierarchy
**DON'T**: Use overused fonts — Inter, Roboto, Arial, Open Sans, Lato, Montserrat
**DON'T**: Use monospace typography as lazy shorthand for "technical" vibes
**DON'T**: Put large icons with rounded corners above every heading

Better alternatives:
- Instead of Inter → Instrument Sans, Plus Jakarta Sans, Outfit
- Instead of Roboto → Onest, Figtree, Urbanist
- Instead of Open Sans → Source Sans 3, Nunito Sans, DM Sans
- For editorial/premium → Fraunces, Newsreader, Lora

## Color DO/DON'T

**DO**: Use OKLCH for all colors — perceptually uniform
**DO**: Tint neutrals toward brand hue (chroma 0.01 is enough)
**DO**: Use 60-30-10 rule for visual weight
**DON'T**: Use pure black (#000) or pure white (#fff) — always tint
**DON'T**: Use pure gray neutrals — add subtle color tint
**DON'T**: Put gray text on colored backgrounds — use a shade of the background color
**DON'T**: Use the AI color palette: cyan-on-dark, purple-to-blue gradients, neon accents on dark
**DON'T**: Use gradient text for "impact" — especially on metrics or headings
**DON'T**: Default to dark mode with glowing accents

## Layout DO/DON'T

**DO**: Create visual rhythm through varied spacing — tight groupings, generous separations
**DO**: Use asymmetry and unexpected compositions — break the grid intentionally for emphasis
**DON'T**: Wrap everything in cards — not everything needs a container
**DON'T**: Nest cards inside cards — flatten the hierarchy
**DON'T**: Use identical card grids — same-sized cards with icon + heading + text, repeated endlessly
**DON'T**: Use the hero metric layout — big number, small label, supporting stats, gradient accent
**DON'T**: Center everything — left-aligned text with asymmetric layouts feels more designed

## Visual Details DO/DON'T

**DON'T**: Use glassmorphism everywhere — blur effects used decoratively rather than purposefully
**DON'T**: Use rounded elements with thick colored border on one side — lazy accent
**DON'T**: Use sparklines as decoration — tiny charts that convey nothing meaningful
**DON'T**: Use rounded rectangles with generic drop shadows — safe, forgettable
**DON'T**: Use modals unless there is truly no better alternative

## Motion DO/DON'T

**DO**: Use exponential easing (ease-out-quart/quint/expo) for natural deceleration
**DO**: Use motion to convey state changes — entrances, exits, feedback
**DON'T**: Animate layout properties (width, height, padding, margin) — use transform and opacity only
**DON'T**: Use bounce or elastic easing — they feel dated and tacky
