# Research: spec-result-parser

> Mode: research
> Date: 2026-04-02

---

## Executive Summary

**Verdict: BUILD** — with a focused, pragmatic scope.

The current market has a clear gap: engineers working with multiple simulators (Spectre, HSPICE, ngspice) and verification tools (Calibre) must stitch together ad-hoc scripts, OCEAN macros, and manual Excel copy-paste to check spec compliance and generate reports. No existing open-source or free tool covers the full pipeline (multi-format parsing → spec check → corner aggregation → report export) as a unified, zero-GUI CLI tool. Commercial solutions (Cadence ADE Maestro, BeSpice) are either GUI-bound, extremely expensive, or locked to a single simulator vendor. A well-designed CLI tool here directly addresses a painful, daily productivity bottleneck for analog IC engineers in mid-size fab-less teams and universities — estimated at 1–3 hours per engineer per verification cycle spent on manual result collection.

---

## Problem Statement

Analog IC design engineers produce results from multiple simulator and verification tool outputs per day (Spectre AC/DC/Transient PSF, HSPICE MT0/AC0/TR0, ngspice RAW, Calibre LVS/DRC logs). These files use different binary/ASCII formats that no single open-source tool can parse uniformly. After completing corner simulations (PVT sweep across TT/FF/SS/SF/FS at -40/27/125C — typically 25-50 simulation runs per design), engineers manually copy data into Excel to check against spec targets and produce sign-off reports. This wastes 1-3 hours [estimate] per verification milestone, and is error-prone due to manual transcription.

---

## Target Users

| Persona | Role | Goal | Key Frustration |
|---------|------|------|-----------------|
| **Analog IC Engineer** | Full-stack analog designer at fab-less company | Quickly verify design meets spec across all PVT corners before tape-out | Spending hours copying sim results to Excel manually; no unified tool |
| **Verification / Characterization Engineer** | Focuses on post-layout simulation and sign-off | Aggregate corner data, produce compliance report for lead or client | Must maintain a zoo of ad-hoc shell/OCEAN/Python scripts per project |
| **Research / PhD Student** | Academic user working with Xschem + ngspice or open-PDK flows | Run and check multi-corner simulations for paper/thesis | Existing tools require Cadence license they don't have |
| **Team Lead / Design Manager** | Reviews sign-off results before tape-out | Wants consolidated pass/fail dashboard for all specs across all corners | No way to get a clean summary without engineer manually preparing Excel |

---

## Core Workflows

### Workflow 1: Single-file Spec Check
1. Engineer finishes a simulation run
2. Runs `spec-parser check result.psf --spec opamp.spec.yaml`
3. Tool parses PSF, extracts measurements (gain, BW, PM, ...)
4. Compares against YAML-defined spec targets
5. Prints color-coded PASS/FAIL table to terminal

### Workflow 2: Multi-Corner Aggregation
1. Engineer completes corner sweep (25-50 sim files across PVT)
2. Runs `spec-parser aggregate ./results/ --spec opamp.spec.yaml --corners corners.yaml`
3. Tool parses all result files in folder (auto-detects format)
4. Builds corner x spec matrix
5. Reports worst-case margin and any FAIL corners

### Workflow 3: Report Generation
1. After corner check, engineer runs `spec-parser report --format excel`
2. Tool generates formatted Excel/PDF with corner table, pass/fail highlights, margin columns
3. Engineer attaches report to tape-out sign-off package

### Workflow 4: LVS/DRC Log Summary
1. Engineer runs Calibre LVS/DRC
2. Runs `spec-parser lvs calibre_lvs.log`
3. Tool extracts rule violation count, clean/notclean status
4. Outputs structured summary to stdout or file

### Workflow 5: CI/CD Integration
1. Post-simulation script calls `spec-parser check` in batch mode
2. Returns exit code 0 (all PASS) or 1 (any FAIL)
3. CI pipeline (make/Jenkins/GitHub Actions) reports pass/fail gate

---

## Domain Entities

