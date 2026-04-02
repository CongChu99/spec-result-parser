# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-02

### Added

- `spec-parser check` — single-file spec checking (PSF-ASCII and HSPICE MT0)
- `spec-parser aggregate` — multi-corner folder aggregation with worst-case row
- Spec config loader supporting YAML and CSV formats
- SpecChecker with PASS/FAIL/MARGIN/NA status and `margin_pct`
- FormatDetector — auto-detect file format from extension + header sniff
- CornerAggregator — scan folder, parse all corners, return `list[Corner]`
- TerminalRenderer — color-coded Rich tables (PASS=green, FAIL=red, MARGIN=yellow)
- Exit codes: 0 (all PASS), 1 (any FAIL), 2 (parse/config error)
- GitHub Actions CI: Python 3.9, 3.11, 3.12 with 80% coverage gate
- MIT license
