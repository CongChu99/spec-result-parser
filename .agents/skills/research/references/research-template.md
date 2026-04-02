# Research: <feature-name>

> Mode: fast | research
> Date: YYYY-MM-DD

<!-- In fast mode, add this disclaimer: -->
<!-- ⚠️ This analysis was generated in **fast mode** using AI internal knowledge only. Competitor data (pricing, features, market position) may be outdated. Run with `--research` for verified, current data. -->

---

## Executive Summary
2-3 sentence verdict: should we build this, buy/integrate, or skip? Why?
This is the LAST section to be written but the FIRST in the document.

## Problem Statement
What problem does this feature solve? Who has this problem? How do they cope today? (2-3 sentences)

## Target Users
| Persona | Role | Goal | Key Frustration |
|---------|------|------|-----------------|
| Persona 1 | ... | ... | ... |
| Persona 2 | ... | ... | ... |

List 2-4 personas.

## Core Workflows
3-6 primary user workflows as numbered steps.

### Workflow 1: <name>
1. Step →
2. Step →
3. Step

### Workflow 2: <name>
1. Step →
2. Step →
3. Step

## Domain Entities
Key data objects the system manages.

| Entity | Key Attributes | Description |
|--------|---------------|-------------|
| e.g. Transaction | amount, date, category, note | ... |
| e.g. Budget | category, limit, period | ... |

## Business Rules
Constraints and logic the system must enforce.

- Rule 1 (e.g., "Budget cannot exceed income")
- Rule 2
- Rule 3

## Competitive Landscape
| Product | Type | Target Segment | Pricing | Platform | Key Differentiator |
|---------|------|---------------|---------|----------|--------------------|
| Competitor A | direct | ... | ... | ... | ... |
| Competitor B | indirect | ... | ... | ... | ... |
| Competitor C | adjacent | ... | ... | ... | ... |
| Competitor D | direct | ... | ... | ... | ... |

List 4-8 competitors. Type: direct | indirect | adjacent.

## Feature Comparison
| Feature | Competitor A | Competitor B | Competitor C | Competitor D | Your Product |
|---------|-------------|-------------|-------------|-------------|-------------|
| Core feature 1 | ✓ | ✓ | ✗ | △ | |
| Core feature 2 | ✗ | ✓ | ✓ | ✓ | |
| Advanced feature 1 | △ | ✗ | ✓ | ✗ | |

✓ = has it, △ = partial/limited, ✗ = missing. List ≥10 features, ≥4 competitors.

## Gap Analysis

### Feature Gaps
Features missing or poor across most competitors.

```
Gap: <short name>
Evidence: <which competitors have this problem>
Opportunity: <how you can address it>
Priority: high | medium | low
```

### Segment Gaps
User groups underserved by current market.

### UX / DX Gaps
Usability or developer experience problems common in existing tools.

### Pricing Gaps
Underserved price points or model mismatches.

### Integration Gaps
Missing integrations that target users need.

Must have entries in at least 3 of 5 gap categories.

## Differentiation Strategy
3-5 specific, concrete differentiators. Avoid generic claims like "better UX" — say *what* specifically will be better and *why*.

1. **Differentiator 1**: specific explanation
2. **Differentiator 2**: specific explanation
3. **Differentiator 3**: specific explanation

## Initial MVP Scope
5-10 features for a minimal but shippable v1.

| Feature | Priority | Rationale |
|---------|----------|-----------|
| e.g. Manual transaction entry | must | Core pain point — no MVP without this |
| e.g. Budget categories | must | Primary differentiation vs competitors |
| e.g. Monthly summary dashboard | must | Required to show value immediately |
| e.g. Recurring transaction templates | should | Reduces friction for common patterns |
| e.g. Export to CSV | should | Common request, low effort |
| e.g. Multi-currency support | later | Needed v2, adds complexity to v1 |

## Technical Approaches
| Approach | Pros | Cons | Complexity | Lock-in Risk |
|----------|------|------|-----------|-------------|
| Approach A | ... | ... | Low/Med/High | Low/Med/High |
| Approach B | ... | ... | ... | ... |

## Contrarian View
What are the strongest arguments against building this? Include at least one.
- Argument 1
- Argument 2

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Risk 1 | Low/Med/High | Low/Med/High | ... |
| Risk 2 | ... | ... | ... |

## Recommendations
*Label each point:*
- `[fact]` Summary of verified finding
- `[inference]` Conclusion drawn from data
- `[recommendation]` Suggested direction, directly supported by findings above

## Sources
<!-- Only populated in research mode. In fast mode, write: "Fast mode — no external sources used." -->

| Source | Competitor / Topic | What was found |
|--------|-------------------|----------------|
| URL | Competitor name | What was learned |

> **Data freshness**: Note any data older than 2 years as `[stale: YYYY]`. Research date: YYYY-MM-DD.
