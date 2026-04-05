#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo ""
echo " ==========================================="
echo "   Bulk Email Sender  |  Azure ACS"
echo " ==========================================="
echo ""

# ── Locate uv ─────────────────────────────────────────────────────────────────
UV=""
if [ -x "$DIR/uv" ]; then
    UV="$DIR/uv"
elif command -v uv &>/dev/null; then
    UV="uv"
else
    echo " [ERROR] uv not found."
    echo " Download it from https://github.com/astral-sh/uv/releases"
    echo " and place it in the same folder as this script."
    exit 1
fi

# ── First-run: configure .env ─────────────────────────────────────────────────
if [ ! -f "$DIR/.env" ]; then
    if [ ! -f "$DIR/.env.example" ]; then
        echo " [ERROR] .env.example is missing."
        exit 1
    fi
    cp "$DIR/.env.example" "$DIR/.env"
    echo " First-time setup detected."
    echo " Fill in your Azure credentials in .env:"
    echo "   ACS_CONNECTION_STRING"
    echo "   ACS_SENDER_EMAIL"
    echo ""
    EDITOR="${EDITOR:-}"
    if   command -v nano  &>/dev/null; then nano  "$DIR/.env"
    elif command -v vim   &>/dev/null; then vim   "$DIR/.env"
    elif command -v gedit &>/dev/null; then gedit "$DIR/.env"
    else
        echo " Could not find a text editor. Edit $DIR/.env manually, then re-run."
        exit 1
    fi
fi

# ── Sync dependencies ─────────────────────────────────────────────────────────
echo " Checking dependencies..."
"$UV" sync --quiet

# ── Kill anything already on the ports ───────────────────────────────────────
fuser -k 9000/tcp 2>/dev/null || true
fuser -k 8501/tcp 2>/dev/null || true

# ── Start backend ─────────────────────────────────────────────────────────────
echo " Starting backend  (http://localhost:9000)..."
"$UV" run uvicorn main:app --host 0.0.0.0 --port 9000 &
BACKEND_PID=$!

# ── Open browser ──────────────────────────────────────────────────────────────
sleep 2
if   command -v xdg-open &>/dev/null; then xdg-open http://localhost:8501 &>/dev/null &
elif command -v open     &>/dev/null; then open     http://localhost:8501  &>/dev/null &
fi

# ── Start frontend (blocks) ───────────────────────────────────────────────────
echo " Starting frontend  (http://localhost:8501)..."
echo ""
echo " Press Ctrl+C to stop."
echo ""

cleanup() {
    echo ""
    echo " Shutting down..."
    kill "$BACKEND_PID" 2>/dev/null || true
    fuser -k 9000/tcp 2>/dev/null || true
    echo " Done."
}
trap cleanup EXIT INT TERM

"$UV" run streamlit run app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true \
    --browser.gatherUsageStats=false
