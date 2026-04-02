# Responsive Design

## Mobile-First

Write CSS with `min-width` media queries — start with mobile, add complexity for larger screens.

```css
/* Base: mobile */
.card { flex-direction: column; }

/* Tablet+ */
@media (min-width: 640px) { .card { flex-direction: row; } }

/* Desktop+ */
@media (min-width: 1024px) { .card { max-width: 1024px; } }
```

## Breakpoints

Let content determine breakpoints, not specific devices. Common ranges:
- `< 640px`: mobile
- `640–1024px`: tablet
- `> 1024px`: desktop

Use `clamp()` for fluid scaling between breakpoints.

## Input Detection

Query actual capabilities, not screen size:
- `pointer: fine` vs `coarse` (touch vs mouse)
- `hover: hover` vs `none` (can hover vs cannot)

Touch users can't hover. Don't hide critical information behind hover states.

## Safe Areas

Handle notches and rounded corners:
```html
<meta name="viewport" content="viewport-fit=cover">
```
```css
padding: env(safe-area-inset-top) env(safe-area-inset-right) ...
```

## Images

```html
<!-- Resolution switching -->
<img srcset="hero-400.jpg 400w, hero-800.jpg 800w"
     sizes="(max-width: 640px) 100vw, 50vw"
     src="hero-800.jpg" alt="...">

<!-- Art direction only (different crops) -->
<picture>
  <source media="(min-width: 800px)" srcset="wide.jpg">
  <img src="narrow.jpg" alt="...">
</picture>
```

## Navigation Patterns

Adapt through three stages:
1. **Drawer** (mobile) — hamburger menu
2. **Compact** (tablet) — horizontal compact nav
3. **Full** (desktop) — full navigation bar

## Tables → Cards

Transform data tables to cards on mobile:
```html
<table> → `<div class="card" data-label="Column Name">`
```
Use `data-label` attribute to show column headers alongside cell values.

## Progressive Disclosure

Use `<details>/<summary>` for collapsible content on mobile — native, accessible, no JS needed.

## Test on Real Devices

DevTools misses touch behavior, memory constraints, and font rendering. Cheap Android phones expose issues simulators hide.
