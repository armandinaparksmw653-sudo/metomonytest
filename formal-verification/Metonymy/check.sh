#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if rg -n \
  '(^|[[:space:]])(postulate|TERMINATING|NON_TERMINATING|NO_POSITIVITY)([[:space:]]|$)' \
  formal-verification/Metonymy --glob '*.agda'; then
  echo "forbidden unsafe declaration found in formal artifact" >&2
  exit 1
fi

make formal
python3 formal-verification/Metonymy/generate_manifest.py --check
printf '%s\n' "formal publication artifact verified"
