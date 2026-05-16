#!/usr/bin/env bash
# Print Gemini API key from macOS Keychain (for local dev only; do not log in CI).
# Usage: ./scripts/read-gemini-keychain.sh

set -euo pipefail

SERVICE="${KEYCHAIN_SERVICE:-ophthalmology-gemini}"
ACCOUNT="${KEYCHAIN_ACCOUNT:-SMILE}"

security find-generic-password -s "$SERVICE" -a "$ACCOUNT" -w 2>/dev/null
