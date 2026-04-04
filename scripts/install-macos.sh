#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="$HOME/.openclaw/workspace"
if [ ! -d "$WORKSPACE" ]; then
  echo "OpenClaw workspace not found: $WORKSPACE" >&2
  exit 1
fi

echo "Installing openclaw-task-watchdog into $WORKSPACE"
mkdir -p "$WORKSPACE"
cp -R "$REPO_ROOT/tools" "$WORKSPACE/" || true
cp -R "$REPO_ROOT/tasks" "$WORKSPACE/" || true
cp -R "$REPO_ROOT/config" "$WORKSPACE/" || true
cp "$REPO_ROOT/docs/OPERATE.md" "$WORKSPACE/OPERATE.md"

echo
echo "Install complete."
echo "Recommended next steps:"
echo "1) Run acceptance:"
echo "   python3 tools/run_report_delivery_acceptance.py"
echo "2) Check live status:"
echo "   python3 tools/report_delivery_status.py"
echo "3) Read docs/OPERATE.md in the workspace if you want operator details."
