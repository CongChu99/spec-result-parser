#!/usr/bin/env bash
# classify-failure.sh — Classify test output as Tier 1 (code) or Tier 2 (env)
# Usage: bash classify-failure.sh < output.txt
#    or: bash classify-failure.sh output.txt
# Output: TIER=<1|2> TYPE=<type> DETAIL=<matched pattern>
#
# Tier 2 (environment) is checked first — these prevent tests from running at all.
# Tier 1 (code) is checked second — these are actual test failures.

set -euo pipefail

# Read input from file argument or stdin
if [[ $# -gt 0 && -f "$1" ]]; then
  INPUT=$(cat "$1")
else
  INPUT=$(cat)
fi

# --- Tier 2 patterns (environment/tooling — check first) ---

# Module/import errors
if echo "$INPUT" | grep -qiE '(ModuleNotFoundError|Cannot find module|Module not found|ImportError|No module named|require\(\) of ES Module|ERR_REQUIRE_ESM)'; then
  echo "TIER=2 TYPE=missing_module DETAIL=missing module or import"
  exit 0
fi

# Command not found
if echo "$INPUT" | grep -qiE '(command not found|not recognized as|is not recognized|No such file or directory.*bin|spawn .* ENOENT)'; then
  echo "TIER=2 TYPE=command_not_found DETAIL=command not found or not in PATH"
  exit 0
fi

# Permission denied
if echo "$INPUT" | grep -qiE '(Permission denied|EACCES|access denied|EPERM)'; then
  echo "TIER=2 TYPE=permission_denied DETAIL=permission denied"
  exit 0
fi

# Config/parse errors
if echo "$INPUT" | grep -qiE '(SyntaxError.*config|YAMLException|JSON\.parse|YAML.*error|invalid.*config|Cannot read config|Configuration error)'; then
  echo "TIER=2 TYPE=config_parse_error DETAIL=configuration parse error"
  exit 0
fi

# Docker / container errors (check before generic connection errors)
if echo "$INPUT" | grep -qiE '(Cannot connect to the Docker daemon|docker.*not running|container.*not found|no such container|Error response from daemon)'; then
  echo "TIER=2 TYPE=docker_error DETAIL=Docker daemon or container error"
  exit 0
fi

# Connection errors (database, network, external services)
if echo "$INPUT" | grep -qiE '(ECONNREFUSED|Connection refused|Cannot connect|connection.*timeout|ETIMEDOUT|ENOTFOUND|EHOSTUNREACH|getaddrinfo|ECONNRESET)'; then
  echo "TIER=2 TYPE=connection_error DETAIL=connection error"
  exit 0
fi

# Out of memory
if echo "$INPUT" | grep -qiE '(FATAL ERROR.*heap|out of memory|MemoryError|java\.lang\.OutOfMemoryError|ENOMEM|JavaScript heap out of memory)'; then
  echo "TIER=2 TYPE=out_of_memory DETAIL=out of memory"
  exit 0
fi

# Port already in use
if echo "$INPUT" | grep -qiE '(EADDRINUSE|address already in use|port.*already.*use)'; then
  echo "TIER=2 TYPE=port_in_use DETAIL=port already in use"
  exit 0
fi

# Version mismatch / dependency conflicts
if echo "$INPUT" | grep -qiE '(peer dep|ERESOLVE|version mismatch|incompatible version|requires.*version|could not resolve)'; then
  echo "TIER=2 TYPE=dependency_conflict DETAIL=dependency version conflict"
  exit 0
fi

# TypeScript / compilation errors (not test failures)
if echo "$INPUT" | grep -qiE '(TS[0-9]{4}:|error TS|Cannot find type definition|tsc.*error|compilation failed|Build failed)' && \
   ! echo "$INPUT" | grep -qiE '(FAIL|FAILED|assert|expect)'; then
  echo "TIER=2 TYPE=compilation_error DETAIL=TypeScript or build compilation error"
  exit 0
fi

# Database errors (when no test output present)
if echo "$INPUT" | grep -qiE '(SQLITE_ERROR|relation.*does not exist|no such table|Access denied for user|authentication failed|OperationalError.*database)' && \
   ! echo "$INPUT" | grep -qiE '(FAIL|FAILED|[0-9]+ (failed|passing))'; then
  echo "TIER=2 TYPE=database_error DETAIL=database connection or schema error"
  exit 0
fi

# --- Tier 1 patterns (test/code failures) ---

# Assertion errors (broad coverage across all frameworks)
if echo "$INPUT" | grep -qiE '(AssertionError|AssertionError|assert\.|assertEqual|assertEquals|assertThat|expect\(|toBe|toEqual|toMatch|toThrow|assert_equal|assert_eq!|assert_ne!|assert_match|XCTAssert|XCTFail|shouldBe|shouldEqual|FAIL|FAILED|failures?=|errors?=)'; then
  echo "TIER=1 TYPE=test_failure DETAIL=test assertion or failure detected"
  exit 0
fi

# Test count patterns (e.g., "3 failed", "Tests: 2 failed")
if echo "$INPUT" | grep -qiE '([0-9]+ (failed|failing|error|broken)|Tests:.*failed|FAILURES!|tests? FAILED|FAIL:|--- FAIL:)'; then
  echo "TIER=1 TYPE=test_failure DETAIL=test failure count detected"
  exit 0
fi

# Framework-specific failure patterns
if echo "$INPUT" | grep -qiE '(not ok [0-9]|# tests [0-9]+.*# fail [0-9]+|FAILURES|failures\.|PhpUnit.*ERRORS|Minitest.*Error|ExUnit.*\(test\))'; then
  echo "TIER=1 TYPE=test_failure DETAIL=framework-specific failure pattern"
  exit 0
fi

# Stack traces pointing to test files (broader extension coverage)
if echo "$INPUT" | grep -qiE '\.(test|spec|_test|_spec)\.(ts|js|tsx|jsx|py|go|rs|ex|rb|php|java|kt|swift|dart):[0-9]+'; then
  echo "TIER=1 TYPE=test_failure DETAIL=stack trace in test file"
  exit 0
fi

# Exception/error patterns that indicate code failures
if echo "$INPUT" | grep -qiE '(panic:|goroutine [0-9]+|thread.*panicked|Unhandled.*Error|uncaught.*exception|RuntimeError|NullPointerException|IndexError|KeyError|TypeError|ValueError|ZeroDivisionError)'; then
  echo "TIER=1 TYPE=runtime_error DETAIL=runtime exception or panic"
  exit 0
fi

# --- Unrecognized ---
echo "TIER=2 TYPE=unrecognized_exit DETAIL=unrecognized output pattern"
exit 0
