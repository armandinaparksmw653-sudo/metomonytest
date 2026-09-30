#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

require_min_version() {
  local label="$1"
  local actual="$2"
  local expected="$3"
  if [[ "$(printf '%s\n' "$expected" "$actual" | sort -V | awk 'NR == 1 { print; exit }')" != "$expected" ]]; then
    printf '%s version mismatch: expected >= %s, got %s\n' \
      "$label" "$expected" "$actual" >&2
    exit 1
  fi
}

require_min_version "GHC" "$(ghc --numeric-version)" "9.4.7"
require_min_version "Agda" "$(agda --version | awk '{print $3}')" "2.6.3"
require_min_version \
  "GF" \
  "$(gf --version | awk 'NR == 1 { print $5 }')" \
  "3.12.0"

./scripts/bootstrap.sh
make evaluation-test
make qid-fiber-test
make framenet-generated-check
make formal-artifact
make report

git diff --exit-code -- \
  auxiliary/grammar/GeneratedMetonymy.gf \
  auxiliary/grammar/GeneratedMetonymyEng.gf \
  auxiliary/data/contextual-gf-actions.json \
  auxiliary/data/contextual-gf-nouns.json \
  auxiliary/data/framenet-role-capabilities.json

printf '%s\n' "publication artifact verified"
