---
name: c4flow:spec
description: Generate structured spec artifacts (proposal, tech-stack, spec, design) through interactive collaboration, using research.md as structured input.
---

# /c4flow:spec — Spec Generation

**Phase**: 1: Research & Spec
**Agent type**: Main agent (interactive with user)
**Status**: Implemented

## Overview

Generate 4 planning artifacts from research findings through interactive collaboration with the user. Each artifact is presented for approval before proceeding to the next.

**Duration estimate**: ~15-30 minutes (depends on iteration rounds with user)

## Input
- `docs/specs/<feature>/research.md` (from research phase — 16 sections)

## Output
- `docs/specs/<feature>/proposal.md`
- `docs/specs/<feature>/tech-stack.md`
- `docs/specs/<feature>/spec.md`
- `docs/specs/<feature>/design.md`

## Artifact Dependency Graph

```
proposal.md (root — generate first)
    |
    +--- tech-stack.md (requires: proposal)
    |
    +--- spec.md (requires: proposal)
    |
    +--- design.md (requires: proposal, tech-stack, spec)
```

---

## Research → Spec Mapping

Before generating any artifact, **read the full `research.md`** and use this mapping to pull structured data:

| Research Section | Feeds Into | How to Use |
|-----------------|------------|-----------|
| Executive Summary | `proposal.md` → Why | Extract motivation and build/buy/skip verdict |
| Problem Statement | `proposal.md` → Why | Use as problem context |
| Target Users + Core Workflows | `proposal.md` → What Changes; `spec.md` → User stories | Each workflow becomes 1+ scenario; each persona validates requirements |
| Domain Entities + Business Rules | `spec.md` → Requirements; `design.md` → Data Model | Entities → data model; rules → MUST requirements |
| Competitive Landscape + Feature Comparison | `proposal.md` → Impact | Reference competitors to justify feature decisions |
| Gap Analysis + Differentiation Strategy | `proposal.md` → Capabilities (New) | Gaps → new capabilities; differentiation → scope priorities |
| Initial MVP Scope | `proposal.md` → Scope (In/Out) | Must features → In Scope; later features → Out of Scope |
| Technical Approaches | `tech-stack.md` → Technology Choices | Each approach → tech-stack option with pros/cons |
| Contrarian View + Risks | `design.md` → Risks/Trade-offs | Import directly; ensure mitigations address contrarian concerns |
| Recommendations | `proposal.md` → Success Criteria | Recommendations → measurable success criteria |

> **CRITICAL**: Do NOT just "read research.md for context." Extract specific data from specific sections. The mapping above tells you exactly what to pull and where to put it.

---

## Instructions

### Step 1: Read Research Context

Read `docs/specs/<feature>/research.md`. Parse all 16 sections. Note especially:
- **Executive Summary** — the build/buy/skip verdict
- **Initial MVP Scope** — shapes proposal scope
- **Technical Approaches** — shapes tech-stack choices
- **Risks** — carries forward to design

If `research.md` is missing sections or quality is low, note concerns but proceed with available data. Do NOT re-do research.

---

### Step 2: Direction Exploration (Q&A + Suggestions)

**Before generating any artifact**, pause and collaborate with the user to define the spec direction. Research gives us data — this step turns data into a clear vision.

#### 2.1 Clarifying Questions

Ask the user **3-5 targeted questions** based on what you found in `research.md`. Focus on decisions that will fundamentally shape the spec:

| Category | Example Questions |
|----------|------------------|
| **Scope priority** | "Research tìm thấy 8 features cho MVP. Bạn muốn focus vào core workflow nào trước?" |
| **User focus** | "Research xác định 3 personas. Bạn muốn optimize cho persona nào là chính?" |
| **Technical direction** | "Research đề xuất 3 approach. Bạn có preference về [monolith vs microservice, self-hosted vs SaaS]?" |
| **Differentiation** | "Gap analysis cho thấy [X] là cơ hội lớn nhất. Bạn đồng ý đây là điểm khác biệt chính?" |
| **Constraints** | "Có constraint nào chưa được đề cập trong research? (timeline, budget, team size, existing infra)" |
| **Integration** | "Feature này cần integrate với hệ thống nào hiện tại?" |
| **Risk appetite** | "Contrarian view nêu [risk X]. Bạn đánh giá mức độ nghiêm trọng thế nào?" |

**Rules:**
- Questions must be **specific to the research findings**, not generic
- Reference specific sections/data from `research.md` when asking
- **Wait for user response** before proceeding to 2.2

#### 2.2 Propose Spec Directions

Based on the user's answers, propose **2-3 possible spec directions**. Each direction represents a different strategy for the same feature:

```
## Direction A: [Name] — [1-line summary]
- **Focus**: [Primary capability/user segment]
- **MVP Scope**: [3-5 key features]
- **Tech approach**: [From research]
- **Timeline estimate**: [Relative: small/medium/large]
- **Trade-off**: [What you gain vs what you sacrifice]

## Direction B: [Name] — [1-line summary]
...

## Direction C (optional): [Name] — [1-line summary]
...
```

