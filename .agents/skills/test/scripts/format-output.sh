#!/usr/bin/env bash
# format-output.sh — Format test results for display
# Usage: bash format-output.sh <mode> <passed> <failed> <duration> [json_data_file]
#   mode: concise | detailed | json
#
# For concise/detailed modes, reads failure details from stdin (one per line):
#   FILE:LINE:TEST_NAME:TIER:TYPE:CONFIDENCE:MESSAGE:SUGGESTION
#
# For json mode, reads from json_data_file or stdin as raw JSON.

set -euo pipefail

MODE="${1:-concise}"
PASSED="${2:-0}"
FAILED="${3:-0}"
DURATION="${4:-0}"

TOTAL=$((PASSED + FAILED))

# Check if stdout is a TTY (for symbol rendering)
if [[ -t 1 && "$MODE" != "json" ]]; then
  SYM_PASS="✓"
  SYM_FAIL="✗"
  SYM_BULLET="·"
else
  SYM_PASS="PASS"
  SYM_FAIL="FAIL"
  SYM_BULLET="-"
fi

case "$MODE" in
  concise)
    if [[ "$FAILED" -eq 0 ]]; then
      echo "${SYM_PASS} ${PASSED}/${TOTAL} passed  (${DURATION}s)"
    else
      echo "${SYM_FAIL} ${FAILED}/${TOTAL} failed  (${DURATION}s)"
      echo ""
      # Read failure lines from stdin
      slot_count=0
      overflow_count=0
      while IFS=: read -r file line test_name tier type confidence message suggestion; do
        if [[ $slot_count -lt 5 ]]; then
          if [[ "$tier" == "env" ]]; then
            echo "${SYM_BULLET} ${file}${line:+:${line}} — ${message}   [env]"
            echo "  ${suggestion:-${message}}"
          else
            echo "${SYM_BULLET} ${file}${line:+:${line}} — ${message}"
            if [[ -n "$confidence" && -n "${suggestion:-}" ]]; then
              echo "  [${confidence}] ${suggestion}"
            elif [[ -n "$confidence" ]]; then
              echo "  [${confidence}] ${message}"
            fi
          fi
          echo ""
          slot_count=$((slot_count + 1))
        else
          overflow_count=$((overflow_count + 1))
        fi
      done
      if [[ $overflow_count -gt 0 ]]; then
        echo "${overflow_count} more failures not shown. Run /run-tests name:<test> to deep-dive."
      fi
    fi
    ;;

  detailed)
    if [[ "$FAILED" -eq 0 ]]; then
      echo "${SYM_PASS} ${PASSED}/${TOTAL} passed  (${DURATION}s)"
    else
      echo "${SYM_FAIL} ${FAILED}/${TOTAL} failed  (${DURATION}s)"
      echo ""
      while IFS=: read -r file line test_name tier type confidence message suggestion; do
        echo "── ${file} ────────────────────────────────────────"
        echo "Test:    \"${test_name}\"${line:+ (line ${line})}"
        echo "Tier:    ${tier}"
        echo "Type:    ${type}"
        echo "Cause:   ${message}"
        if [[ -n "$confidence" && -n "${suggestion:-}" ]]; then
          echo "Suggestion [${confidence}]: ${suggestion}"
        elif [[ -n "$confidence" ]]; then
          echo "Suggestion [${confidence}]: ${message}"
        fi
        echo "──────────────────────────────────────────────────────────────"
        echo ""
      done
    fi
    ;;

  json)
    # For JSON mode, if a data file is provided, cat it
    # Otherwise the agent constructs the JSON directly
    if [[ -n "${5:-}" && -f "${5:-}" ]]; then
      cat "$5"
    else
      # Minimal JSON success output
      cat <<JSONEOF
{
  "passed": ${PASSED},
  "failed": ${FAILED},
  "duration": ${DURATION},
  "analyzed": 0,
  "command": "",
  "cwd": "",
  "framework": "unknown",
  "exit_code": 0,
  "timed_out": false,
  "warnings": [],
  "failures": []
}
JSONEOF
    fi
    ;;

  *)
    echo "ERROR: Unknown output mode: ${MODE}" >&2
    exit 1
    ;;
esac
