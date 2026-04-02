#!/usr/bin/env bash
# detect-framework.sh — Detect test framework in a directory
# Usage: bash detect-framework.sh [directory]
# Output: FRAMEWORK=<name> CMD=<command>
#
# Checks signals in priority order (first match wins).
# If no framework detected, outputs FRAMEWORK=unknown CMD=
#
# Supported frameworks (16):
#   jest, vitest, mocha, ava, pytest, go, cargo, mix,
#   gradle, mvn, dotnet, phpunit, rspec, dart, swift, make

set -euo pipefail

DIR="${1:-.}"

# Helper: safely check if a JSON file has a key under "scripts"
has_script_key() {
  local file="$1" key="$2"
  # Use a simple state machine: find "scripts" block, then check for key
  # This avoids false positives from "dependencies", "description", etc.
  awk -v key="\"${key}\"" '
    /"scripts"/ { in_scripts=1 }
    in_scripts && /\}/ { exit }
    in_scripts && $0 ~ key { found=1; exit }
    END { exit !found }
  ' "$file" 2>/dev/null
}

# Helper: check if Makefile has a target
has_make_target() {
  local file="$1" target="$2"
  grep -qE "^${target}[[:space:]]*:" "$file" 2>/dev/null
}

# Detect package manager from lockfiles
detect_pkg_manager() {
  if [[ -f "${DIR}/pnpm-lock.yaml" ]]; then
    echo "pnpm"
  elif [[ -f "${DIR}/yarn.lock" ]]; then
    echo "yarn"
  elif [[ -f "${DIR}/bun.lockb" ]] || [[ -f "${DIR}/bun.lock" ]]; then
    echo "bun"
  else
    echo "npm"
  fi
}

# Detect specific JS test runner from package.json + config files
detect_js_runner() {
  local pkg="${DIR}/package.json"

  # Check for Vitest config files first (most specific signal)
  if [[ -f "${DIR}/vitest.config.ts" ]] || [[ -f "${DIR}/vitest.config.js" ]] || \
     [[ -f "${DIR}/vitest.config.mts" ]] || [[ -f "${DIR}/vitest.config.mjs" ]]; then
    echo "vitest"
    return
  fi

  # Check for Vitest in devDependencies
  if grep -q '"vitest"' "$pkg" 2>/dev/null; then
    echo "vitest"
    return
  fi

  # Check for Mocha config files
  if [[ -f "${DIR}/.mocharc.yml" ]] || [[ -f "${DIR}/.mocharc.yaml" ]] || \
     [[ -f "${DIR}/.mocharc.js" ]] || [[ -f "${DIR}/.mocharc.json" ]]; then
    echo "mocha"
    return
  fi

  # Check for Mocha in devDependencies
  if grep -q '"mocha"' "$pkg" 2>/dev/null; then
    echo "mocha"
    return
  fi

  # Check for Ava config
  if grep -q '"ava"' "$pkg" 2>/dev/null; then
    echo "ava"
    return
  fi

  # Check for Jest config files
  if [[ -f "${DIR}/jest.config.ts" ]] || [[ -f "${DIR}/jest.config.js" ]] || \
     [[ -f "${DIR}/jest.config.json" ]]; then
    echo "jest"
    return
  fi

  # Check for Jest in devDependencies
  if grep -q '"jest"' "$pkg" 2>/dev/null; then
    echo "jest"
    return
  fi

  # Default: assume jest (npm test typically runs jest)
  echo "jest"
}

# ─── Priority 1: package.json with scripts.test ───────────────────────
if [[ -f "${DIR}/package.json" ]] && has_script_key "${DIR}/package.json" "test"; then
  PKG_MGR=$(detect_pkg_manager)
  JS_RUNNER=$(detect_js_runner)
  echo "FRAMEWORK=\"${JS_RUNNER}\" CMD=\"${PKG_MGR} test\""
  exit 0
fi

# ─── Priority 2: pytest ───────────────────────────────────────────────
if [[ -f "${DIR}/pytest.ini" ]]; then
  echo "FRAMEWORK=\"pytest\" CMD=\"pytest\""
  exit 0
fi
if [[ -f "${DIR}/pyproject.toml" ]]; then
  if grep -qE '\[tool\.pytest' "${DIR}/pyproject.toml" 2>/dev/null; then
    echo "FRAMEWORK=\"pytest\" CMD=\"pytest\""
    exit 0
  fi
fi
if [[ -f "${DIR}/setup.cfg" ]]; then
  if grep -qE '\[tool:pytest\]' "${DIR}/setup.cfg" 2>/dev/null; then
    echo "FRAMEWORK=\"pytest\" CMD=\"pytest\""
    exit 0
  fi
fi
if [[ -f "${DIR}/tox.ini" ]]; then
  if grep -qE '\[pytest\]' "${DIR}/tox.ini" 2>/dev/null; then
    echo "FRAMEWORK=\"pytest\" CMD=\"pytest\""
    exit 0
  fi
