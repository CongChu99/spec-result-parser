---
name: c4flow:design
description: Generate design system and UI mockups for a feature using Pencil MCP. Runs after SPEC phase, before BEADS. Produces MASTER.md (design tokens), screen-map.md (screen breakdown), and a .pen file with reusable components and screen frames. Use when the workflow reaches DESIGN state or user asks to design screens/UI. Integrates impeccable best practices OKLCH colors, tinted neutrals, modular typography, spatial rhythm, motion tokens, 8-state component design, and UX writing.
---

# /c4flow:design — Design System + Mockups

**Phase**: 2: Design & Beads
**Agent type**: Main agent (interactive) + sub-agents (parallel screen composition)
**Status**: Implemented

## Workflow Overview

```
Step 0: Teach   → Auto-parse context → Recommend → User approves
Phase 1:        → Screen map + Design system tokens + Components + Hero screen
Phase 2:        → Remaining screens (sub-agents, parallel)
Phase 3:        → Final review + Gate check → update .state.json → BEADS
```

---

## Step 0: Teach — Auto-Parse, Recommend, Approve

**Before Pencil MCP or any design work**, gather persistent project context.

**Read:** `references/teach.md` for the full protocol.

### 0a: Check for Existing Context

```bash
[ -f "docs/specs/<feature>/context.md" ] && echo "CONTEXT_EXISTS"
[ -f ".impeccable.md" ] && echo "IMMACULATE_EXISTS"
```

- Context exists → ask: "Design context found. Re-run to update, or reuse existing?"
- No context → proceed to 0b

### 0b: Auto-Parse Sources

Scan these files **without asking the user**. Extract what you can:

```
README.md                              # Product type, value prop, users
docs/specs/<feature>/spec.md           # Requirements, constraints
docs/specs/<feature>/proposal.md       # Goals, scope, brand tone
package.json / pyproject.toml          # Tech stack, framework
src/**/*.{css,scss,styles,css.ts}      # Existing tokens, design variables
components/**/*.{tsx,jsx,vue}          # Component names, structure
docs/**/*.md                           # Any existing design docs
 CLAUDE.md / .cursorrules              # Existing design guidance
```

Synthesize into a **Design Context Recommendation**:

---

**Design Context — Recommended**

```
Product type:       [parsed — e.g., SaaS dashboard, e-commerce, developer tool]
Target users:      [parsed — role, tech level, context]
Brand personality:  [3 words — e.g., Professional, minimal, trustworthy]
Aesthetic direction:
  Recommended:      [bold direction based on product type + brand]
  Anti-references: [what to avoid — AI slop patterns to reject]
Design tokens:     [existing CSS variables/tokens found]
Accessibility:     WCAG AA (default) / WCAG AAA / custom target
Tech stack:        [parsed from package.json — framework, styling approach]
Design system:     [detected (Tailwind, MUI, Chakra) or "none"]
```

⚠️ **Couldn't infer:** [list anything missing — user can fill in or accept recommendation]

---

### 0c: User Reviews and Edits

User can edit any field, add missing context, or approve as-is.

After approval, save:

```bash
# Inside c4flow workflow: alongside spec
cp /tmp/context.md "docs/specs/<feature>/context.md"

# Standalone project: project root
cp /tmp/context.md ".impeccable.md"
```

Then proceed to Phase 1.

---

## Prerequisites (Pencil MCP)

Before Phase 1, verify:
1. Pencil MCP is available — call `get_editor_state()`. If it fails: "Design skill requires Pencil MCP. Install from https://docs.pencil.dev/getting-started/ai-integration"
2. `docs/specs/<feature>/spec.md` exists — if not, run SPEC phase first
3. `docs/specs/<feature>/design.md` exists — if not, run SPEC phase first

Read workflow state from `docs/c4flow/.state.json` to get `feature.slug` and `feature.name`.

---

## Partial Resume

Check `docs/c4flow/designs/<slug>/` before starting:

