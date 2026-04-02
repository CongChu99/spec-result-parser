---
source: Adapted from Impeccable (github.com/pbakaus/impeccable) — Apache 2.0 License
---

# Spatial Design

## 4pt Spacing Scale (Not 8pt — Too Coarse)

4pt gives granularity for tight UI without arbitrary values:

```
4 · 8 · 12 · 16 · 24 · 32 · 48 · 64 · 96
```

Pencil variable names: `space-xs` (4), `space-sm` (8), `space-md` (16), `space-lg` (32), `space-xl` (64)

Use `gap` not margins for sibling spacing — eliminates margin collapse hacks.

## Visual Rhythm

Create rhythm through varied spacing — not the same padding everywhere:

- **Tight grouping** (8-12px): Related elements within a component
- **Medium separation** (16-24px): Between items in a list
- **Generous separation** (48-96px): Between distinct page sections

Without rhythm, layouts feel monotonous. Same spacing everywhere = no hierarchy.

## The Squint Test

Blur your eyes (or screenshot and blur). Can you still identify:
1. The most important element?
2. The second most important?
3. Clear content groupings?

If everything looks equal weight when blurred, you have a hierarchy problem.

**Run this test after every screen composition.**

## Card Usage Rules

Cards are overused. Spacing and alignment create visual grouping naturally.

Use cards ONLY when:
- Content is truly distinct and actionable
- Items need visual comparison in a grid
- Content needs clear interaction boundaries

**Never nest cards inside cards** — use spacing, typography, and subtle dividers for hierarchy within a card.

## Screen Dimension Defaults

| Platform | Default Size |
|----------|-------------|
| Web app (desktop) | 1440 × 900 |
| Web app (tablet) | 768 × 1024 |
| Web app (mobile) | 375 × 812 |
| Mobile app (iPhone) | 375 × 812 |
| Mobile app (iPhone Pro) | 390 × 844 |
| Landing page | 1440 × 900+ (scrollable) |
| Landscape | Rotate dimensions (e.g. 812 × 375) |

If `tech-stack.md` specifies a target platform, use that. Otherwise default to 1440 × 900 for web.

## Hierarchy Through Multiple Dimensions

| Dimension | Strong | Weak |
|-----------|--------|------|
| Size | 3:1 ratio+ | <2:1 ratio |
| Weight | Bold vs Regular | Medium vs Regular |
| Color | High contrast | Similar tones |
| Position | Top/left (primary) | Buried |
| Space | Surrounded by whitespace | Crowded |

Best hierarchy uses 2-3 dimensions at once.
