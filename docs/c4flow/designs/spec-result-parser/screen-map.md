# Screen Map: spec-result-parser

## CLI Output Flow (4 terminal mockup frames)

### FIG. 01 — `check` PASS — `XbzS5`
- **Components:** Terminal chrome (macOS-style dots + dark bar), command prompt line, separator, table header (SPEC/VALUE/MIN/MAX/STATUS), 4 data rows, summary line
- **Spec refs:** spec.md#single-file-spec-check, spec.md#passfail-exit-codes
- **Notes:** All rows green. Summary shows `✓ All 4 specs: PASS`. File type shown (Spectre PSF-ASCII). Elapsed time shown.

### FIG. 02 — `check` FAIL + MARGIN — `Nb5io`
- **Components:** Same chrome, command prompt, table with MARGIN row (yellow badge), FAIL row (red background highlight + red FAIL badge), summary line
- **Spec refs:** spec.md#single-file-spec-check, spec.md#margin-warning
- **Notes:** FAIL row gets red `--accent-red-dim` fill entire row. MARGIN row shows yellow badge. Error summary: `✗ 1 of 3 specs FAILED`. Exit 1 shown.

### FIG. 03 — `aggregate` corner matrix — `jERgt`
- **Components:** Terminal chrome, command prompt with folder path + both flags, progress info line, matrix table (CORNER col + 4 spec cols), Worst Case row, fail summary
- **Spec refs:** spec.md#multi-corner-aggregation, spec.md#worst-case-corner-highlight
- **Notes:** SS_1V62_m40 row has full red background. Worst Case row has amber `#1A1000` background with bold values. Each cell shows value + badge. Exit 1 shown.

### FIG. 04 — Error + `--verbose` debug — `GMksV`
- **Components:** Two terminal windows stacked vertically. Top window: red border stroke, ERROR message in red, hint line in secondary text, exit code. Bottom window: `--verbose` mode showing [DEBUG] lines in muted color, parsed values in blue.
- **Spec refs:** spec.md#verbose-debug-mode, design.md#error-handling
- **Notes:** Top window border is `$--accent-red` instead of `$--border` to signal error state. DEBUG lines distinguish detected format, count, values, spec file.

## Shared Components

| Component | Reusable ID | Description |
|-----------|-------------|-------------|
| `Comp/Badge/PASS` | `Gp8xK` | Green dim bg, green bold text, 4px radius |
| `Comp/Badge/FAIL` | `aLyFf` | Red dim bg, red bold text |
| `Comp/Badge/MARGIN` | `c5wmF` | Yellow dim bg, yellow bold text |
| `Comp/Badge/NA` | `E4yR4` | Panel bg, muted text |
| `Comp/TerminalWindow` | `t9KFB` | Chrome bar (dots + title) + body slot |

## Design Token Reference → MASTER.md
