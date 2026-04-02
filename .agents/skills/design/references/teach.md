# Teach Step — Design Context Gathering

## Purpose

Before generating any design system, gather persistent design context for the project. This context informs all design decisions and is saved to `.impeccable.md` at the project root (or `docs/specs/<feature>/context.md` if running within a c4flow workflow).

## Step 1: Auto-Parse Existing Context

Scan these files automatically — don't ask the user:

```
README.md
package.json / pyproject.toml
src/**/*.{css,scss,styles}
docs/**/*.md
 CLAUDE.md
 .cursorrules
 components/ (file names + structure)
```

Extract and **recommend** the following, derived from the files:

| Field | Source |
|-------|--------|
| **Product type** | README, spec.md |
| **Target users** | README, spec.md |
| **Brand personality** | Colors, fonts, tone of existing docs |
| **Design tokens already in use** | CSS variables, design tokens |
| **Accessibility needs** | Any a11y mentions, WCAG targets |
| **Tech constraints** | package.json (React/Vue/etc.), styling approach |
| **Design system in use** | Existing component libraries, token files |

## Step 2: Recommend, Don't Ask

Present findings in this format:

---

**Design Context — Recommended**

> **Product type:** [parsed from README/spec]
> **Target users:** [parsed]
> **Brand personality:** [parsed — e.g., "Professional, minimal, trustworthy"]
> **Aesthetic direction:** [parsed — note any existing colors, fonts, visual patterns]
> **Design tokens:** [list existing CSS variables/tokens]
> **Accessibility target:** WCAG AA (default) / WCAG AAA / custom
> **Tech stack:** [parsed from package.json]
> **Design system:** [detected or "none"]
>
> ⚠️ **Missing:** [anything that couldn't be inferred]

---

If key fields are missing or uncertain, add **1-2 specific recommendations** rather than open-ended questions.

## Step 3: User Edits / Approves

User can:
- Edit any field directly
- Add missing context
- Approve as-is

After approval, save to `.impeccable.md` (project root) or `docs/specs/<feature>/context.md` (c4flow flow).

## Context Template

```markdown
# Design Context

> Auto-generated from /teach step — edit freely

## Product
- **Type:** ...
- **Target users:** ...
- **Core value:** ...

## Brand
- **Personality:** [3 words — e.g., "Professional, minimal, trustworthy"]
- **Emotional goal:** [how should users feel?]
- **Aesthetic direction:** [minimal, bold, playful, editorial, brutalist...]
- **Anti-references:** [what to avoid — e.g., "no gradients, no shadows"]`

## Guiding Principles
- [3-5 short principles that guide design decisions]
- [e.g., "Content first, chrome second"]
- [e.g., "Motion should feel physical, not digital"]
```

## Re-running Teach

If context already exists at `.impeccable.md` or `docs/specs/<feature>/context.md`, skip Step 1–2. Ask: "Design context exists. Re-run teach step to update it?"
- **Yes** → overwrite with fresh parse + recommendations
- **No** → use existing context

## c4flow Integration

When running inside the c4flow workflow, the context is saved to `docs/specs/<feature>/context.md` and includes a link back to the spec:
```markdown
> Spec: docs/specs/<feature>/spec.md
> Generated: YYYY-MM-DD
```
