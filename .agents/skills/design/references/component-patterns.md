---
source: Adapted from Impeccable (github.com/pbakaus/impeccable) — Apache 2.0 License
---

# Component Patterns

## The Eight Interaction States

Every interactive component needs all states designed. Missing states create broken experiences.

| State | When | Visual Treatment |
|-------|------|-----------------|
| Default | At rest | Base styling |
| Hover | Pointer over | Subtle lift, color shift |
| Focus | Keyboard/programmatic | Visible ring (2-3px, offset) |
| Active | Being pressed | Pressed in, darker fill |
| Disabled | Not interactive | Reduced opacity, no pointer |
| Loading | Processing async action | Spinner or skeleton |
| Error | Invalid/failed state | Destructive color, message |
| Success | Completed | Success color, confirmation |

**The common miss**: Designing hover without focus. Keyboard users never see hover states — they are different and both required.

## Focus Rings

Never remove focus indicators without replacement. Use `:focus-visible` to show only for keyboard:

Focus ring design rules:
- 2-3px thick, offset from element (not inside)
- High contrast: 3:1 minimum against adjacent colors
- Use `--primary` or `--accent` color
- Consistent across ALL interactive elements

## Form Design

- Labels are always visible — placeholders are NOT labels (they disappear on input)
- Validate on blur, not on keystroke (exception: password strength)
- Error messages below fields with clear description
- Required indicators consistent and clear

## Loading States

- Skeleton screens > spinners — they preview content shape and feel faster
- Optimistic updates for low-stakes actions (likes, toggles) — update immediately, rollback on failure
- Never use optimistic updates for payments, destructive actions, or irreversible operations

## Destructive Actions

Undo toast > confirmation dialog. Users click through confirmations mindlessly.

Pattern: Remove from UI → show undo toast (5 seconds) → actually delete on expiry.

Use confirmation dialog ONLY for: truly irreversible actions, high-cost actions, batch operations.

## Motion Rules for Components

Duration guidelines:
- 100-150ms: Instant feedback (button press, toggle, color change)
- 200-300ms: State changes (menu open, tooltip, hover state)
- 300-500ms: Layout changes (accordion, drawer)

Easing:
- ease-out (cubic-bezier(0.16, 1, 0.3, 1)): Elements entering
- ease-in: Elements leaving
- ease-in-out: State toggles

**Never**: bounce, elastic, or spring easing. They feel dated. Real objects decelerate smoothly.
**Only animate**: transform and opacity. Never width/height/padding/margin.
For height: animate `grid-template-rows: 0fr → 1fr` instead.

Always respect `prefers-reduced-motion`.

## Empty States

Empty states should TEACH the interface, not just say "nothing here."

Good empty state:
- Explains what this area is for
- Shows the action to get started
- Has a CTA button or link

Bad empty state: Just "No items found."

## Progressive Disclosure

Start simple, reveal sophistication through interaction:
- Basic options first, advanced behind expandable sections
- Hover states that reveal secondary actions
- Not every button should be primary — use ghost, text links, secondary styles
- Hierarchy matters: one primary action per screen area
