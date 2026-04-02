---
source: Adapted from Impeccable (github.com/pbakaus/impeccable) — Apache 2.0 License
---

# Color & Contrast

## Use OKLCH, Not HSL

OKLCH is perceptually uniform — equal steps in lightness look equal. HSL is not.

```css
/* OKLCH: lightness (0-100%), chroma (0-0.4+), hue (0-360) */
--primary:       oklch(60% 0.15 250);   /* Blue */
--primary-light: oklch(85% 0.08 250);   /* Same hue, lighter — reduce chroma! */
--primary-dark:  oklch(35% 0.12 250);   /* Same hue, darker */
```

**Key rule**: As you move toward white or black, reduce chroma. High chroma at extreme lightness looks garish (e.g., oklch(90% 0.15 250) is an ugly washed-out blue — use oklch(90% 0.06 250) instead).

## Tinted Neutrals — Never Pure Gray

```css
/* Dead — no personality */
--gray-100: oklch(95% 0 0);

/* Warm-tinted (subtle warmth toward brand) */
--gray-100: oklch(95% 0.01 60);   /* Chroma 0.01 is enough */
--gray-900: oklch(15% 0.01 60);

/* Cool-tinted (tech, professional) */
--gray-100: oklch(95% 0.01 250);
--gray-900: oklch(15% 0.01 250);
```

Never use pure black (`#000`) or pure white (`#fff`) for large areas. Even chroma 0.005 feels natural.

## Required Color Tokens

| Role | Pencil Variable Name | Purpose |
|------|---------------------|---------|
| Primary | `--primary` | CTAs, links, key actions |
| Background | `--bg` | Page background |
| Foreground | `--fg` | Body text |
| Muted | `--muted` | Secondary text |
| Border | `--border` | Borders, dividers |
| Card | `--card` | Card/surface backgrounds |
| Destructive | `--destructive` | Errors, delete actions |
| Success | `--success` | Confirmations |
| Warning | `--warning` | Warnings |

## 60-30-10 Rule (Visual Weight)

- **60%** Neutral backgrounds, white space, base surfaces
- **30%** Secondary — text, borders, inactive states
- **10%** Accent — CTAs, highlights, focus states

Overusing accent color kills its power. Rare = powerful.

## WCAG Contrast Requirements

| Content | AA Minimum | AAA Target |
|---------|------------|------------|
| Body text | 4.5:1 | 7:1 |
| Large text (18px+ or 14px bold) | 3:1 | 4.5:1 |
| UI components, icons | 3:1 | 4.5:1 |
| Placeholders | 4.5:1 | — |

**Gray text on colored backgrounds always fails** — use a darker shade of the background color or transparency instead.

## Dark Mode

Dark mode requires different decisions, not just inverted colors:

| Light Mode | Dark Mode |
|------------|-----------|
| Shadows for depth | Lighter surfaces for depth |
| Dark text on light | Light text on dark (reduce font weight slightly) |
| Vibrant accents | Desaturate accents slightly |
| White backgrounds | Never pure black — use oklch(12-18% 0.01 250) |

Use semantic tokens (redefine `--bg`, `--fg`, `--card` per theme) not primitive tokens.
