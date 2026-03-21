#!/usr/bin/env bash
# Server setup: install deps and configure env vars for Telegram alerts
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==> Syncing dependencies..."
uv sync

if [[ ! -f .env ]]; then
    echo "==> Creating .env from .env.example..."
    cp .env.example .env
    echo "==> Edit .env and add your TELEGRAM_TOKEN and TELEGRAM_CHAT_ID"
    echo "    Then re-run: source .env && uv run ftf"
else
    echo "==> .env exists, loading for this shell..."
    set -a
    source .env
    set +a
    echo "==> TELEGRAM_TOKEN is ${TELEGRAM_TOKEN:+set}"
    echo "==> TELEGRAM_CHAT_ID is ${TELEGRAM_CHAT_ID:+set}"
    echo ""
    echo "To run with env vars:  source .env && uv run ftf"
    echo "Or just:               uv run ftf   (dotenv loads .env automatically)"
fi