| Entity | Key Attributes | Description |
|--------|---------------|-------------|
| **SimResult** | simulator, format, filepath, corner_id, timestamp | A single simulation output file (PSF, RAW, TR0, etc.) |
| **Measurement** | name, value, unit, corner_id | A scalar performance metric extracted from SimResult |
| **SpecTarget** | name, min, max, unit, description | A spec limit defined in the YAML spec file |
| **SpecCheck** | measurement, target, status (PASS/FAIL/MARGIN), margin | Result of comparing a Measurement to a SpecTarget |
| **Corner** | name, process, voltage, temperature | A PVT corner (e.g., SS_1V8_m40C) |
| **CornerMatrix** | corners x specs -> SpecChecks | Aggregated result table across all corners |
| **Report** | format (Excel/PDF/CSV/HTML), generated_at, corner_matrix | Final output artifact |
| **LVSResult** | tool, clean, rule_count, error_list | DRC/LVS log parse result |
| **SpecFile** | path, version, specs: [SpecTarget] | YAML/TOML file defining spec targets by measurement name |

---

## Business Rules

- A spec check is PASS if min <= value <= max; it is FAIL if either bound is violated
- If min or max is omitted in SpecTarget, that bound is unchecked (one-sided spec)
- Corner aggregation shows worst-case margin (min margin across all corners)
- Overall design sign-off is PASS only if ALL specs PASS across ALL corners
- Format auto-detection is based on file extension + header magic bytes (e.g., PSF header, binary markers)
- LVS is CLEAN only if violation count = 0; any short, open, or missing device = FAIL
- Reports preserve color-coding: FAIL = red, MARGIN less than 10% = orange, PASS = green
- If a file cannot be parsed, tool emits a warning and continues (non-fatal parse errors)
- Exit code 0 = all checks pass; exit code 1 = any FAIL; exit code 2 = parse/config error

---

## Competitive Landscape

| Product | Type | Target Segment | Pricing | Platform | Key Differentiator |
|---------|------|---------------|---------|----------|-------------------|
| **Cadence ADE Maestro** | direct | Large EDA teams with Cadence license | $$$$ (enterprise, tens of k$/seat) | GUI, Linux | Best-in-class PVT corner management, Spectre-native |
| **psf-utils** | direct | Open-source Spectre users | Free (open source) | CLI, Linux/Mac | Simple PSF ASCII reader, limited formats |
| **spicelib** | direct | Python devs, LTspice/ngspice users | Free (open source) | Python CLI, cross-platform | Multi-sim batch runner + RAW parser, no spec check |
| **hspiceParser** | direct | HSPICE-only engineers | Free (open source) | CLI (pip), Linux/Mac | HSPICE binary/ASCII to CSV/MATLAB, single simulator |
| **BeSpice Wave** | indirect | Advanced waveform analysis users | Custom enterprise pricing | GUI, Windows/Linux | Widest format support, waveform viewer, not CLI-first |
| **PySpice** | adjacent | Python/academic simulation users | Free (GPLv3) | Python lib, cross-platform | Full ngspice Python OOP interface; no spec check |
| **OCEAN Scripts (Cadence)** | indirect | Cadence Virtuoso users | Included with Virtuoso | Scripting, Linux | Powerful SKILL scripting, steep learning curve, Cadence-only |
| **Custom in-house scripts** | adjacent | Any analog team | Engineering time cost | Shell/Python, ad-hoc | How ~80% of teams currently solve this problem [estimate] |

---

## Feature Comparison

| Feature | ADE Maestro | psf-utils | spicelib | hspiceParser | BeSpice | PySpice | Your Product |
|---------|-------------|-----------|----------|--------------|---------|---------|-------------|
| Parse Spectre PSF/PSFXL | yes | yes | no | no | yes | no | |
| Parse HSPICE TR0/AC0/MT0 | yes | no | partial | yes | yes | no | |
| Parse ngspice RAW | partial | no | yes | no | yes | yes | |
| Parse Calibre LVS/DRC log | no | no | no | no | no | no | |
| Spec YAML/TOML config | no | no | no | no | no | no | |
| Automated PASS/FAIL check | yes | no | no | no | no | no | |
| Multi-corner aggregation | yes | no | partial | no | no | no | |
| Worst-case margin report | yes | no | no | no | no | no | |
| Excel/CSV report export | partial | no | partial | yes | no | no | |
| PDF report export | no | no | no | no | no | no | |
| CLI-first (no GUI required) | no | yes | yes | yes | no | yes | |
| No Cadence license required | no | yes | yes | yes | yes | yes | |
| CI/CD friendly (exit codes) | no | no | no | no | no | no | |
| Auto format detection | no | no | no | no | partial | no | |
| Open source / free | no | yes | yes | yes | no | yes | |