| Existing State | Resume From |
|---|---|
| Directory doesn't exist | Step 1.1 (analyze & screen map) |
| `screen-map.md` exists, no `MASTER.md` | Step 1.2 (design tokens) |
| `MASTER.md` exists, no components in .pen | Step 1.3 (reusable components) |
| Components exist, no screen frames | Step 1.4 (hero screen) |
| Hero screen exists, remaining screens missing | Phase 2 (sub-agents) |
| All screens exist | Phase 3 (final review) |

If resuming, tell user: "Found existing design artifacts. Resuming from [step]. Say 'regenerate' to start over."

---

## Phase 1: Main Agent (Interactive)

### Step 1.1: Analyze & Screen Map

**Goal**: Understand what screens to build and get user approval.

1. Read `skills/design/references/design-principles.md` — Impeccable context gathering + AI slop test
2. Read `docs/specs/<feature>/spec.md` — extract all MUST requirements + scenarios
3. Read `docs/specs/<feature>/design.md` — extract components, data model, API endpoints
4. Read `docs/specs/<feature>/proposal.md` if exists — extract target audience, brand tone
5. Read `skills/design/references/ux-writing.md` — for UX writing guidelines
6. Group requirements into screens:
   - Each major user flow → 1 screen group
   - Each MUST requirement needing UI → at least 1 screen
   - Shared elements (nav, sidebar) → note for component list
7. Draft screen map and present to user:
   ```
   I've analyzed the spec and propose these screens:

   [Auth Flow] (3 screens): Login, Register, Forgot Password
   [Dashboard] (2 screens): Overview, Analytics
   [Feature X] (3 screens): List, Create, Detail

   Shared components needed: Nav, Sidebar, Button, Input, Card, Badge, Table, Modal

   Does this look right? Want to add, remove, or merge any screens?
   ```
8. Iterate until user approves
9. Create directory: `docs/c4flow/designs/<slug>/`
10. Write `docs/c4flow/designs/<slug>/screen-map.md`:
```markdown
# Screen Map: <feature-name>

## <Flow Name> (N screens)

### <Screen Name> — <frame-name>
- **Components:** Nav, Input×2, Button(primary)
- **Spec refs:** spec.md#<section>
- **Notes:** <layout or interaction notes>
```

### Step 1.2: Design System Tokens

**Goal**: Create project-specific design tokens, save to `.pen` file and `MASTER.md`.

1. Read `skills/design/references/color-and-contrast.md` — OKLCH, tinted neutrals, 60-30-10
2. Read `skills/design/references/typography.md` — modular scale, font pairing
3. Read `skills/design/references/spatial-design.md` — 4pt scale, rhythm
4. Read `skills/design/references/quality-checklist.md` — AI slop detection
5. Call `get_style_guide_tags()` → get available tags
6. Select tags based on feature (webapp/mobile/landing-page + mood tags)
7. Call `get_style_guide(name: <chosen-guide>)` → get style inspiration
8. Call `get_guidelines(topic: "design-system")` → get Pencil schema rules
9. Design tokens following Impeccable principles:
   - **Colors**: OKLCH, tinted neutrals (chroma 0.01), 60-30-10 rule, no pure black/gray
   - **Typography**: avoid Inter/Roboto/Arial, modular scale (1.25 or 1.333), max 5 sizes
   - **Spacing**: 4pt base (4, 8, 12, 16, 24, 32, 48, 64, 96)
   - **Motion**: ease-out-quint, only transform+opacity, respect prefers-reduced-motion
10. Call `open_document("new")` → creates new `.pen` file
11. Call `set_variables()` with all tokens
12. Call `batch_design()` → create "Design System" frame with color swatches + type scale samples
13. Call `get_screenshot()` on the DS frame
14. Run quality checklist — **AI Slop Detection first** (see `references/quality-checklist.md`)
15. Present to user for review and iterate until approved
16. Write `docs/c4flow/designs/<slug>/MASTER.md`:
```markdown
# MASTER: <feature-name> Design System

## Design Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--primary` | `oklch(...)` | CTAs, links |
| `--bg` | `oklch(...)` | Page background |
| `--fg` | `oklch(...)` | Body text |
| `--muted` | `oklch(...)` | Secondary text |
| `--border` | `oklch(...)` | Borders |
| `--card` | `oklch(...)` | Card surfaces |
| `--destructive` | `oklch(...)` | Errors |
| `--success` | `oklch(...)` | Confirmations |
| `--warning` | `oklch(...)` | Warnings |
| `font-heading` | `'...'` | Heading font |
| `font-body` | `'...'` | Body font |
| `space-xs` | `4` | Tight spacing |
| `space-sm` | `8` | Small spacing |
| `space-md` | `16` | Medium spacing |
| `space-lg` | `32` | Large spacing |
| `space-xl` | `64` | XL spacing |