**Direction types to consider** (pick the most relevant contrasts):

| Contrast | Direction A | Direction B |
|----------|------------|------------|
| Scope | MVP tối giản (3-4 features) | Feature-rich v1 (8-10 features) |
| Audience | B2C consumer-first | B2B enterprise-first |
| Architecture | Monolith (ship fast) | Modular (scale later) |
| Build vs Integrate | Build from scratch | Integrate existing tools |
| Market entry | Compete head-on | Target underserved niche |

**Rules:**
- Each direction must be **genuinely viable** — not a strawman
- Highlight the **trade-offs** clearly so the user can make an informed decision
- Recommend one direction with reasoning, but let the user decide
- The user may choose one direction, **mix elements** from multiple directions, or propose a new one

#### 2.3 Lock Direction

After the user chooses (or mixes), summarize the agreed direction in 3-5 bullet points:

```
## Agreed Direction
- **Focus**: [chosen focus]
- **Primary persona**: [chosen persona]
- **MVP features**: [list]
- **Tech approach**: [chosen approach]
- **Key constraint**: [timeline/budget/etc.]
```

**This becomes the guiding frame for all 4 artifacts.** Reference this agreed direction in every subsequent step.

---

### Step 3: Generate proposal.md

Using the template from `references/spec-templates/proposal-template.md`:

1. **Draft the proposal** using the Research → Spec mapping above, **filtered through the agreed direction**:
   - **Why**: Pull from Executive Summary + Problem Statement. Include the build/buy/skip verdict and explain why building is the right choice
   - **What Changes**: Describe new capabilities based on Gap Analysis findings. Reference what competitors lack
   - **Capabilities (New)**: Map from agreed direction's MVP features. Each capability gets a name and description
   - **Capabilities (Modified)**: Only if modifying existing features — skip if greenfield
   - **Scope (In)**: Features from agreed direction's MVP list
   - **Scope (Out/Non-Goals)**: Everything NOT in agreed direction + anything the Contrarian View flagged as risky scope creep
   - **Success Criteria**: Derive from Recommendations. Make each criterion measurable (e.g., "User can create a budget in <30 seconds" not "Good UX")
   - **Impact**: Reference Competitive Landscape for affected ecosystem. Note which competitors this positions against

2. **Present the draft section by section** to the user (e.g., Why → What Changes → Capabilities → Scope → Success Criteria → Impact). Ask for feedback after each section before moving on.
3. **Iterate** on each section based on feedback until the user approves
4. **Write** the approved version to `docs/specs/<feature>/proposal.md`

**Quality check before presenting:**
- [ ] Every In Scope item traces back to the agreed direction or research MVP scope
- [ ] At least 2 Out of Scope items (prevents scope creep)
- [ ] Success Criteria are measurable (numbers, time, or verifiable outcomes)
- [ ] Impact section references at least 1 competitor by name

---

### Step 4: Generate tech-stack.md

Using the template from `references/tech-stack-template.md`:

1. **Map research Technical Approaches** to tech-stack categories:
   - For each category (Frontend, Backend, Infra, CI/CD, Monitoring):
     - If research evaluated relevant approaches → recommend the top-scoring one with reasoning
     - If research didn't cover this category → suggest based on project context + your knowledge
   - Include lock-in risk assessment from research
2. **Present suggestions** to the user with reasoning from research
3. **Let the user choose** or modify each category
4. **Skip irrelevant categories** (e.g., skip Frontend for a CLI-only tool)
5. **Write** to `docs/specs/<feature>/tech-stack.md`

**Quality check before presenting:**
- [ ] Every tech choice with an alternative from research includes pros/cons comparison
- [ ] No category left as placeholder — explicitly mark skipped categories as "N/A — reason"
- [ ] Lock-in risk noted for any proprietary/vendor-specific choice

---

### Step 5: Generate spec.md

Using the template from `references/spec-templates/spec-template.md`:

1. **Extract requirements** from research + proposal:
   - Each **Core Workflow** from research → at least 1 scenario
   - Each **Business Rule** from research → at least 1 MUST requirement
   - Each **Domain Entity** → validation rules where applicable
   - Each **Capability** from proposal → 1+ requirements with scenarios
2. **Write each requirement** with:
   - A clear name and description
   - **Priority**: MUST / SHOULD / MAY (align with MVP "must"/"should"/"later")
   - One or more scenarios in GIVEN/WHEN/THEN format

   **Example scenario:**
   ```
   ### Requirement: Budget Creation
   Users can create budgets with categories and spending limits.

   **Priority**: MUST

   #### Scenario: Create a new monthly budget
   - **GIVEN** a logged-in user on the budget page
   - **WHEN** the user enters category "Food", limit "3,000,000 VND", period "monthly", and clicks Save
   - **THEN** the budget is created and appears in the budget list with remaining amount = limit
   ```

3. **Use delta operations**:
   - `ADDED` — new behavior (most items for greenfield)
   - `MODIFIED` — changed behavior (for existing features)
   - `REMOVED` — deleted behavior
