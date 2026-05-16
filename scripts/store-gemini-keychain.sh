#!/usr/bin/env bash
# Store Gemini API key in macOS Keychain (Passwords app).
# Usage: GEMINI_API_KEY='your-key' ./scripts/store-gemini-keychain.sh
#    or: ./scripts/store-gemini-keychain.sh   # reads GEMINI_API_KEY or prompts securely

set -euo pipefail
cd "$(dirname "$0")/.."

SERVICE="${KEYCHAIN_SERVICE:-ophthalmology-gemini}"
ACCOUNT="${KEYCHAIN_ACCOUNT:-SMILE}"

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  if [[ -f config/gemini-api-key.local ]]; then
    GEMINI_API_KEY="$(tr -d '[:space:]' < config/gemini-api-key.local)"
  else
    read -rsp "Gemini API key: " GEMINI_API_KEY
    echo
  fi
fi

if [[ -z "$GEMINI_API_KEY" ]]; then
  echo "No API key provided." >&2
  exit 1
fi

if [[ "$GEMINI_API_KEY" == "$ACCOUNT" ]]; then
  echo "Refusing to store account label \"$ACCOUNT\" as the API key (use -w password field)." >&2
  exit 1
fi

# Update if entry exists, else add (-a account label, -w password = API key)
if security find-generic-password -s "$SERVICE" -a "$ACCOUNT" &>/dev/null; then
  security delete-generic-password -s "$SERVICE" -a "$ACCOUNT" &>/dev/null || true
fi

security add-generic-password \
  -s "$SERVICE" \
  -a "$ACCOUNT" \
  -w "$GEMINI_API_KEY" \
  -U \
  -T /usr/bin/security

echo "Stored in Keychain: service=$SERVICE account=$ACCOUNT (password = Gemini API key)"
