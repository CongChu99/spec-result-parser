# Spec: spec-result-parser

## ADDED Requirements

---

### Requirement: PSF-ASCII Parsing
Parse Cadence Spectre PSF-ASCII result files and extract named scalar measurement values.

**Priority**: MUST

#### Scenario: Parse a valid PSF-ASCII file and extract measurements
- **GIVEN** a Spectre PSF-ASCII file (`result.psf`) containing scalar measurement outputs (e.g., `gain`, `bw`, `pm`)
- **WHEN** the user runs `spec-parser check result.psf --spec opamp.spec.yaml`
- **THEN** the tool extracts all named scalar values from the PSF file with their units and proceeds to spec checking

#### Scenario: PSF file has no scalar measurements
- **GIVEN** a PSF-ASCII file that contains only waveform data (no `.MEASURE`-equivalent scalars)
- **WHEN** the user runs `spec-parser check result.psf --spec opamp.spec.yaml`
- **THEN** the tool exits with code 2 and prints: `ERROR: No scalar measurements found in result.psf. Only scalar PSF sections are supported.`

#### Scenario: PSF file is corrupted or not valid PSF format
- **GIVEN** a file `result.psf` with corrupted or non-PSF content
- **WHEN** the user runs `spec-parser check result.psf --spec opamp.spec.yaml`
- **THEN** the tool exits with code 2 and prints: `ERROR: Cannot parse result.psf as PSF-ASCII. Check file format.`

---

### Requirement: HSPICE MT0 Parsing
Parse HSPICE `.mt0` / printfile outputs and extract `.MEASURE` statement scalar results.

**Priority**: MUST

#### Scenario: Parse a valid HSPICE MT0 file
- **GIVEN** an HSPICE `.mt0` file with `.MEASURE` results (e.g., `gain_dc=68.5`, `ugbw=12.5e6`)
- **WHEN** the user runs `spec-parser check result.mt0 --spec opamp.spec.yaml`
- **THEN** the tool extracts all measurement name-value pairs and proceeds to spec checking

#### Scenario: Auto-detect format from file extension
- **GIVEN** files `corner_tt.psf` and `corner_ss.mt0` in a folder
- **WHEN** the user runs `spec-parser aggregate ./corners/ --spec opamp.spec.yaml`
- **THEN** the tool auto-detects PSF format for `.psf` files and HSPICE format for `.mt0` files without additional flags

#### Scenario: Unknown file extension in aggregate folder
- **GIVEN** a folder containing `result.tr0` (binary HSPICE waveform, not supported in v1)
- **WHEN** the tool scans the folder
- **THEN** it prints a warning `WARN: Skipping result.tr0 — unsupported format in v1 (binary TR0)` and continues processing other files

---

### Requirement: YAML Spec Config
Load spec targets from a YAML file defining min/max bounds per measurement name.

**Priority**: MUST

#### Scenario: Load a valid YAML spec file
- **GIVEN** a file `opamp.spec.yaml`:
  ```yaml
  specs:
    gain_dc:  { min: 60, max: null, unit: dB }
    ugbw:     { min: 10e6, max: null, unit: Hz }
    pm:       { min: 45, max: null, unit: deg }
    offset:   { min: null, max: 5e-3, unit: V }
  ```
- **WHEN** the tool loads the spec file
- **THEN** it creates SpecTarget objects with correct min/max/unit per measurement

#### Scenario: YAML has a measurement name not found in the result file
- **GIVEN** spec YAML defines `cmrr` but the PSF file has no `cmrr` measurement
- **WHEN** `spec-parser check` runs
- **THEN** it prints `WARN: Spec 'cmrr' not found in result file — skipped` and marks that row as `N/A`

#### Scenario: YAML file is missing or malformed
- **GIVEN** the `--spec` path points to a non-existent or invalid YAML file
- **WHEN** the tool tries to load it
- **THEN** it exits with code 2 and prints: `ERROR: Cannot load spec file: opamp.spec.yaml`

---

### Requirement: CSV Spec Config
Load spec targets from a CSV file with columns: `measurement`, `min`, `max`, `unit`.

**Priority**: MUST

#### Scenario: Load a valid CSV spec file
- **GIVEN** a file `opamp.spec.csv`:
  ```
  measurement,min,max,unit
  gain_dc,60,,dB
  ugbw,10e6,,Hz
  pm,45,,deg
  offset,,5e-3,V
  ```
- **WHEN** the user runs `spec-parser check result.psf --spec opamp.spec.csv`
- **THEN** the tool detects CSV from extension and loads spec targets identically to YAML mode

#### Scenario: CSV has blank min or max (one-sided spec)
- **GIVEN** a CSV row `gain_dc,60,,dB` (no max bound)
- **WHEN** the tool loads the spec
- **THEN** it creates a SpecTarget with `min=60`, `max=None` — only the lower bound is checked

