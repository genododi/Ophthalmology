#!/usr/bin/env bash
# One-shot: Keychain + gitignored local config for localhost auto-fill.
# Usage: GEMINI_API_KEY='...' ./scripts/setup-gemini-key.sh

set -euo pipefail
cd "$(dirname "$0")/.."

export GEMINI_API_KEY="${GEMINI_API_KEY:-}"
chmod +x scripts/store-gemini-keychain.sh scripts/seed-local-config.sh scripts/read-gemini-keychain.sh

./scripts/store-gemini-keychain.sh
./scripts/seed-local-config.sh

echo ""
echo "Next: run python3 server.py and open http://localhost:8000"
echo "The app will load the key from local config into localStorage (this browser only)."
echo "GitHub Pages uses the bundled default seed when localStorage is empty (see script.js)."
