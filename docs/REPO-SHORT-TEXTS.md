# Repo short texts

## One-line tagline
Stop long-running OpenClaw tasks from silently stalling in the middle.

## One-sentence description
A watchdog runtime for long-running OpenClaw tasks that must not silently stall, disappear, or fake progress.

## Slightly longer description
`openclaw-task-watchdog` adds a file-backed watchdog layer to OpenClaw long tasks so operators can see uncertain middle states, wait for observation, reconcile from evidence, and prevent silent failure from being mistaken for progress.

## Problem-first version
Long-running automation often fails in the middle while still looking alive. This project exists to make that failure visible before humans mistake silence for progress.

## Installation-first version
Install into an OpenClaw workspace, run acceptance, then use the status command to confirm the watchdog runtime is healthy.

## First commands to show in docs or posts
```bash
python tools/run_report_delivery_acceptance.py
python tools/report_delivery_status.py
python tools/validate_report_delivery_suite.py
```

## Three-value version
This project is for:
- stopping silent stall
- exposing fake progress
- turning uncertain middle state into observed, reconciled terminal state

## Topics block
- openclaw
- automation
- long-running-tasks
- task-watchdog
- workflow
- heartbeat
- observability
- reconciliation
- failure-detection
- windows
- macos
- python
