# c4flow:research — Execution Prompt

## Step 1: Clarifying Questions

**Before starting any research**, assess whether the feature description is clear enough to research effectively — then decide how many questions to ask.

### Assess description completeness

Score the description across these dimensions:

| Dimension | Clear | Vague |
|-----------|-------|-------|
| **Who** | Target users or segment named | "users", "people", no specifics |
| **What problem** | Specific pain point described | Generic or missing |
| **Scope** | Standalone vs part of bigger system clear | Unknown |
| **Context** | Domain, platform, or constraints mentioned | None |

**Decision rules:**

| Score | Action |
|-------|--------|
| **3-4 dimensions clear** | Ask **0-1 questions** — only for the most critical gap. Note assumptions for the rest. |
| **2 dimensions clear** | Ask **2-3 questions** — the most important unknowns. |
| **0-1 dimensions clear** | Ask **3-5 questions** — description too vague to research well. |

> **Why this matters:** Asking 5 questions for a well-described feature adds unnecessary round-trips. Asking 0 questions for a vague one produces research that misses the mark. Match depth to need.

### Question categories (pick the most relevant)

| Category | Example Questions |
|----------|------------------|
| **Target audience** | "Ai là người dùng chính? B2B hay B2C? Quy mô team/company?" |
| **Problem context** | "Pain point cụ thể nhất mà bạn muốn giải quyết là gì?" |
| **Existing solutions** | "Hiện tại bạn (hoặc user) đang xử lý vấn đề này bằng cách nào?" |
| **Scope boundaries** | "Feature này là standalone product hay một phần của hệ thống lớn hơn?" |
| **Constraints** | "Có ràng buộc nào về tech stack, budget, timeline, hoặc platform không?" |
| **Success criteria** | "Thành công được đo bằng gì? Revenue, adoption, efficiency gain?" |
| **Competitive context** | "Bạn đã biết competitor nào chưa? Có tool nào bạn thích/ghét?" |

**Rules:**
- Questions must be **specific to the feature** — never ask generic templates verbatim.
- If asking 0 questions, state what assumptions you're making before proceeding: "Proceeding with the following assumptions: [list]. Let me know if any of these are wrong."
- If the user says "skip" or "just go" at any point, proceed with reasonable assumptions and note them in the output.
- **Do NOT proceed** to Step 2 if you asked questions and are waiting for a response.

**After receiving answers** (or if asking 0 questions), incorporate context into your research and proceed to Step 2.

---

## Step 2: Parse Input & Determine Mode

**Mode resolution:**

| Condition | Mode |
|-----------|------|
| Prompt contains `Mode: fast` | `fast` |
| No Mode field or `Mode: research` | `research` (default) |

In **fast mode**: Use only AI internal knowledge. No web search.
In **research mode**: Search the web for competitor data and technical sources. Fetch relevant URLs for detailed information. Collect all source URLs — they go in the `## Sources` section.

**Edge cases:**
- If the idea is still very broad after clarifying questions, make reasonable assumptions and note them.
- If the idea is very niche and likely has no direct competitors, proceed anyway — use adjacent/indirect competitors and note the niche nature.

---

## Step 3: Layer 1 — Market Analysis

Analyze the feature from business and market perspectives. Do NOT reference technical approaches yet — that's Layer 2.

Produce data for **10 sections**:

### 3.1 Problem Statement
- 2-3 sentences: What pain does this solve? For whom? In what context?

### 3.2 Target Users
- List 2-4 user personas
- Per persona: role, goal, key frustration

### 3.3 Core Workflows
- List 3-6 primary user workflows as numbered steps
- Format: `Workflow N: <name>` → `1. step → 2. step → 3. step`

### 3.4 Domain Entities
- Key data objects the system manages (e.g., Transaction, Budget, Category)
- Include key attributes for each entity

### 3.5 Business Rules
- Constraints and logic the system must enforce (e.g., "Budget cannot exceed income")

### 3.6 Competitive Landscape
- Identify 4-8 relevant competitors or alternatives
- For each competitor, collect 6 fields:

```
Name:
Type: [direct | indirect | adjacent]
Target segment:
Pricing model:
Platform:
Key differentiator:
```

- **Research mode**: Search the web per competitor to verify and enrich:
  - `"<competitor> pricing"`
  - `"<competitor> features"`
  - `"<competitor> reviews site:reddit.com OR site:producthunt.com"`
  - Maximum 3 searches per competitor
  - Wait 1-2 seconds between searches to avoid rate limits
  - If search fails, retry once with broader query; if still fails, mark data as `?` and note "search failed" in Sources
- **Fast mode**: Use internal knowledge only

### 3.7 Feature Comparison
- Build a feature comparison matrix across top 4-6 competitors
- List 10-15 most important features for this product category
- For each competitor, mark: `✓` (has it), `△` (partial/limited), `✗` (missing)
- Add a **"Your Product"** column — leave blank (filled during gap analysis)

```
| Feature            | Competitor A | Competitor B | Competitor C | Competitor D | Your Product |
|--------------------|-------------|-------------|-------------|-------------|-------------|
| Core feature 1     | ✓           | ✓           | ✗           | △           |             |
| Core feature 2     | ✗           | ✓           | ✓           | ✓           |             |
```

