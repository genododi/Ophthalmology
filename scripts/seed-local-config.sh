#!/usr/bin/env bash
# Write gitignored config/gemini-api-key.local from env or Keychain.
# Usage: GEMINI_API_KEY='...' ./scripts/seed-local-config.sh
#    or: ./scripts/seed-local-config.sh   # uses Keychain

set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p config

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  GEMINI_API_KEY="$(./scripts/read-gemini-keychain.sh 2>/dev/null || true)"
fi

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  read -rsp "Gemini API key: " GEMINI_API_KEY
  echo
fi

if [[ -z "$GEMINI_API_KEY" ]]; then
  echo "No API key available." >&2
  exit 1
fi

printf '%s' "$GEMINI_API_KEY" > config/gemini-api-key.local
chmod 600 config/gemini-api-key.local
echo "Wrote config/gemini-api-key.local (gitignored)"