---

## Gap Analysis

### Feature Gaps

Gap: Unified multi-format parser
Evidence: No single open-source tool handles PSF + HSPICE + ngspice RAW + Calibre in one CLI
Opportunity: Build a plugin-based parser architecture (one parser per format)
Priority: high

Gap: Automated spec checking
Evidence: psf-utils, spicelib, hspiceParser all parse but none define spec targets or check PASS/FAIL
Opportunity: YAML/TOML spec config + measurement to spec comparison engine
Priority: high

Gap: Multi-corner aggregation
Evidence: Only ADE Maestro (expensive, GUI-bound, Cadence-only) provides this; all open-source tools lack it
Opportunity: Corner matrix builder that ingests a folder of results and auto-assigns corners
Priority: high

Gap: LVS/DRC log parsing
Evidence: No open-source tool parses Calibre or Assura LVS/DRC logs in structured format
Opportunity: Regex-based parser for Calibre LVS clean/notclean, DRC rule violation count
Priority: medium

Gap: PDF/Excel report generation
Evidence: Only hspiceParser outputs CSV; no tool produces formatted, deliverable-quality reports
Opportunity: openpyxl/reportlab-based report generator with color-coded pass/fail table
Priority: high

### Segment Gaps

Gap: Small-team and academic users without Cadence license
Evidence: ADE Maestro is unaffordable for startups and researchers; psf-utils requires Cadence psf binary
Opportunity: Pure-Python open-source tool with zero EDA vendor dependency
Priority: high

Gap: Open PDK users (Sky130, GF180, IHP-SG13G)
Evidence: Growing open-source ASIC community uses ngspice + Xschem; no post-processing tool exists
Opportunity: First-class ngspice RAW + Spectre PSF support targets both communities
Priority: medium

### UX/DX Gaps

Gap: CI/CD integration
Evidence: No EDA tool supports exit-code-based pass/fail for automation pipelines
Opportunity: Return exit 0/1 based on spec check; machine-readable --json output mode
Priority: high

Gap: Declarative, version-controllable spec definition
Evidence: All existing tools require custom scripting per project; no portable spec YAML standard exists
Opportunity: YAML/TOML spec config committable to Git alongside netlist/schematic
Priority: high

### Pricing Gaps

Gap: Free, MIT-licensed tool (no GPL concerns for commercial use)
Evidence: Free tools (PySpice) are GPLv3; commercial tools are expensive
Opportunity: MIT license makes adoption frictionless for commercial analog teams
Priority: medium

### Integration Gaps

Gap: Makefile/CI integration
Evidence: No EDA result parsing tool outputs clean exit codes or JSON for automation
Opportunity: --json flag for machine-readable output; standard exit codes documented
Priority: high

Gap: Git-committable spec files
Evidence: Spec targets currently live in docs/Excel/heads of engineers, not source control
Opportunity: YAML spec file = source of truth, version-controlled alongside netlist
Priority: medium

---

## Differentiation Strategy

1. **Multi-simulator in a single CLI** — while psf-utils handles only PSF and hspiceParser handles only HSPICE, spec-result-parser auto-detects and parses PSF/PSFXL, HSPICE MT0/AC0/TR0, ngspice RAW, and Calibre LVS/DRC logs with one command. Engineers stop maintaining 3-5 separate scripts.

2. **Spec checking is first-class, not an afterthought** — the tool is built around a YAML specification file format that makes spec limits explicit, version-controllable, and reviewable in pull requests. This shifts spec review from verbal/Word-doc to code-review level.

3. **Corner aggregation as a primary feature** — the `aggregate` subcommand treats a folder of simulation runs as a structured dataset, auto-maps them to PVT corners, and produces a worst-case corner matrix. This replaces 1-2 hours of manual Excel work per sign-off.