### 3.8 Gap Analysis
- Based on all above, identify opportunities across 5 categories:
  - **Feature Gaps**: Features missing or poor across most competitors
  - **Segment Gaps**: User groups underserved by current market
  - **UX/DX Gaps**: Usability or developer experience problems common in existing tools
  - **Pricing Gaps**: Underserved price points or model mismatches
  - **Integration Gaps**: Missing integrations that target users need

- Per gap, format as:
```
Gap: <short name>
Evidence: <which competitors have this problem>
Opportunity: <how you can address it>
Priority: [high | medium | low]
```

### 3.9 Differentiation Strategy
- 3-5 bullet points describing how this product will be meaningfully different
- Be specific. Avoid generic claims like "better UX" — say *what* specifically will be better and *why*

### 3.10 Initial MVP Scope
- 5-10 features for a minimal but shippable v1

```
| Feature | Priority | Rationale |
|---------|----------|-----------|
| ...     | must     | ...       |
| ...     | should   | ...       |
| ...     | later    | ...       |
```

---

## Step 4: Layer 2 — Technical Research

Using the competitive context from Step 3 (Layer 1), analyze technical feasibility and risks. Step 3 MUST complete before this step.

Produce data for **4 sections**:

### 4.1 Technical Approaches
- Evaluate 2-4 technical approaches
- Per approach: pros, cons, complexity (low/medium/high), lock-in risk

```
| Approach | Pros | Cons | Complexity | Lock-in Risk |
|----------|------|------|-----------|-------------|
| ...      | ...  | ...  | ...       | ...         |
```

- **Research mode**: Fetch and read 3-5 most relevant technical sources (docs, blog posts, comparisons)
- **Fast mode**: Use internal knowledge only

### 4.2 Contrarian View
- **Mandatory**: At least 1 strong argument against building this
- What could go wrong? Why might this fail? What are the strongest arguments for NOT building?
- Include criticisms, downside cases, and market risks

### 4.3 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| ...  | Low/Med/High | Low/Med/High | ... |

- Must not be empty or generic

### 4.4 Recommendations
- Clear recommendation: build, buy/integrate, or skip
- Label each point as one of:
  - `[fact]` — verified data
  - `[inference]` — logical conclusion from data
  - `[recommendation]` — suggested action

---

## Step 5: Quality Gate (self-check before writing)

Verify ALL checks pass before writing the file. **If any fail, fix content first — do not write a failing document.**

**8 core checks:**

Market checks:
1. ✅ Feature Comparison has ≥10 features and ≥4 competitors
2. ✅ Gap Analysis has entries in at least 3 of 5 gap categories
3. ✅ Differentiation Strategy has ≥3 specific (not generic) points
4. ✅ MVP Scope has 5-10 features with priority labels

Technical checks:
5. ✅ Every number/stat has a source or is labeled `[estimate]`
6. ✅ Data older than 2 years is flagged `[stale: YYYY]`
7. ✅ At least 1 contrarian/downside case is included
8. ✅ Risks section is not empty

**Conditional check (fast mode only):**
9. ✅ Disclaimer is present at top of file

---

## Step 6: Executive Summary

After quality gate passes, write the Executive Summary:
- 2-3 sentence verdict: should we build this, buy/integrate, or skip? Why?
- Base on: competitive landscape, gaps, technical feasibility, and risks from Steps 3-4
- This is the **FIRST section** in the output file but the **LAST to be written**

---

## Step 7: Write Output

Create the directory if it doesn't exist:
```bash
mkdir -p docs/specs/<feature>
```

Write findings to `docs/specs/<feature>/research.md` using the template from `references/research-template.md`. Fill ALL 16 sections with sourced, actionable content.

**Fast mode only** — add disclaimer at top:
> ⚠️ This analysis was generated in **fast mode** using AI internal knowledge only. Competitor data (pricing, features, market position) may be outdated. Run with `--research` for verified, current data.

**Research mode only** — populate `## Sources` with all URLs used:
```
| Source | Competitor / Topic | What was found |
|--------|-------------------|----------------|
| URL    | Competitor name    | What was learned |
```

---

## Step 8: Report Status

At the end of your work, report one of:
- **DONE**: Research complete, all quality gate checks passed, document written
- **DONE_WITH_CONCERNS**: Complete, but note concerns (e.g., niche topic with <4 direct competitors, conflicting sources, mostly stale data)
- **BLOCKED**: Cannot proceed — explain why (e.g., idea too vague after clarifying questions, no web access in research mode)
- **NEEDS_CONTEXT**: Need more information from the user — explain what you need

---

## Guardrails

- **Always start with Step 1 (Clarifying Questions)** — do not skip to research without asking first. If user says "skip", proceed with assumptions noted.
- Complete ALL layers before writing the artifact — never write partial analysis
- In fast mode, **never** use web search — use internal knowledge only
- In research mode, search each major competitor individually — do not batch
- Do not fabricate competitor features — if unknown, mark as `?` and note uncertainty
- Do not skip Gap Analysis — it is the most valuable layer for proposal quality
- The artifact must be complete and standalone — readable without this conversation
- In fast mode, always include the outdated-data disclaimer at the top
- In research mode, always populate the Sources section with URLs used
