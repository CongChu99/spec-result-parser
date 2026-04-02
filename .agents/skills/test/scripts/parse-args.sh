#!/usr/bin/env bash
# parse-args.sh — Parse /run-tests arguments into structured form
# Usage: bash parse-args.sh [args...]
# Output: Shell-evaluable variable assignments
#
# Flags (--) are parsed first in any position.
# The first non-flag token is the scope argument.
# Only one scope argument is allowed.

set -euo pipefail

# Defaults
DRY_RUN=false
TIMEOUT=120
CWD=""
CMD=""
OUTPUT_MODE="concise"
SCOPE_TYPE=""
SCOPE_VALUE=""
ERRORS=""

# Parse arguments
args=("$@")
i=0
scope_found=false

while [[ $i -lt ${#args[@]} ]]; do
  arg="${args[$i]}"

  case "$arg" in
    --dry-run)
      DRY_RUN=true
      ;;
    --timeout)
      i=$((i + 1))
      if [[ $i -lt ${#args[@]} ]]; then
        TIMEOUT="${args[$i]}"
        if ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
          ERRORS="Invalid timeout value: ${TIMEOUT}"
        fi
      else
        ERRORS="--timeout requires a value"
      fi
      ;;
    --cwd)
      i=$((i + 1))
      if [[ $i -lt ${#args[@]} ]]; then
        CWD="${args[$i]}"
      else
        ERRORS="--cwd requires a value"
      fi
      ;;
    --cmd)
      i=$((i + 1))
      if [[ $i -lt ${#args[@]} ]]; then
        CMD="${args[$i]}"
      else
        ERRORS="--cmd requires a value"
      fi
      ;;
    --output)
      i=$((i + 1))
      if [[ $i -lt ${#args[@]} ]]; then
        OUTPUT_MODE="${args[$i]}"
        if [[ "$OUTPUT_MODE" != "concise" && "$OUTPUT_MODE" != "detailed" && "$OUTPUT_MODE" != "json" ]]; then
          ERRORS="Invalid output mode: ${OUTPUT_MODE}. Must be concise, detailed, or json."
        fi
      else
        ERRORS="--output requires a value"
      fi
      ;;
    --*)
      ERRORS="Unknown flag: ${arg}"
      ;;
    *)
      # Non-flag token — this is the scope argument
      if $scope_found; then
        ERRORS="Only one scope argument allowed. Got extra: ${arg}"
      else
        scope_found=true
        # Check for explicit scope prefix
        if [[ "$arg" == file:* ]]; then
          SCOPE_TYPE="file"
          SCOPE_VALUE="${arg#file:}"
        elif [[ "$arg" == dir:* ]]; then
          SCOPE_TYPE="dir"
          SCOPE_VALUE="${arg#dir:}"
        elif [[ "$arg" == name:* ]]; then
          SCOPE_TYPE="name"
          SCOPE_VALUE="${arg#name:}"
        elif [[ "$arg" == tag:* ]]; then
          SCOPE_TYPE="tag"
          SCOPE_VALUE="${arg#tag:}"
        else
          # Bare string → treat as name:
          SCOPE_TYPE="name"
          SCOPE_VALUE="$arg"
        fi
      fi
      ;;
  esac

  i=$((i + 1))
done

# Output as shell-evaluable variables (all values quoted for safe eval)
cat <<EOF
DRY_RUN="${DRY_RUN}"
TIMEOUT="${TIMEOUT}"
CWD="${CWD}"
CMD="${CMD}"
OUTPUT_MODE="${OUTPUT_MODE}"
SCOPE_TYPE="${SCOPE_TYPE}"
SCOPE_VALUE="${SCOPE_VALUE}"
ERRORS="${ERRORS}"
EOF