4. **CI/CD native** — exit codes, --json output mode, and pip-installable packaging make this the first EDA post-processing tool that fits naturally into a Makefile or GitHub Actions workflow. Critical for open-source ASIC teams using SkyWater/GF180 PDKs.

5. **No EDA vendor dependency** — runs fully in Python 3.9+, installable via pip, works offline, needs no Cadence/Synopsys license. Usable in academic labs, startups, and the open-PDK community.

---

## Initial MVP Scope

| Feature | Priority | Rationale |
|---------|----------|-----------|
| Spectre PSF ASCII parser | must | Most common production simulator; PSF-ASCII syntax well-documented |
| HSPICE MT0 scalar results parser | must | MT0 contains .MEASURE outputs; most spec-relevant format |
| ngspice RAW (ASCII) parser | must | Growing open-source community; syntax is well-documented |
| YAML spec config format | must | Foundation of all spec checking; no spec file = no value proposition |
| check subcommand (single file + spec) | must | Core use case: parse file, compare to spec, print PASS/FAIL |
| Color-coded terminal output (rich/termcolor) | must | Engineer UX essential; glanceable results |
| aggregate subcommand (folder + corner YAML) | must | Eliminates biggest manual time sink; key differentiator |
| Excel report export (openpyxl) | should | Deliverable format; all IC teams use Excel for sign-off |
| Calibre LVS log parser (regex-based) | should | Adds LVS result to unified workflow |
| --json output mode + exit codes 0/1/2 | should | CI/CD integration requirement |
| PDF report export (reportlab) | later | Nice-to-have; Excel covers 80% of use cases |
| HSPICE binary TR0/AC0 parser | later | Complex reverse-engineering; MT0 ASCII covers measurement data |
| Spectre PSFXL (binary) parser | later | Requires libpsf dependency; scope to v2 |
| Monte Carlo result aggregation (mean/sigma) | later | v2 feature; statistical summary engine |

---

## Technical Approaches

| Approach | Pros | Cons | Complexity | Lock-in Risk |
|----------|------|------|-----------|-------------|
| Pure Python regex/struct parsers | Zero dependencies, pip-installable, fast for ASCII | Binary HSPICE/PSFXL needs reverse-engineering; maintenance per vendor version | Medium | Low |
| Leverage existing libs (psf-utils, spicelib) as backends | Proven parsers, saves 3-6 months of format R&D | GPLv3 from PySpice may contaminate; need adapter layer per lib | Low | Medium |
| Hybrid: own ASCII parsers + optional upstream libs | Full control for ASCII (MT0/PSF-ASCII/RAW); community-backed for binary; clean deps | More complex plugin architecture | Medium | Low |
| C extension / Cython for binary parsing | Very fast for large binary files | Build complexity, platform packaging, fewer contributors | High | Low |

Recommended approach (v1): Hybrid -- write own ASCII parsers for PSF-ASCII, HSPICE MT0, ngspice RAW; use optional psf-utils/libpsf for binary PSF (user installs spec-result-parser[spectre-binary]). Ships working v1 in 4-6 weeks; binary support added incrementally.

---

## Contrarian View

Arguments against building this:

1. **Cadence ADE Maestro already solves this for professional teams.** Every serious IC company already pays for Cadence Virtuoso. Engineers at large companies (Qualcomm, MediaTek, TSMC ecosystem) will not adopt a CLI tool when ADE Maestro handles corner simulation and spec checking natively. The TAM for "teams who need this and don't already have ADE Maestro" may be smaller than it appears.

2. **In-house scripts have won by default.** Analog teams are deeply conservative. They have maintained and trusted their grep/awk/OCEAN scripts for 10-20 years. Adoption requires convincing a team lead, passing corporate security review, and training -- a very high bar.

3. **Format diversity is a permanent maintenance moat.** EDA file formats (HSPICE binary, PSFXL binary) are undocumented proprietary formats. A single vendor update that changes binary headers can silently corrupt all downstream parsing with no warning.