---

### Requirement: Single-File Spec Check (`check` subcommand)
Compare extracted measurements from a single result file against all spec targets, print color-coded PASS/FAIL table.

**Priority**: MUST

#### Scenario: All specs pass
- **GIVEN** a PSF-ASCII file where all extracted measurements satisfy their spec bounds
- **WHEN** the user runs `spec-parser check result.psf --spec opamp.spec.yaml`
- **THEN** the tool prints a table with all rows in green, summary line `All 6 specs: PASS`, and exits with code 0

#### Scenario: One or more specs fail
- **GIVEN** a PSF-ASCII file where `pm=42 deg` fails the spec `min: 45 deg`
- **WHEN** `spec-parser check` runs
- **THEN** the `pm` row is printed in red with `FAIL`, the actual value `42 deg`, and the miss `3 deg below min`. Exit code = 1

#### Scenario: Margin warning (close to limit)
- **GIVEN** a measurement value within 10% of a spec bound (e.g., `gain_dc=61 dB` against `min=60 dB`, margin = 1/60 = 1.7%)
- **WHEN** `spec-parser check` runs
- **THEN** the row is printed in yellow with `MARGIN` and margin percentage displayed

#### Scenario: Check runs in under 2 seconds
- **GIVEN** a PSF-ASCII file with up to 20 scalar measurements
- **WHEN** the check command runs
- **THEN** it completes and prints output within 2 seconds on any modern Linux machine

---

### Requirement: Multi-Corner Aggregation (`aggregate` subcommand)
Parse all result files in a folder, map to PVT corners, build and display a corner x spec worst-case matrix.

**Priority**: MUST

#### Scenario: Aggregate 25 corner files with a corner mapping YAML
- **GIVEN** a folder `./corners/` with 25 `.psf` and/or `.mt0` files, and a `corners.yaml`:
  ```yaml
  corner_tt_27:  { file: "tt_27.psf",  process: TT, voltage: 1.8, temp: 27 }
  corner_ss_m40: { file: "ss_m40.psf", process: SS, voltage: 1.62, temp: -40 }
  ...
  ```
- **WHEN** the user runs `spec-parser aggregate ./corners/ --spec opamp.spec.yaml --corners corners.yaml`
- **THEN** the tool builds a corner x spec matrix, each cell showing the value and PASS/FAIL status, with the worst-case row highlighted

#### Scenario: Aggregate without corner mapping (flat mode)
- **GIVEN** a folder of result files with no corner mapping YAML
- **WHEN** the user runs `spec-parser aggregate ./corners/ --spec opamp.spec.yaml`
- **THEN** the tool uses filenames as corner names and builds the matrix using filename as corner identifier

#### Scenario: One file in the folder fails to parse
- **GIVEN** a folder with 10 valid files and 1 corrupted file
- **WHEN** `spec-parser aggregate` runs
- **THEN** it prints `WARN: Skipping corrupted_file.psf — parse error` and completes the matrix with the remaining 10 files

#### Scenario: Worst-case corner highlight
- **GIVEN** a corner matrix where corner `SS_m40` has the lowest margin for `pm`
- **WHEN** aggregate runs
- **THEN** the matrix includes a `Worst Case` row showing the minimum value per spec across all corners, colored red/yellow/green accordingly

---

### Requirement: PASS/FAIL Exit Codes
Return machine-readable exit codes for scripting and future CI/CD integration.

**Priority**: MUST

#### Scenario: All pass — exit code 0
- **GIVEN** all spec checks pass
- **WHEN** `spec-parser check` or `spec-parser aggregate` completes
- **THEN** process exits with code 0

#### Scenario: Any fail — exit code 1
- **GIVEN** at least one spec check fails
- **WHEN** the command completes
- **THEN** process exits with code 1

#### Scenario: Config / parse error — exit code 2
- **GIVEN** the spec file or result file cannot be loaded
- **WHEN** the command starts
- **THEN** process exits with code 2 with an error message

---

### Requirement: Verbose Debug Mode
Allow engineers to inspect raw parsed values for troubleshooting.

**Priority**: SHOULD

#### Scenario: Verbose flag shows raw parser output
- **GIVEN** an engineer suspects the parser is misreading a measurement name
- **WHEN** the user runs `spec-parser check result.psf --spec opamp.spec.yaml --verbose`
- **THEN** the tool prints each parsed measurement name/value/unit before the spec check table

---

### Requirement: Help and Usage Documentation
Comprehensive `--help` output for all subcommands.

**Priority**: MUST

#### Scenario: Top-level help
- **GIVEN** the user runs `spec-parser --help`
- **THEN** it lists `check` and `aggregate` subcommands with one-line descriptions

#### Scenario: Subcommand help
- **GIVEN** the user runs `spec-parser check --help`
- **THEN** it shows all options: `--spec`, `--verbose`, `--margin-threshold`
