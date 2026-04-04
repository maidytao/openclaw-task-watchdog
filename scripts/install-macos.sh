#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="$HOME/.openclaw/workspace"
if [ ! -d "$WORKSPACE" ]; then
  echo "OpenClaw workspace not found: $WORKSPACE" >&2
  exit 1
fi

echo "Installing openclaw-hard-delivery into $WORKSPACE"
mkdir -p "$WORKSPACE"
cp -R "$REPO_ROOT/tools" "$WORKSPACE/" || true
cp -R "$REPO_ROOT/tasks" "$WORKSPACE/" || true
cp -R "$REPO_ROOT/config" "$WORKSPACE/" || true
cp "$REPO_ROOT/docs/OPERATE.md" "$WORKSPACE/OPERATE.md"

echo "Install complete. Recommended next step:"
echo "python3 tools/run_report_delivery_acceptance.py"
