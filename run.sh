#!/usr/bin/env bash
# Quick launcher for Google Antigravity & Ollama Doctor

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "Select launch mode:"
echo "  1) Interactive CLI Doctor (Terminal)"
echo "  2) Web Dashboard GUI (Browser at http://localhost:8080)"
echo "  3) Run Verification Test Agent"
echo "  4) Exit"
read -p "Enter choice [1-4] (default 1): " choice
choice=${choice:-1}

case "$choice" in
  1)
    python3 doctor.py
    ;;
  2)
    python3 server.py
    ;;
  3)
    python3 test_local_agent.py
    ;;
  *)
    echo "Exiting."
    ;;
esac
