#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CUBICAL_DIR="${CUBICAL_LIB:-$HOME/.cache/metonymy/cubical-v0.5}"
RGL_SOURCE="${RGL_SOURCE:-$HOME/.cache/metonymy/gf-rgl-20260403}"
RGL_DIR="${RGL_LIB:-$HOME/.cache/metonymy/gf-rgl-lib}"
CUBICAL_COMMIT="132a2a3197b490c571356f0399a2a6fbfab40f2a"
RGL_COMMIT="e825d9223305ad3066e1ac5b276bcdedd2fcd15a"

verify_commit() {
  local directory="$1"
  local expected="$2"
  local label="$3"
  local actual
  actual="$(git -C "$directory" rev-parse HEAD)"
  if [[ "$actual" != "$expected" ]]; then
    printf '%s commit mismatch: expected %s, got %s\n' \
      "$label" "$expected" "$actual" >&2
    exit 1
  fi
}

if [[ ! -f "$CUBICAL_DIR/cubical.agda-lib" ]]; then
  mkdir -p "$(dirname "$CUBICAL_DIR")"
  git clone --depth 1 --branch v0.5 \
    "https://github.com/agda/cubical.git" \
    "$CUBICAL_DIR"
fi
verify_commit "$CUBICAL_DIR" "$CUBICAL_COMMIT" "Cubical"

if [[ ! -f "$RGL_DIR/alltenses/SyntaxEng.gfo" ]]; then
  mkdir -p "$(dirname "$RGL_SOURCE")"
  if [[ ! -f "$RGL_SOURCE/Setup.hs" ]]; then
    git clone --depth 1 --branch 20260403 \
      "https://github.com/GrammaticalFramework/gf-rgl.git" \
      "$RGL_SOURCE"
  fi
  verify_commit "$RGL_SOURCE" "$RGL_COMMIT" "GF RGL"
  (
    cd "$RGL_SOURCE"
    runghc Setup.hs build prelude lang api --langs=Eng --gf=gf
    runghc Setup.hs copy --dest="$RGL_DIR"
  )
elif [[ -d "$RGL_SOURCE/.git" ]]; then
  verify_commit "$RGL_SOURCE" "$RGL_COMMIT" "GF RGL"
fi

cd "$ROOT"

make test CUBICAL_LIB="$CUBICAL_DIR" RGL_LIB="$RGL_DIR"
