---
source: Adapted from Impeccable (github.com/pbakaus/impeccable) — Apache 2.0 License
---

# Quality Checklist

Run this after EVERY `get_screenshot` call. Fix issues before presenting to user.

## Step 1: AI Slop Detection (CRITICAL — run first)

**This is the most important check.** Does this look like every other AI-generated interface?

Check against these fingerprints of AI-generated work:
- [ ] No cyan-on-dark or purple-to-blue gradients
- [ ] No gradient text on headings or metrics
- [ ] No glassmorphism used decoratively
- [ ] No sparklines as decoration
- [ ] No identical card grids (icon + heading + text, repeated)
- [ ] No hero metric layout (big number, small label, stats, gradient)
- [ ] No rounded rectangles with generic drop shadows
- [ ] No dark mode with glowing neon accents
- [ ] No pure gray neutrals (must be tinted)
- [ ] No pure black (#000) backgrounds

**If any boxes are unchecked → fix before proceeding.**

## Step 2: Visual Hierarchy (Squint Test)

Blur your eyes. Ask:
- [ ] Can you identify the primary element in 2 seconds?
- [ ] Is there a clear second-level element?
- [ ] Are content groupings visible as regions?

## Step 3: Color Contrast

- [ ] Body text contrast ≥ 4.5:1
- [ ] Large text (18px+) contrast ≥ 3:1
- [ ] UI components (buttons, inputs) contrast ≥ 3:1
- [ ] Focus indicators contrast ≥ 3:1 against adjacent colors
- [ ] No gray text on colored backgrounds

## Step 4: Typography

- [ ] No invisible defaults (Inter, Roboto, Arial, Open Sans) unless intentional
- [ ] Clear hierarchy — heading vs body identifiable at a glance
- [ ] Body text ≥ 16px
- [ ] Consistent weights (same role = same weight throughout)

## Step 5: Spacing & Layout

- [ ] Spacing uses the 4pt scale (values from the spacing tokens)
- [ ] Related elements grouped tightly (8-12px), sections separated generously (48-96px)
- [ ] No card nesting (max 1 level)
- [ ] Layout passes squint test for hierarchy

## Step 6: Consistency

- [ ] All colors use design tokens (no hard-coded hex values)
- [ ] Same elements styled the same way throughout
- [ ] Interactive elements have clear affordance
- [ ] Components match the approved design system

## Step 7: Structural Check (via `snapshot_layout`)

After visual check, always call `snapshot_layout({problemsOnly: true})`:
- [ ] No overlapping elements
- [ ] No clipped content
- [ ] No misaligned items

## Pass / Fail Verdict

If ALL boxes are checked → PASS, present to user.
If ANY box is unchecked → FIX first, then re-screenshot, then re-check.

Do NOT present a design to the user that fails the AI Slop Detection check.
