---
name: c4flow:research
description: Perform merged market analysis and technical research on a feature idea. Combines market-research (business domain, competitive landscape, feature comparison, gap analysis) with C4Flow technical research (approaches, contrarian view, risks).
---

# /c4flow:research — Merged Market & Technical Research

**Phase**: 1: Research & Spec
**Agent type**: Sub-agent (dispatched by orchestrator)
**Status**: Implemented

## Overview

Analyze a feature idea across both market and technical dimensions. Produces a single structured artifact (`research.md`) with 16 sections that feeds directly into the spec phase.

**Sources merged:**
- [market-research](https://github.com/CongChu99/market-research) — business domain, competitive landscape, feature comparison, gap analysis
- C4Flow research — technical approaches, contrarian view, risks, recommendations

## Input
- Feature name (kebab-cased)
- Feature description from user
- Mode: `research` (default) | `fast`

## Output
- `docs/specs/<feature>/research.md` (16 sections)

## Execution Modes

| Mode | Web Search | Duration | Use When |
|------|-----------|----------|----------|
| `research` (default) | Yes (web search + URL fetching) | ~3-5 minutes | Pre-proposal, serious builds, funding prep |
| `fast` | No | ~30 seconds | Quick exploration, early ideation |

## Analysis Layers

| Layer | Sections | Purpose |
|-------|----------|---------|
| **Layer 1: Market** | Problem Statement → Initial MVP Scope (10 sections) | "Nên build không, và build gì?" |
| **Layer 2: Technical** | Technical Approaches → Recommendations (4 sections) | "Build như thế nào?" |
| **Quality Gate** | 8 core + 1 conditional check | Verify output completeness |
| **Executive Summary** | 2-3 sentence verdict | Build / buy / skip decision |

## Research Standards

Every research output MUST follow these 5 standards:

1. **Source every claim** — numbers, stats, and key claims must link to a source or be explicitly labeled `[estimate]`
2. **Favor recent data** — prefer sources from the last 12 months; flag anything older than 2 years as `[stale: YYYY]`
3. **Include contrarian evidence** — actively search for downside cases, criticisms, and reasons the feature might fail
4. **Translate to a decision** — findings must lead to a clear recommendation, not just a dump of information
5. **Distinguish fact / inference / recommendation** — label each clearly so the reader knows what is proven vs. interpreted vs. suggested

## Execution

Follow `prompt.md` step by step.

## Output Sections (16 total)

```
Executive Summary → Problem Statement → Target Users → Core Workflows →
Domain Entities → Business Rules → Competitive Landscape → Feature Comparison →
Gap Analysis → Differentiation Strategy → Initial MVP Scope →
Technical Approaches → Contrarian View → Risks → Recommendations → Sources
```

See `references/research-template.md` for full artifact structure.

## How Spec Phase Uses This Output

| Research Section | Feeds Into |
|-----------------|------------|
| Executive Summary | `proposal.md` → Why (motivation) |
| Target Users + Core Workflows | `proposal.md` → What Changes; `spec.md` → User stories |
| Domain Entities + Business Rules | `spec.md` → Requirements; `design.md` → Data Model |
| Competitive Landscape + Feature Comparison | `proposal.md` → Impact + Differentiation |
| Gap Analysis + Differentiation Strategy | `proposal.md` → Capabilities (New) |
| Initial MVP Scope | `proposal.md` → Scope (In/Out) |
| Technical Approaches | `tech-stack.md` → Technology Choices |
| Contrarian View + Risks | `design.md` → Risks/Trade-offs |
| Recommendations | `proposal.md` → Success Criteria |