4. **The open-source ASIC community is too small for sustainability.** Sky130 users number in the thousands. Without monetization or institutional backing, the tool risks becoming unmaintained within 2-3 years.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Binary format reverse-engineering fails / breaks on new tool versions | High | High | V1 ASCII-only (MT0, PSF-ASCII, ngspice raw). Binary = optional v2 scope. |
| Low adoption in commercial teams (not-invented-here culture) | High | Medium | Target open-source ASIC community first where switching cost = 0 |
| GPL license contamination from psf-utils/PySpice dependencies | Medium | High | Use MIT-compatible alternatives; write own ASCII parsers; audit dep licenses pre-ship |
| HSPICE/Spectre format version changes silently break parser | Medium | High | Ship reference test fixture files per format; regression CI test suite |
| Spec YAML format inadequate for complex specs (freq-dependent, conditional) | Medium | Medium | Design extensible schema from day 1; v1 scoped to scalar specs only |
| Cadence opens OCEAN CLI or open-sources ADE tool features | Low | High | Differentiate on multi-simulator support -- Cadence will never officially support ngspice |
| PDF report layout issues with reportlab | Low | Low | Ship Excel first; PDF is v2; openpyxl is well-documented |

---

## Recommendations

- [fact] No existing open-source CLI tool provides unified parsing for Spectre PSF, HSPICE MT0, ngspice RAW, and Calibre LVS in a single tool with spec checking and corner aggregation.
- [fact] The EDA market for analog IC tools is projected at ~$1.8 billion by 2025 (skyquestt.com), with analog verification automation identified as a key growth driver.
- [fact] All major open-source parsers (psf-utils, spicelib, hspiceParser) are single-simulator, format-only tools. None implement spec checking or corner aggregation.
- [inference] A unified, MIT-licensed CLI tool with CI/CD support would be immediately adopted by the open-source ASIC community (Sky130, GF180, IHP-SG13) -- a fast-growing segment with zero incumbent tooling.
- [inference] Binary format parsing (PSFXL, HSPICE TR0/AC0) is the highest technical risk. ASCII formats (PSF-ASCII, MT0, ngspice RAW) cover the most spec-relevant data and should be the full scope of v1.
- [recommendation] Build in Python 3.9+, MIT license, plugin-based parser architecture. Ship MVP with 3 ASCII parsers + YAML spec config + check + aggregate subcommands. Target 4-6 week build timeline.
- [recommendation] Publish to PyPI on day 1 for adoption signal. Track GitHub stars/PyPI downloads as leading indicator of organic community traction.
- [recommendation] Define the YAML spec file format as the first technical design artifact -- it drives CLI API design, user experience, and is the key differentiator vs. all competitors.

---

## Sources

| Source | Competitor / Topic | What was found |
|--------|-------------------|----------------|
| github.com/HMC-ACE/hspiceParser | hspiceParser | CLI pip tool for HSPICE binary/ASCII to CSV/MATLAB; single simulator only |
| analogflavor.com | BeSpice Wave | Widest format support (psf, tr0, vcd, ...); GUI-only; custom enterprise pricing |
| pypi.org/project/spicelib | spicelib | Multi-sim batch runner + RawRead for ngspice/LTspice; no spec check; active in 2024 |
| github.com/KenKundert/psf-utils | psf-utils | PSF ASCII reader; well-maintained; no spec check; ASCII PSF only |
| pypi.org/project/PySpice | PySpice | ngspice Python OOP interface; GPLv3; active; no spec check; ngspice-only |
| cadence.com (OCEAN docs) | Cadence OCEAN | SKILL scripting for ADE; spec check possible via scripting; Cadence-only |
| cadence.com (ADE Maestro) | Cadence ADE Maestro | Commercial gold standard for corner simulation + spec check; GUI-only; enterprise |
| skyquestt.com | Market size | Analog IC EDA tools segment ~$1.8B by 2025; ~5.5% CAGR |
| asicpro.com | Market trends 2024-25 | Data-driven design and regression analytics growing trend in analog verification |
| chipxpert.in | Analog automation | Automation driven by FinFET complexity and chronic analog talent shortage |

Data freshness: All sources from 2024-2026. No data flagged as stale. Research date: 2026-04-02.