## Motion Tokens

| Token | Value | Purpose |
|-------|-------|---------|
| `--duration-fast` | `150ms` | Button press, toggle |
| `--duration-normal` | `250ms` | Menu open, tooltip |
| `--duration-slow` | `400ms` | Accordion, drawer |
| `--ease-out` | `cubic-bezier(0.16,1,0.3,1)` | Elements entering |
| `--ease-in` | `cubic-bezier(0.7,0,1,1)` | Elements leaving |

## Reusable Components

| Component | Variants | Frame ID |
|-----------|----------|----------|
| Button | Primary, Secondary, Ghost, Destructive | `<id>` |
| Input | Default, Error, Disabled | `<id>` |
| ... | ... | ... |

## File

- Pencil file: `docs/c4flow/designs/<slug>/<slug>.pen`
- Design System Frame ID: `<id>`
```

17. Save the `.pen` file: call `get_editor_state()` to get the current document path. If not saved to target path, call `open_document("save", path: "docs/c4flow/designs/<slug>/<slug>.pen")`.

### Step 1.3: Reusable Components

**Goal**: Create all shared components in the `.pen` file as reusable frames.

1. Read `skills/design/references/component-patterns.md` — 8 interaction states, focus rings, forms
2. Read `skills/design/references/spatial-design.md` — 4pt scale, rhythm
3. Determine platform type from `tech-stack.md`
4. From `screen-map.md`, extract the full component list
5. For each component:
   - Call `batch_design()` — insert frame with `reusable: true` inside the Design System frame
   - Design all 8 states (Default, Hover, Focus, Active, Disabled, Loading, Error, Success)
   - Create variants as separate reusable frames (Button Primary, Button Secondary, etc.)
   - Use design tokens for all colors, fonts, spacing
   - Max 25 operations per `batch_design` call — split if needed
6. After all components created, call `get_screenshot()` on the Design System frame
7. Run quality checklist (AI Slop Detection first)
8. Present to user for review and iterate

**Binding names must be unique across calls. Never reuse a binding name.**

### Step 1.4: Hero Screen Mockup

**Goal**: Compose the most complex screen using reusable components, validate style direction.

1. Read all `references/*.md` files — this is the most design-intensive step
2. Select hero screen (most components, most layout decisions)
3. Determine dimensions from `tech-stack.md` or use defaults from `references/spatial-design.md`
4. Call `find_empty_space_on_canvas({direction: "right", width: <w>, height: <h>})` → get position
5. Call `batch_design()` → create screen frame at that position
6. Call `batch_get({patterns: [{reusable: true}], searchDepth: 2})` → get all component ref IDs
7. Call `batch_design()` → compose screen using `{type: "ref", ref: "<id>"}` for components
   - Split into multiple calls by section (nav first, then sidebar, then main content)
8. Call `get_screenshot()` on the screen frame
9. Run full quality checklist:
   - **AI Slop Detection** (CRITICAL — first) — no gradients, no glassmorphism, no pure gray, no hero metrics
   - Visual hierarchy squint test
   - Color contrast check
   - Typography check (no Inter/Roboto/Arial)
   - Spacing check (4pt scale, rhythm)
   - Call `snapshot_layout({nodeIds: [<screenId>], problemsOnly: true})`
10. Fix any issues found, re-screenshot
11. Present to user for review and iterate until approved
12. Record hero screen frame ID
13. Update `.state.json`:
    ```bash
    jq '.heroScreen = "<hero-frame-id>" | .designSystem = "docs/c4flow/designs/<slug>/<slug>.pen" | .screenCount = <N>' \
      docs/c4flow/.state.json > docs/c4flow/.state.json.tmp \
      && mv docs/c4flow/.state.json.tmp docs/c4flow/.state.json
    ```

---

## Phase 2: Sub-Agents (Parallel)

**Goal**: Compose remaining screens concurrently — each screen gets its own sub-agent running in parallel. All agents write to the same `.pen` file safely (Pencil MCP handles concurrent writes).

1. Read `screen-map.md` — list all screens except the hero
2. If >15 screens: batch into groups of 5 — dispatch one group at a time, wait all in group, user review, then next group
3. Call `batch_get({patterns: [{reusable: true}], searchDepth: 2})` — extract ALL component ref IDs **once** before dispatching
4. Dispatch **all remaining screen sub-agents in parallel** using the prompt template below
   - Each sub-agent needs: feature name, `.pen` path, DS frame ID, hero frame ID, screen spec, all component ref IDs, design tokens
   - Model selection per screen: simple form → `haiku`, dashboard/complex → `sonnet`
5. Wait for all sub-agents to complete
   - **BLOCKED**: collect all blockers, present to user, ask for guidance
   - **DONE_WITH_CONCERNS**: collect all concerns, present to user, ask "Proceed or fix first?"
   - **DONE**: continue to Phase 3
6. After all screens done: call `get_screenshot()` for all screen frames, present batch review
7. If user requests fixes: dispatch fix sub-agent for that screen only

### Sub-Agent Prompt Template

```
# Design Screen: {screen_name}

## Context
Feature: {feature_name}
Pencil MCP file: {pen_file_path}
Design System Frame ID: {ds_frame_id}
Hero Screen Frame ID: {hero_frame_id} — match spacing rhythm, visual weight, layout patterns
Screen Dimensions: {width}×{height}

## Screen Spec (from screen-map.md)
{full screen entry from screen-map.md}

## Reusable Components Available
{list each: name: ref="<id>"}

## Design Tokens (from MASTER.md)
Primary: {value}
Background: {value}
Foreground: {value}
Font heading: {value}
Font body: {value}
Spacing scale: 4 · 8 · 12 · 16 · 24 · 32 · 48 · 64

## Impeccable Design Rules (non-negotiable)
- No pure black/gray — tinted neutrals only (chroma ≥ 0.005)
- No card nesting — use spacing for hierarchy within sections
- Squint test: primary element identifiable in 2 seconds
- Every interactive element needs clear affordance
- Tight grouping (8-12px) for related items, generous (48-96px) between sections
- 60-30-10 color weight rule (neutrals 60%, secondary 30%, accent 10%)
- No identical repeated card grids (icon + heading + text repeated)
- Match hero screen's layout rhythm and visual weight
- Motion: ease-out for entering, ease-in for leaving — no bounce/elastic
- Animate only transform + opacity

## AI Slop Checklist (run before reporting DONE)
- [ ] No gradient text or backgrounds
- [ ] No glassmorphism
- [ ] No pure gray neutrals
- [ ] No hero metric layout (big number, small label, stats, gradient)
- [ ] No Inter/Roboto/Arial fonts
- [ ] No rounded rectangles with generic drop shadows everywhere

## Report
Return: DONE | DONE_WITH_CONCERNS | BLOCKED
Include:
- Screen frame ID
- Screenshot verified: yes/no
- Issues found: <list or "none">
```

### Model Selection

| Screen Type | Model |
|---|---|
| Simple form (login, register, settings) | `haiku` |
| Dashboard / data-heavy / multi-section | `sonnet` |
| Complex flow (multi-step wizard) | `sonnet` |

---

## Phase 3: Completion

1. Call `get_screenshot()` of entire canvas (all frames)
2. Optional: Call `export_nodes()` for all screen frame IDs → PNG exports
3. Verify gate conditions:
   - `docs/c4flow/designs/<slug>/MASTER.md` exists
   - `docs/c4flow/designs/<slug>/screen-map.md` exists
   - `.pen` file exists with Design System frame + ≥1 screen frame
   - All screens in `screen-map.md` have corresponding frames
   - Hero screen passed quality check (AI Slop Detection = PASS)
   - User approved final review
4. Update `.state.json`:
   ```bash
   # Read current state first
   CURRENT=$(cat docs/c4flow/.state.json)
   COMPLETED=$(echo "$CURRENT" | jq -r '.completedStates // []')
   PHASE_NAME="DESIGN"

   # Add DESIGN to completedStates if not already there
   if echo "$COMPLETED" | grep -q "\"$PHASE_NAME\""; then
     NEW_COMPLETED="$COMPLETED"
   else
     NEW_COMPLETED=$(echo "$COMPLETED" | jq --arg p "$PHASE_NAME" '. + [$p]')
   fi

   # Update state: mark DESIGN done, screenCount, design path, move to next state
   echo "$CURRENT" | jq \
     --argjson completed "$NEW_COMPLETED" \
     --arg count "<N>" \
     --arg designPath "docs/c4flow/designs/<slug>/<slug>.pen" \
     --arg nextState "BEADS" \
     '
     .completedStates = $completed
     | .currentState = $nextState
     | .screenCount = ($count | tonumber)
     | .designPath = $designPath
     ' > docs/c4flow/.state.json.tmp \
   && mv docs/c4flow/.state.json.tmp docs/c4flow/.state.json
   ```
   > **Critical:** This is the ONLY place `.state.json` is updated during design. The orchestrator reads this file to determine the next state (BEADS).
5. Report to user: DONE — gate conditions met, design artifacts ready, state updated to BEADS

---

## Error Handling

| Situation | Action |
|---|---|
| Pencil MCP not available | Abort: "Design skill requires Pencil MCP." |
| `spec.md` or `design.md` missing | Abort: "Run SPEC phase first (`/c4flow:run`)" |
| `get_style_guide` returns no results | Proceed with Impeccable defaults from reference files |
| Sub-agent can't find component ref | Re-call `batch_get()`, provide correct ref IDs, re-dispatch |
| `snapshot_layout` reports issues | Fix via `batch_design`, re-screenshot (1 auto-retry), then DONE_WITH_CONCERNS |
| Canvas space insufficient | Call `find_empty_space_on_canvas` with larger dimensions |
| User rejects design 3+ times | Ask: "Want to try a different style direction?" |
| `batch_design` fails (rollback) | Check error message, fix operation list, retry |
| `.pen` file corrupted or empty | Delete file, restart from Step 1.2 |
| >15 screens | Batch into groups of 5, user review between groups |

---

## Pencil MCP Constraints

- `batch_design` max **25 operations** per call — split by logical section
- Every `I()`, `C()`, `R()` operation **must** have a binding name
- `document` is reserved — only use when creating top-level canvas frames
- Bindings are only valid within the same `batch_design` call
- Do NOT `U()` descendants of a freshly `C()`'d node
- No `"image"` node type — images are fills on frame/rectangle nodes
- `find_empty_space_on_canvas` before every new screen frame

---

## Reference Files

Read as needed:

- `references/teach.md` — Context gathering (auto-parse, recommend, approve)
- `references/design-principles.md` — Impeccable design direction + AI slop test
- `references/color-and-contrast.md` — OKLCH, tinted neutrals, 60-30-10, dark mode
- `references/typography.md` — Modular scale, font pairing, vertical rhythm
- `references/spatial-design.md` — 4pt scale, visual rhythm, card usage rules
- `references/component-patterns.md` — 8 states, focus rings, forms, loading states
- `references/quality-checklist.md` — AI slop detection, contrast, hierarchy, spacing
- `references/motion.md` — Easing curves, timing, prefers-reduced-motion
- `references/interaction.md` — Keyboard nav, gestures, destructive actions
- `references/responsive.md` — Mobile-first, container queries, input detection
- `references/ux-writing.md` — Button labels, errors, empty states, terminology