4. **Present requirements one at a time** (or in small groups of 2-3 related ones):
   - Show each requirement with its scenarios
   - Ask the user: "Does this look right? Any changes?"
   - Iterate on that requirement until approved before moving to the next
   - After all requirements are presented and approved, show a final summary list of all requirement names + priorities for a quick overview
5. **Write** to `docs/specs/<feature>/spec.md`

**Quality check before presenting:**
- [ ] Every proposal Capability has ≥1 corresponding requirement
- [ ] Every MUST requirement has ≥1 GIVEN/WHEN/THEN scenario
- [ ] Business Rules from research are all represented as MUST requirements
- [ ] At least 1 edge case / error scenario per major workflow

---

### Step 6: Generate design.md

Using the template from `references/design-template.md`:

1. **Build the design** from all previous artifacts:
   - **Context**: Summarize from proposal Why + research Problem Statement
   - **Architecture Overview**: Based on tech-stack choices + research Technical Approaches analysis
   - **Components**: One per major Domain Entity group or major Capability. Each component:
     - Purpose: what it does
     - Interface: inputs/outputs
     - Dependencies: which other components it uses
   - **Data Model**: Start from research Domain Entities + attributes. Add relationships, types, constraints from Business Rules
   - **API Design**: Derive from spec requirements — each external-facing requirement → API endpoint
   - **Error Handling**: Derive from spec error scenarios + research Risks
   - **Goals/Non-Goals**: Mirror from proposal Scope In/Out
   - **Decisions**: Document each tech-stack choice as a decision with rationale + alternatives considered (from research Technical Approaches)
   - **Risks/Trade-offs**: Import from research Risks + Contrarian View. Add any design-specific risks
   - **Testing Strategy**: One test type per requirement priority level (MUST → unit+integration, SHOULD → integration, MAY → manual)

2. **Present the design section by section** (e.g., Architecture → Components → Data Model → API → Error Handling → Risks → Testing). Ask for feedback after each section.
3. **Iterate** on each section until approved
4. **Write** to `docs/specs/<feature>/design.md`

**Quality check before presenting:**
- [ ] Every Component has clear boundaries — can explain what it does without reading internals
- [ ] Data Model includes all Domain Entities from research
- [ ] Risks section includes all items from research Risks + Contrarian View
- [ ] At least 1 design Decision with alternatives considered (not just "we chose X")

---

### Step 7: Completion

All four artifacts are written. Report back to the orchestrator that SPEC is complete.

Before reporting, run the **final quality gate**:

**Cross-artifact consistency checks:**
1. ✅ Every proposal Capability has requirements in `spec.md`
2. ✅ Every tech-stack choice is referenced in `design.md` decisions
3. ✅ Every research Risk appears in `design.md` risks
4. ✅ Data Model entities in `design.md` match Domain Entities from `research.md`
5. ✅ Proposal Scope (In) items all have corresponding spec requirements
6. ✅ No orphaned requirements in `spec.md` (every req traces to a proposal capability)

If any check fails, fix the artifact before reporting completion.

---

## Error Handling

| Situation | What to Do |
|-----------|-----------|
| **User rejects all directions (Step 2.2)** | Ask which specific aspect doesn't work: scope too large/small? Wrong audience? Wrong architecture? Then re-propose 2 directions that specifically address the complaint. If rejected again, ask the user to describe their preferred direction in their own words — use that as the agreed direction instead of proposing further. |
| **User rejects direction partially** | Acknowledge what they want to keep, what to drop. Restate as a new blended direction for confirmation before proceeding. "So your direction is: [X from A] + [Y from B] — is that right?" |
| User rejects artifact 3+ times | Ask: "Would you like to adjust the proposal scope? The current requirements may be misaligned with your vision." Offer to go back to proposal |
| `research.md` missing or incomplete | Note which sections are missing. Proceed with available data. Flag gaps in each artifact: "[Note: research.md lacked Competitive Landscape — this section is based on general knowledge]" |
| Artifact conflict (e.g., tech-stack doesn't support spec requirement) | Surface the conflict to user immediately: "The chosen tech [X] doesn't support requirement [Y]. Options: 1) Change tech stack, 2) Modify requirement, 3) Accept as tech debt" |
| User wants to skip an artifact | Explain dependency: "Skipping [X] means [Y] cannot reference it. Generate a minimal version instead?" Generate minimal version if user agrees |
| User adds scope during spec generation | Check against proposal Scope: "This wasn't in the proposal scope. Options: 1) Add to proposal and continue, 2) Note as future work, 3) Replace an existing scope item" |

---

## Guardrails

- **Always complete Step 2 (Direction Exploration)** before generating any artifact — don't skip the Q&A
- Generate artifacts **in dependency order** — never skip ahead
- **Reference the agreed direction** from Step 2 in every artifact
- Present each artifact for **user approval** before proceeding
- **Every claim should trace** back to research.md or user input — don't invent requirements
- Keep artifacts **DRY** — don't duplicate content across artifacts; reference instead
- Flag any **deviation from research** recommendations — explain why you disagree
- Spec requirements should be **testable** — if you can't write a scenario, it's too vague
- Design components should be **independently understandable** — each component's purpose is clear from its description alone
