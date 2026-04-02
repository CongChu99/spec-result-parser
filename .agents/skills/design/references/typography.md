---
source: Adapted from Impeccable (github.com/pbakaus/impeccable) — Apache 2.0 License
---

# Typography

## Type Scale — 5 Sizes Max

Use fewer sizes with more contrast. Too many sizes close together = muddy hierarchy.

| Role | Size | Line-height | Letter-spacing |
|------|------|-------------|----------------|
| `--text-h1` | 36px | 1.2 | -0.02em |
| `--text-h2` | 28px | 1.25 | -0.01em |
| `--text-h3` | 22px | 1.3 | 0 |
| `--text-body` | 16px | 1.5 | 0 |
| `--text-small` | 14px | 1.4 | 0 |
| `--text-caption` | 12px | 1.4 | 0.01em |

Use a consistent ratio between levels: 1.25 (major third) or 1.333 (perfect fourth).

## Avoid Invisible Default Fonts

These are everywhere — they make design feel generic:
- Inter, Roboto, Arial, Open Sans, Lato, Montserrat, system-ui without customization

Better alternatives:
- **Body (humanist sans)**: Instrument Sans, Plus Jakarta Sans, Outfit, Figtree, Onest, DM Sans
- **Editorial/premium**: Fraunces (serif), Newsreader (serif), Lora (serif)
- **Geometric sans**: Urbanist, Raleway

## Font Pairing

One well-chosen font family in multiple weights often beats two competing typefaces.

When pairing, contrast on multiple axes:
- Serif + Sans (structure contrast)
- Geometric + Humanist (personality contrast)
- Condensed display + Wide body (proportion contrast)

**Never pair fonts that are similar but not identical** (e.g., two geometric sans-serifs). They create visual tension without clear hierarchy.

## Hierarchy Through Multiple Dimensions

Don't rely on size alone. Combine:
- Size + weight (bold heading, regular body)
- Color (muted secondary text)
- Spacing (more space above heading than below)

## Vertical Rhythm

Line-height × base size = base unit for ALL vertical spacing.
- 16px × 1.5 = 24px base unit
- Spacing values should be multiples: 24px, 48px, 72px

## Readability Rules

- Body text minimum: 16px (never below)
- Optimal line length: 45-75 characters (`max-width: 65ch`)
- Line-height for light on dark: add 0.05-0.1 (text feels lighter, needs more room)
- Use `rem` not `px` for font sizes (respects browser zoom)
- Tabular numbers for data: `font-variant-numeric: tabular-nums`

## Pencil Typography Tokens

In `set_variables()`:
```json
{
  "font-heading": "'Instrument Sans', sans-serif",
  "font-body": "'Plus Jakarta Sans', sans-serif",
  "text-h1-size": 36,
  "text-h2-size": 28,
  "text-h3-size": 22,
  "text-body-size": 16,
  "text-small-size": 14,
  "text-caption-size": 12
}
```
