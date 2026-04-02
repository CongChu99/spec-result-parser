# MASTER: spec-result-parser Design System

> Terminal Scientific aesthetic — dark, precise, monospace-first. No glassmorphism, no gradients.
> Inspired by oscilloscope displays and GitHub's dark mode; designed for engineers who trust data, not decoration.

## Design Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--bg` | `#0D1117` | Deep page/canvas background (GitHub dark bg level) |
| `--bg-surface` | `#161B22` | Terminal window body background |
| `--bg-panel` | `#1C2128` | Terminal chrome bar, panel headers |
| `--border` | `#30363D` | Window borders, table separators |
| `--fg-primary` | `#E6EDF3` | Primary text, measurement names |
| `--fg-secondary` | `#8B949E` | Secondary text, min/max values |
| `--fg-muted` | `#484F58` | Column headers, timestamps, dim labels |
| `--accent-green` | `#3FB950` | PASS badge text, PASS value, prompt-$ |
| `--accent-green-dim` | `#1B4D26` | PASS badge background |
| `--accent-red` | `#F85149` | FAIL badge text, FAIL values, error messages |
| `--accent-red-dim` | `#4D1C1C` | FAIL row highlight background, FAIL badge bg |
| `--accent-yellow` | `#D29922` | MARGIN badge text, MARGIN values, Worst Case |
| `--accent-yellow-dim` | `#3D2C0A` | MARGIN badge background |
| `--accent-blue` | `#58A6FF` | Verbose debug parsed values |
| `--prompt-green` | `#56D364` | Terminal prompt `$` symbol |
| `--font-heading` | `'Geist Mono', monospace` | Screen labels, table section headers |
| `--font-body` | `'Geist', sans-serif` | Descriptions (not used in CLI mockup) |
| `--font-mono` | `'IBM Plex Mono', monospace` | All measurement data, values, command text |

## Motion Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--duration-fast` | `150ms` | Badge flash on check complete |
| `--duration-normal` | `250ms` | Table row entry on aggregate |
| `--ease-out` | `cubic-bezier(0.16,1,0.3,1)` | Elements entering |
| `--ease-in` | `cubic-bezier(0.7,0,1,1)` | Elements leaving |

> Motion Note: CLI tool — actual animations are in terminal renderer (`rich`). Motion tokens document intent, not implementation.

## Reusable Components

| Component | Variants | Pencil ID |
|-----------|----------|-----------|
| `Comp/Badge/PASS` | — | `Gp8xK` |
| `Comp/Badge/FAIL` | — | `aLyFf` |
| `Comp/Badge/MARGIN` | — | `c5wmF` |
| `Comp/Badge/NA` | — | `E4yR4` |
| `Comp/TerminalWindow` | chrome-bar + chrome-body slot | `t9KFB` |

## Spacing Scale (4pt)

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Badge internal padding, icon gaps |
| `--space-2` | 8px | Cell padding horizontal |
| `--space-3` | 12px | Table body vertical padding |
| `--space-4` | 16px | Panel padding, section gap |
| `--space-6` | 24px | Section separation |
| `--space-8` | 32px | Screen outer padding |

## Screen Dimensions

- **Desktop default**: 720–900px × 500–560px dark canvas frames
- **Platform**: Linux terminal (primary), macOS terminal (secondary)
- **Rendering**: `rich` library in Python — all dimensions map to character-grid layout

## Color Rules (60-30-10)

- **60%** `--bg` / `--bg-surface` — Dark backgrounds dominate
- **30%** `--fg-secondary`, `--fg-muted`, `--border` — Structural text and lines
- **10%** `--accent-green` / `--accent-red` / `--accent-yellow` — Status signals only

Status colors appear **only** in badges and highlighted values. Never used as background for neutral content.

## AI Slop Checklist — PASS ✅

- [x] No gradient text or backgrounds — ✅ flat fills only
- [x] No glassmorphism — ✅ solid surface fills
- [x] No pure gray neutrals — ✅ all neutrals are tinted (`#30363D`, `#484F58`)
- [x] No hero metric layout — ✅ data table layout, not big-number cards
- [x] No Inter/Roboto/Arial — ✅ Geist Mono + IBM Plex Mono
- [x] No rounded rectangles with generic shadows — ✅ sharp corners on tables, subtle border strokes

## File

- Pencil file: `docs/c4flow/designs/spec-result-parser/spec-result-parser.pen`
- Design System Frame ID: `Jjdwi`
- Screen 1 (check PASS): `XbzS5`
- Screen 2 (check FAIL+MARGIN): `Nb5io`
- Screen 3 (aggregate matrix): `jERgt`
- Screen 4 (error+verbose): `GMksV`
