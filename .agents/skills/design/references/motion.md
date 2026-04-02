# Motion Design

## Timing

| Duration | Use case |
|----------|----------|
| 100–150ms | Instant feedback (buttons, toggles) |
| 200–300ms | State changes (menus, tooltips) |
| 300–500ms | Layout changes (accordions, modals) |
| 500–800ms | Entrance animations (page loads) |

Exit animations should be ~75% of enter duration.

## Easing

**Avoid `ease`** — it's a compromise curve.

- `ease-out` for elements entering
- `ease-in` for elements leaving
- `ease-in-out` for state toggles

For micro-interactions, prefer exponential curves (quint, expo) over linear — they mimic real physics.

**Skip bounce and elastic effects.** They feel dated and amateurish. Real objects decelerate smoothly.

```css
/* Prefer */
cubic-bezier(0.16, 1, 0.3, 1); /* ease-out-quint */

/* Avoid */
cubic-bezier(0.68, -0.55, 0.27, 1.55); /* bounce — feels cheap */
```

## Two Properties to Animate

Only animate **`transform`** and **`opacity`** — everything else triggers layout recalculation.

For height animations, use:
```css
grid-template-rows: 0fr → 1fr; /* instead of height: 0 → auto */
```

## Staggering

Use CSS custom properties:
```css
animation-delay: calc(var(--i, 0) * 50ms);
```
Cap total stagger time: 10 items × 50ms = 500ms max.

## Accessibility

`prefers-reduced-motion` is mandatory. ~35% of adults over 40 have vestibular disorders.

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Perceived Performance

- **80ms threshold**: Anything under 80ms feels instant
- Use skeleton screens and optimistic UI updates
- Ease-in can make tasks feel shorter (peak-end effect)
- Too-fast responses may decrease perceived value