fi

# ─── Priority 3: Go ──────────────────────────────────────────────────
if [[ -f "${DIR}/go.mod" ]]; then
  echo "FRAMEWORK=\"go\" CMD=\"go test ./...\""
  exit 0
fi

# ─── Priority 4: Rust/Cargo ──────────────────────────────────────────
if [[ -f "${DIR}/Cargo.toml" ]]; then
  echo "FRAMEWORK=\"cargo\" CMD=\"cargo test\""
  exit 0
fi

# ─── Priority 5: .NET ────────────────────────────────────────────────
# Detect .csproj or .sln files
if ls "${DIR}"/*.sln 1>/dev/null 2>&1 || ls "${DIR}"/*.csproj 1>/dev/null 2>&1; then
  echo "FRAMEWORK=\"dotnet\" CMD=\"dotnet test\""
  exit 0
fi

# ─── Priority 6: Elixir/Mix ──────────────────────────────────────────
if [[ -f "${DIR}/mix.exs" ]]; then
  echo "FRAMEWORK=\"mix\" CMD=\"mix test\""
  exit 0
fi

# ─── Priority 7: Gradle ──────────────────────────────────────────────
if [[ -f "${DIR}/build.gradle" ]] || [[ -f "${DIR}/build.gradle.kts" ]]; then
  echo "FRAMEWORK=\"gradle\" CMD=\"gradle test\""
  exit 0
fi

# ─── Priority 8: Maven ───────────────────────────────────────────────
if [[ -f "${DIR}/pom.xml" ]]; then
  echo "FRAMEWORK=\"mvn\" CMD=\"mvn test\""
  exit 0
fi

# ─── Priority 9: PHP (PHPUnit) ───────────────────────────────────────
if [[ -f "${DIR}/phpunit.xml" ]] || [[ -f "${DIR}/phpunit.xml.dist" ]]; then
  echo "FRAMEWORK=\"phpunit\" CMD=\"./vendor/bin/phpunit\""
  exit 0
fi
if [[ -f "${DIR}/composer.json" ]] && grep -q '"phpunit"' "${DIR}/composer.json" 2>/dev/null; then
  echo "FRAMEWORK=\"phpunit\" CMD=\"./vendor/bin/phpunit\""
  exit 0
fi

# ─── Priority 10: Ruby (RSpec / minitest) ─────────────────────────────
if [[ -f "${DIR}/.rspec" ]]; then
  echo "FRAMEWORK=\"rspec\" CMD=\"bundle exec rspec\""
  exit 0
fi
if [[ -f "${DIR}/Gemfile" ]]; then
  if grep -q "'rspec'" "${DIR}/Gemfile" 2>/dev/null || grep -q '"rspec"' "${DIR}/Gemfile" 2>/dev/null; then
    echo "FRAMEWORK=\"rspec\" CMD=\"bundle exec rspec\""
    exit 0
  fi
  if grep -q "'minitest'" "${DIR}/Gemfile" 2>/dev/null || grep -q '"minitest"' "${DIR}/Gemfile" 2>/dev/null; then
    echo "FRAMEWORK=\"minitest\" CMD=\"bundle exec rake test\""
    exit 0
  fi
fi

# ─── Priority 11: Dart/Flutter ────────────────────────────────────────
if [[ -f "${DIR}/pubspec.yaml" ]]; then
  if grep -q 'flutter' "${DIR}/pubspec.yaml" 2>/dev/null; then
    echo "FRAMEWORK=\"dart\" CMD=\"flutter test\""
  else
    echo "FRAMEWORK=\"dart\" CMD=\"dart test\""
  fi
  exit 0
fi

# ─── Priority 12: Swift ──────────────────────────────────────────────
if [[ -f "${DIR}/Package.swift" ]]; then
  echo "FRAMEWORK=\"swift\" CMD=\"swift test\""
  exit 0
fi

# ─── Priority 13: Makefile with test target ───────────────────────────
if [[ -f "${DIR}/Makefile" ]] && has_make_target "${DIR}/Makefile" "test"; then
  echo "FRAMEWORK=\"make\" CMD=\"make test\""
  exit 0
fi

# ─── No framework detected ───────────────────────────────────────────
# Before giving up, check if this is a monorepo and hint at workspaces
MONOREPO=""
if [[ -f "${DIR}/nx.json" ]]; then
  MONOREPO="nx"
elif [[ -f "${DIR}/turbo.json" ]]; then
  MONOREPO="turbo"
elif [[ -f "${DIR}/lerna.json" ]]; then
  MONOREPO="lerna"
elif [[ -f "${DIR}/pnpm-workspace.yaml" ]]; then
  MONOREPO="pnpm-workspaces"
fi

if [[ -n "$MONOREPO" ]]; then
  echo "FRAMEWORK=\"unknown\" CMD=\"\" MONOREPO=\"${MONOREPO}\""
else
  echo "FRAMEWORK=\"unknown\" CMD=\"\""
fi
exit 1
