#!/usr/bin/env bash
# Print Gemini API key from macOS Keychain password field (for local dev only).
# Convention: -a SMILE is the account label; -w returns the password (= API key).
# Usage: ./scripts/read-gemini-keychain.sh

set -euo pipefail

SERVICE="${KEYCHAIN_SERVICE:-ophthalmology-gemini}"
ACCOUNT="${KEYCHAIN_ACCOUNT:-SMILE}"

key="$(security find-generic-password -s "$SERVICE" -a "$ACCOUNT" -w 2>/dev/null || true)"
if [[ -z "$key" || "$key" == "$ACCOUNT" ]]; then
  exit 1
fi
printf '%s' "$key"
